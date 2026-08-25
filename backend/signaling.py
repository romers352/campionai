"""WebRTC signaling for doctor consultations — raw WebRTC, no vendor SFU.

Media goes peer-to-peer and never touches this server. All this does is relay SDP
offers/answers and ICE candidates between exactly the two participants of a consult
session, plus carry in-call text chat on the same socket.

A consequence of P2P worth stating plainly: server-side recording is impossible
here. If a jurisdiction ever requires consult recordings, this needs an SFU.
"""
import os
import time
import hmac
import base64
import hashlib
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from models import now_iso, new_id

logger = logging.getLogger("campionai.rtc")

TURN_TTL_SEC = 6 * 3600
JOINABLE = ("scheduled", "accepted", "live")

# ponytail: in-process room registry — correct for a single uvicorn worker, which is
# what this runs on. Scaling past one process needs Redis pub/sub between workers.
ROOMS: dict[str, dict[str, WebSocket]] = {}


def ice_servers(user_id: str) -> list:
    """STUN is free and covers most users; the ~15% behind symmetric NAT need TURN.

    TURN credentials are short-lived HMACs (coturn's `use-auth-secret` scheme) — a
    static username/password in client JS gets scraped and the relay becomes someone
    else's free bandwidth.
    """
    servers = [{"urls": ["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"]}]
    host = os.environ.get("TURN_HOST", "").strip()
    secret = os.environ.get("TURN_SECRET", "").strip()
    if host and secret:
        username = f"{int(time.time()) + TURN_TTL_SEC}:{user_id}"
        credential = base64.b64encode(
            hmac.new(secret.encode(), username.encode(), hashlib.sha1).digest()
        ).decode()
        servers.append({
            "urls": [f"turn:{host}?transport=udp", f"turn:{host}?transport=tcp"],
            "username": username,
            "credential": credential,
        })
    return servers


def make_router(db, get_current_user, authenticate):
    r = APIRouter()

    @r.get("/rtc/ice")
    async def get_ice(user=Depends(get_current_user)):
        turn_ready = bool(os.environ.get("TURN_HOST", "").strip() and os.environ.get("TURN_SECRET", "").strip())
        return {"iceServers": ice_servers(user["id"]), "turn_configured": turn_ready}

    @r.websocket("/rtc/{session_id}")
    async def signal(ws: WebSocket, session_id: str):
        await ws.accept()
        role = None
        try:
            # Auth in the first message, never a query param: query strings land in
            # access logs and browser history, and this token is long-lived.
            hello = await ws.receive_json()
            token = (hello or {}).get("token")
            if not token:
                await ws.close(code=4401, reason="auth required")
                return
            try:
                user = await authenticate(token)
            except Exception:
                await ws.close(code=4401, reason="invalid token")
                return

            session = await db.consult_sessions.find_one({"id": session_id}, {"_id": 0})
            if not session:
                await ws.close(code=4404, reason="session not found")
                return
            if session["status"] not in JOINABLE:
                await ws.close(code=4409, reason=f"session is {session['status']}")
                return

            if session["user_id"] == user["id"]:
                role = "user"
            else:
                doctor = await db.doctors.find_one({"user_id": user["id"]}, {"_id": 0, "id": 1})
                if doctor and session.get("doctor_id") == doctor["id"]:
                    role = "doctor"
            if not role:
                await ws.close(code=4403, reason="not a participant")
                return

            room = ROOMS.setdefault(session_id, {})
            if role in room:
                # Same participant already connected elsewhere — drop the stale socket.
                try:
                    await room[role].close(code=4409, reason="replaced by a newer connection")
                except Exception:
                    pass
            room[role] = ws

            peer_role = "doctor" if role == "user" else "user"
            await ws.send_json({"type": "joined", "role": role, "peer_present": peer_role in room,
                                "iceServers": ice_servers(user["id"])})
            if peer_role in room:
                try:
                    await room[peer_role].send_json({"type": "peer-joined", "role": role})
                except Exception:
                    pass

            if session["status"] != "live" and len(room) == 2:
                await db.consult_sessions.update_one(
                    {"id": session_id, "status": {"$ne": "live"}},
                    {"$set": {"status": "live", "started_at": now_iso(), "updated_at": now_iso()}},
                )

            while True:
                msg = await ws.receive_json()
                mtype = msg.get("type")

                if mtype == "chat":
                    text = (msg.get("text") or "").strip()[:4000]
                    if not text:
                        continue
                    entry = {
                        "id": new_id(), "session_id": session_id, "sender_role": role,
                        "sender_id": user["id"], "text": text, "created_at": now_iso(),
                    }
                    # consult_messages, never `messages` — see the module docstring.
                    await db.consult_messages.insert_one(dict(entry))
                    entry.pop("_id", None)
                    for target in (ws, room.get(peer_role)):
                        if target:
                            try:
                                await target.send_json({"type": "chat", **entry})
                            except Exception:
                                pass

                elif mtype in ("offer", "answer", "ice-candidate", "media-state", "hangup"):
                    peer = room.get(peer_role)
                    if peer:
                        try:
                            await peer.send_json({**msg, "from": role})
                        except Exception:
                            pass
                    if mtype == "hangup":
                        await _end_session(db, session_id)
                        break

                elif mtype == "ping":
                    await ws.send_json({"type": "pong"})

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"rtc error on {session_id}: {e}")
        finally:
            room = ROOMS.get(session_id, {})
            if role and room.get(role) is ws:
                room.pop(role, None)
                peer_role = "doctor" if role == "user" else "user"
                peer = room.get(peer_role)
                if peer:
                    try:
                        await peer.send_json({"type": "peer-left", "role": role})
                    except Exception:
                        pass
            if not room:
                ROOMS.pop(session_id, None)
                await _end_session(db, session_id)

    return r


async def _end_session(db, session_id: str):
    """Close out a live session once, stamping duration. Guarded on status so a
    reconnect or a second hangup cannot rewrite the numbers."""
    s = await db.consult_sessions.find_one({"id": session_id}, {"_id": 0})
    if not s or s.get("status") != "live":
        return
    started = s.get("started_at")
    duration = 0
    if started:
        try:
            duration = int((datetime.now(timezone.utc) - datetime.fromisoformat(started)).total_seconds())
        except Exception:
            duration = 0
    await db.consult_sessions.update_one(
        {"id": session_id, "status": "live"},
        {"$set": {"status": "completed", "ended_at": now_iso(),
                  "duration_sec": duration, "updated_at": now_iso()}},
    )
