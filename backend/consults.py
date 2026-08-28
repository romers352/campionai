"""Human doctor consultations: scheduled bookings, an instant 'talk now' queue,
access gating, per-session payment, and ratings.

Consult chat lives in `consult_messages`, deliberately NOT `messages`. The AI's
transcript builder and memory extractor both read `messages` unconditionally, so
putting clinical conversation there would quietly feed it into long-term AI memory.
"""
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pymongo import ReturnDocument

from doctors import get_consult_settings, is_online, public_doctor
from models import ConsultBook, ConsultRequest, ConsultRate, now_iso, new_id
from notifications import alert_contact

logger = logging.getLogger("campionai.consults")

REQUEST_TTL_MIN = 5          # an unaccepted instant request expires
CRISIS_WINDOW_MIN = 60       # how recently a high-risk event must have fired to unlock a crisis consult
CRISIS_TTL_MIN = 120         # a crisis request stays open far longer than a normal one
SESSION_SLOT_MIN = 30        # scheduled sessions occupy a 30-minute slot
LIVE_STATUSES = ("requested", "pending_payment", "scheduled", "accepted", "live")
BOOKED_STATUSES = ("scheduled", "accepted", "live")

# Statuses that consume a free-tier allowance. Must include "requested" and
# "pending_payment": an instant session is created as "requested", so leaving those
# out meant instant sessions never counted and the monthly cap never fired.
# cancelled/expired/no_show are excluded — a request no doctor answered must not
# burn the user's allowance.
COUNTED_STATUSES = ("requested", "pending_payment", "scheduled", "accepted", "live", "completed")


def _month_key(dt=None):
    dt = dt or datetime.now(timezone.utc)
    return dt.strftime("%Y-%m")


def _parse(iso):
    try:
        return datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
    except Exception:
        return None


FREE = {"price": 0.0, "commission": 0.0, "doctor_earning": 0.0, "requires_payment": False}


async def free_sessions_used(db, user_id: str) -> int:
    """Volunteer sessions this calendar month. Crisis sessions are excluded — they
    never count against anyone."""
    return await db.consult_sessions.count_documents({
        "user_id": user_id,
        "kind": {"$ne": "crisis"},
        "price": 0,
        "status": {"$in": COUNTED_STATUSES},
        "month": _month_key(),
    })


async def resolve_access(db, settings: dict, user: dict, doctor: dict, kind: str, plus_active: bool) -> dict:
    """Returns {price, commission, doctor_earning, requires_payment}, or raises 402.

    Three paths: a crisis session is always allowed, a volunteer session is capped
    for free users, and a paid session must be paid for up front.

    Module-level (not a closure) so it is directly testable — see selfcheck.py.
    """
    price = 0.0 if doctor.get("is_volunteer") else round(float(doctor.get("session_price", 0) or 0), 2)

    if kind == "crisis":
        # Never gate someone in crisis on billing state or a monthly counter.
        return dict(FREE)

    if price <= 0:
        if plus_active:
            return dict(FREE)
        cap = int(settings["free_volunteer_sessions_per_month"])
        used = await free_sessions_used(db, user["id"])
        if used >= cap:
            raise HTTPException(
                status_code=402,
                detail=f"You've used your {cap} free volunteer sessions this month. "
                       f"CampionAI Plus removes the limit, or you can book a paid doctor.",
            )
        return dict(FREE)

    commission = round(price * float(settings["commission_pct"]) / 100, 2)
    return {"price": price, "commission": commission,
            "doctor_earning": round(price - commission, 2), "requires_payment": True}


def make_router(db, get_current_user, get_doctor_user, plus_state,
                paypal_create_order, paypal_capture_order, claim_transaction) -> APIRouter:
    r = APIRouter()

    async def check_access(user: dict, doctor: dict, kind: str) -> dict:
        settings = await get_consult_settings(db)
        return await resolve_access(db, settings, user, doctor, kind, bool(plus_state(user).get("active")))

    async def expire_stale():
        """Lazy sweep — cheaper than a scheduler for this volume.

        Crisis requests get a much longer window: an emailed doctor needs time to
        sign in, and timing one out after five minutes is the wrong failure mode.
        """
        now = datetime.now(timezone.utc)
        await db.consult_sessions.update_many(
            {"status": "requested", "kind": {"$ne": "crisis"},
             "created_at": {"$lt": (now - timedelta(minutes=REQUEST_TTL_MIN)).isoformat()}},
            {"$set": {"status": "expired", "updated_at": now_iso()}},
        )
        await db.consult_sessions.update_many(
            {"status": "requested", "kind": "crisis",
             "created_at": {"$lt": (now - timedelta(minutes=CRISIS_TTL_MIN)).isoformat()}},
            {"$set": {"status": "expired", "updated_at": now_iso()}},
        )

    async def load_session(session_id: str, user: dict):
        """A session is visible only to its two participants."""
        s = await db.consult_sessions.find_one({"id": session_id}, {"_id": 0})
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        doctor = await db.doctors.find_one({"user_id": user["id"]}, {"_id": 0, "id": 1})
        if s["user_id"] != user["id"] and (not doctor or s.get("doctor_id") != doctor["id"]):
            raise HTTPException(status_code=403, detail="Not your session")
        return s

    async def start_payment(session_doc: dict, user: dict):
        order = await paypal_create_order(
            session_doc["price"], f"Consultation with {session_doc['doctor_name']}", custom_id=session_doc["id"])
        if not order:
            raise HTTPException(status_code=503, detail="Payments are not configured")
        await db.payment_transactions.insert_one({
            "session_id": f"paypal-order-{order['id']}", "user_id": user["id"], "package_id": "consult",
            "amount": session_doc["price"], "currency": "usd", "type": "consult", "provider": "paypal",
            "consult_session_id": session_doc["id"], "description": f"Consultation · {session_doc['doctor_name']}",
            "status": "initiated", "payment_status": "pending", "granted": False,
            "created_at": now_iso(), "updated_at": now_iso(),
        })
        await db.consult_sessions.update_one({"id": session_doc["id"]}, {"$set": {"paypal_order_id": order["id"]}})
        return order["id"]

    def build_session(user, doctor, mode, kind, access, scheduled_at=None, note=None):
        return {
            "id": new_id(),
            "user_id": user["id"],
            "doctor_id": doctor["id"],
            "doctor_name": doctor.get("name"),
            "user_name": (user.get("profile") or {}).get("preferred_name") or "A CampionAI user",
            "mode": mode if mode in ("video", "audio", "chat") else "video",
            "kind": kind,
            "status": "pending_payment" if access["requires_payment"] else ("requested" if kind in ("instant", "crisis") else "scheduled"),
            "scheduled_at": scheduled_at,
            "month": _month_key(_parse(scheduled_at) if scheduled_at else None),
            "note": note,
            "price": access["price"],
            "commission": access["commission"],
            "doctor_earning": access["doctor_earning"],
            "payout_status": "pending" if access["price"] > 0 else "n/a",
            "paypal_order_id": None,
            "started_at": None, "ended_at": None, "duration_sec": 0,
            "rated": False,
            "created_at": now_iso(), "updated_at": now_iso(),
        }

    # ---------------- Scheduled booking ----------------
    @r.post("/consults/book")
    async def book(inp: ConsultBook, user=Depends(get_current_user)):
        doctor = await db.doctors.find_one({"id": inp.doctor_id, "status": "verified"}, {"_id": 0})
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        when = _parse(inp.scheduled_at)
        if not when:
            raise HTTPException(status_code=400, detail="Invalid date/time")
        if when < datetime.now(timezone.utc) + timedelta(minutes=5):
            raise HTTPException(status_code=400, detail="Pick a time at least 5 minutes from now")

        slots = await db.doctor_availability.find(
            {"doctor_id": doctor["id"], "weekday": when.weekday()}, {"_id": 0}).to_list(50)
        hhmm = when.strftime("%H:%M")
        if slots and not any(s["start"] <= hhmm < s["end"] for s in slots):
            raise HTTPException(status_code=400, detail="That time is outside the doctor's availability")

        # Overlap check: no other booking for this doctor inside the slot window.
        window_start = (when - timedelta(minutes=SESSION_SLOT_MIN - 1)).isoformat()
        window_end = (when + timedelta(minutes=SESSION_SLOT_MIN - 1)).isoformat()
        clash = await db.consult_sessions.find_one({
            "doctor_id": doctor["id"], "status": {"$in": BOOKED_STATUSES},
            "scheduled_at": {"$gt": window_start, "$lt": window_end},
        })
        if clash:
            raise HTTPException(status_code=409, detail="That slot was just taken — please pick another")

        access = await check_access(user, doctor, "scheduled")
        doc = build_session(user, doctor, inp.mode, "scheduled", access, when.isoformat(), inp.note)
        await db.consult_sessions.insert_one(dict(doc))
        doc.pop("_id", None)

        order_id = await start_payment(doc, user) if access["requires_payment"] else None
        return {"session": doc, "requires_payment": access["requires_payment"], "order_id": order_id}

    # ---------------- Instant 'talk now' ----------------
    async def verify_crisis(user_id: str) -> bool:
        """A crisis session is free and uncapped, so the claim has to be earned. We
        only honour it if the safety classifier logged a high-risk event for this
        user recently — the client's word is never enough."""
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=CRISIS_WINDOW_MIN)).isoformat()
        event = await db.safety_events.find_one(
            {"user_id": user_id, "risk_level": "high", "created_at": {"$gte": cutoff}}, {"_id": 0, "id": 1})
        return bool(event)

    @r.post("/consults/request")
    async def request_now(inp: ConsultRequest, user=Depends(get_current_user)):
        await expire_stale()
        kind = "crisis" if (inp.crisis and await verify_crisis(user["id"])) else "instant"
        if inp.doctor_id:
            doctor = await db.doctors.find_one({"id": inp.doctor_id, "status": "verified"}, {"_id": 0})
            if not doctor:
                raise HTTPException(status_code=404, detail="Doctor not found")
            # In a crisis we still create the request for an offline doctor and alert
            # them — refusing to connect someone at risk is the wrong failure mode.
            if not is_online(doctor) and kind != "crisis":
                raise HTTPException(status_code=409, detail="That doctor just went offline")
        else:
            # Broadcast: pick the best-rated online doctor matching country + language.
            candidates = await db.doctors.find(
                {"status": "verified", "is_online": True}, {"_id": 0}).to_list(200)
            candidates = [d for d in candidates if is_online(d)]
            country = (user.get("country") or "").upper()
            local = [d for d in candidates if d.get("country") == country]
            pool = local or candidates
            if not pool and kind == "crisis":
                pool = [d for d in await db.doctors.find({"status": "verified"}, {"_id": 0}).to_list(200)]
            if not pool:
                raise HTTPException(status_code=409, detail="No doctors are online right now — try booking a time instead")
            pool.sort(key=lambda d: (-float(d.get("rating_avg", 0) or 0), -int(d.get("rating_count", 0) or 0)))
            doctor = pool[0]

        access = await check_access(user, doctor, kind)
        doc = build_session(user, doctor, inp.mode, kind, access, None, inp.note)
        await db.consult_sessions.insert_one(dict(doc))
        doc.pop("_id", None)

        # An offline doctor can't see the dashboard, so a crisis request has to reach
        # them out-of-band or it just times out at five minutes.
        if kind == "crisis" and not is_online(doctor):
            await alert_contact(
                doctor.get("name", ""), doctor.get("email"), doctor.get("phone"),
                "CampionAI: urgent session request",
                "Someone using CampionAI is in crisis and has requested a session with you. Please open your dashboard.",
                "<div style='font-family:sans-serif;line-height:1.6'>"
                "<h3 style='color:#E11D48'>Urgent session request</h3>"
                "<p>Someone using CampionAI is in crisis and requested a session with you. "
                "Please sign in and open your dashboard.</p></div>",
            )

        order_id = await start_payment(doc, user) if access["requires_payment"] else None
        return {"session": doc, "requires_payment": access["requires_payment"], "order_id": order_id}

    @r.post("/consults/{session_id}/accept")
    async def accept(session_id: str, user=Depends(get_doctor_user)):
        """First doctor to accept wins. The guard lives in the query, not in Python —
        two simultaneous accepts cannot both pass."""
        s = await db.consult_sessions.find_one_and_update(
            {"id": session_id, "status": "requested", "doctor_id": user["doctor"]["id"]},
            {"$set": {"status": "accepted", "accepted_at": now_iso(), "updated_at": now_iso()}},
            return_document=ReturnDocument.AFTER,
        )
        if not s:
            existing = await db.consult_sessions.find_one({"id": session_id}, {"_id": 0, "status": 1})
            if not existing:
                raise HTTPException(status_code=404, detail="Session not found")
            raise HTTPException(status_code=409, detail=f"This request is no longer open ({existing['status']})")
        s.pop("_id", None)
        return s

    # ---------------- Payment confirm ----------------
    @r.post("/consults/{session_id}/pay/{order_id}")
    async def confirm_payment(session_id: str, order_id: str, user=Depends(get_current_user)):
        s = await load_session(session_id, user)
        if s["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Not your session")
        if s.get("paypal_order_id") != order_id:
            raise HTTPException(status_code=400, detail="Order does not match this session")
        if s["status"] != "pending_payment":
            return s

        captured = await paypal_capture_order(order_id)
        if (captured or {}).get("status") != "COMPLETED":
            raise HTTPException(status_code=400, detail="Payment was not completed")
        await claim_transaction(f"paypal-order-{order_id}")

        new_status = "requested" if s["kind"] == "instant" else "scheduled"
        updated = await db.consult_sessions.find_one_and_update(
            {"id": session_id, "status": "pending_payment"},
            {"$set": {"status": new_status, "paid_at": now_iso(), "updated_at": now_iso()}},
            return_document=ReturnDocument.AFTER,
        )
        if updated:
            updated.pop("_id", None)
        return updated or s

    # ---------------- Listing ----------------
    @r.get("/consults")
    async def my_consults(user=Depends(get_current_user)):
        await expire_stale()
        doctor = await db.doctors.find_one({"user_id": user["id"]}, {"_id": 0, "id": 1})
        q = {"doctor_id": doctor["id"]} if doctor else {"user_id": user["id"]}
        return await db.consult_sessions.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)

    @r.get("/consults/inbox")
    async def doctor_inbox(user=Depends(get_doctor_user)):
        """Open instant requests plus upcoming bookings for this doctor."""
        await expire_stale()
        return await db.consult_sessions.find(
            {"doctor_id": user["doctor"]["id"], "status": {"$in": LIVE_STATUSES}}, {"_id": 0}
        ).sort("created_at", -1).to_list(100)

    @r.get("/consults/{session_id}")
    async def get_consult(session_id: str, user=Depends(get_current_user)):
        s = await load_session(session_id, user)
        doctor = await db.doctors.find_one({"id": s["doctor_id"]}, {"_id": 0})
        return {**s, "doctor": public_doctor(doctor) if doctor else None}

    @r.get("/consults/{session_id}/messages")
    async def get_messages(session_id: str, user=Depends(get_current_user)):
        await load_session(session_id, user)
        return await db.consult_messages.find(
            {"session_id": session_id}, {"_id": 0}).sort("created_at", 1).to_list(1000)

    @r.post("/consults/{session_id}/cancel")
    async def cancel(session_id: str, user=Depends(get_current_user)):
        s = await load_session(session_id, user)
        if s["status"] in ("completed", "cancelled", "expired"):
            raise HTTPException(status_code=400, detail=f"Session is already {s['status']}")
        await db.consult_sessions.update_one({"id": session_id}, {"$set": {
            "status": "cancelled", "cancelled_by": user["id"], "updated_at": now_iso(),
        }})
        # ponytail: refunds are manual — the admin payout ledger shows the charge.
        # Wire PayPal refunds here when volume justifies it.
        if s.get("price", 0) > 0 and s.get("status") not in ("pending_payment",):
            logger.info(f"consult {session_id} cancelled after payment — manual refund may be due")
        return {"ok": True}

    # ---------------- Ratings ----------------
    @r.post("/consults/{session_id}/rate")
    async def rate(session_id: str, inp: ConsultRate, user=Depends(get_current_user)):
        s = await db.consult_sessions.find_one({"id": session_id, "user_id": user["id"]}, {"_id": 0})
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        if s["status"] != "completed":
            raise HTTPException(status_code=400, detail="You can only rate a completed session")

        doc = {
            "id": new_id(), "session_id": session_id, "doctor_id": s["doctor_id"],
            "user_id": user["id"], "stars": inp.stars, "comment": (inp.comment or "").strip() or None,
            "created_at": now_iso(),
        }
        try:
            await db.doctor_ratings.insert_one(dict(doc))
        except Exception:
            # Unique index on session_id — the database, not app logic, blocks double-rating.
            raise HTTPException(status_code=409, detail="You've already rated this session")

        await db.consult_sessions.update_one({"id": session_id}, {"$set": {"rated": True}})
        # Full recompute: the volume is tiny and it stays correct if a rating is ever deleted.
        agg = await db.doctor_ratings.aggregate([
            {"$match": {"doctor_id": s["doctor_id"]}},
            {"$group": {"_id": None, "avg": {"$avg": "$stars"}, "n": {"$sum": 1}}},
        ]).to_list(1)
        if agg:
            await db.doctors.update_one({"id": s["doctor_id"]}, {"$set": {
                "rating_avg": round(float(agg[0]["avg"]), 2), "rating_count": int(agg[0]["n"]),
            }})
        doc.pop("_id", None)
        return doc

    return r
