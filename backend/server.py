import asyncio
import os
import re
import json
import base64
import logging
import secrets
from pathlib import Path
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, UploadFile, File, Query
from fastapi.responses import StreamingResponse, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from models import (
    RegisterInput, LoginInput, OnboardingInput, ProfileUpdate, ChatInput,
    SessionCreate, MemoryUpdate, ModelRouteConfig,
    ProviderSettings, PrivateModeInput, VoiceSettingsInput, TTSInput,
    FoodInput, FoodEdit, EventInput, PlanItemToggle, PlanItemAdd, PlanReorder,
    ChatFeedback, MoodInput, GratitudeInput, PaypalActivate, DonationOrder,
    GoogleSessionInput, ForgotPasswordInput, ResetPasswordInput, ContactInput, now_iso, new_id,
)
from auth import (
    hash_password, verify_password, create_token,
    build_get_current_user, build_get_admin_user, build_get_doctor_user, build_authenticate,
)
from hotlines import get_hotlines, country_list, COUNTRY_NAMES
from llm_router import ModelRouter, DEFAULT_ROUTES, list_openrouter_models
from safety import classify_message
from memory_engine import extract_memories, build_memory_context
from notifications import alert_contact, summarize, send_email
from voice import synthesize
from storage import put_object, get_object, init_storage, APP_NAME, MIME_TYPES
from doctors import make_router as doctors_router, is_online as doctor_is_online, public_doctor
from consults import make_router as consults_router
from signaling import make_router as signaling_router
from paypal_client import (
    get_subscription as paypal_get_subscription,
    cancel_subscription as paypal_cancel_subscription,
    activate_subscription as paypal_activate_subscription,
    subscription_transactions as paypal_subscription_transactions,
    create_order as paypal_create_order,
    capture_order as paypal_capture_order,
    verify_webhook as paypal_verify_webhook,
    ensure_plans as paypal_ensure_plans,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("campionai")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="CampionAI")
api = APIRouter(prefix="/api")

router_engine = ModelRouter(db)
authenticate = build_authenticate(db)
get_current_user = build_get_current_user(db)
get_admin_user = build_get_admin_user(get_current_user)
get_doctor_user = build_get_doctor_user(get_current_user, db)

CHECKIN_INTERVALS = {"daily": 20, "few_times_week": 55, "user_set": None, "off": None}


# ---------------- Personality ----------------
def build_system_prompt(user, memory_context, transcript, risk):
    profile = user.get("profile", {})
    name = profile.get("preferred_name") or "friend"
    style = profile.get("communication_style") or "warm"
    facts = []
    if profile.get("work"):
        facts.append(f"Work: {profile['work']}")
    if profile.get("education"):
        facts.append(f"Education: {profile['education']}")
    if profile.get("likes"):
        facts.append(f"Likes: {', '.join(profile['likes'])}")
    if profile.get("important_people"):
        facts.append(f"Important people: {', '.join(profile['important_people'])}")
    if profile.get("goals"):
        facts.append(f"Goals: {', '.join(profile['goals'])}")
    facts_block = ("\nCore profile:\n" + "\n".join(facts)) if facts else ""

    base = f"""You are CampionAI — a warm, genuine, emotionally-present companion. You talk like a trusted close friend, not a corporate assistant.

Voice & style:
- Natural, casual, human. Short-to-medium messages. Contractions. React like a real friend.
- NEVER say "as an AI language model", "I'm just an AI", or robotic disclaimers. You are openly an AI companion, but you don't spam it.
- Be curious about {name}. Ask thoughtful follow-ups. Remember what matters. Celebrate wins, sit with the hard stuff.
- Use emojis very sparingly (at most one, and often none). Warmth comes from your words, not decorations.
- Write in natural, plain sentences. Avoid headings, bullet lists, and markdown formatting; a rare **bold** word for a hotline name is fine.
- Communication style preference: {style}.
- You are NOT a therapist or psychiatrist. You do NOT diagnose, and you do NOT clinically probe. You keep the person company and keep them talking.
{facts_block}
"""
    if memory_context:
        base += "\n" + memory_context + "\n"
    if transcript:
        base += "\nRecent conversation:\n" + transcript + "\n"

    if risk == "high":
        base += (
            "\nSAFETY MODE (high concern detected): Respond with deep warmth and calm. Stay present, do not panic, "
            "do not lecture. Gently let them know they are not alone and that you're connecting them with people who can help right now. "
            "Do NOT diagnose or interrogate. Encourage them to stay with you. Keep it short, human, caring."
        )
    elif risk == "medium":
        base += (
            "\nGENTLE-CARE MODE: They sound like they're having a hard time. Be extra warm, validating, and present. "
            "Gently keep them talking. Don't diagnose or push clinical questions."
        )
    return base


async def recent_transcript(session_id, limit=12):
    msgs = await db.messages.find({"session_id": session_id}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    msgs = list(reversed(msgs))
    lines = []
    for m in msgs:
        who = "CampionAI" if m["role"] == "assistant" else "Them"
        lines.append(f"{who}: {m['content']}")
    return "\n".join(lines)


# ---------------- Auth ----------------
@api.post("/auth/register")
async def register(inp: RegisterInput):
    existing = await db.users.find_one({"email": inp.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    uid = new_id()
    doc = {
        "id": uid,
        "email": inp.email.lower(),
        "password_hash": hash_password(inp.password),
        "is_admin": False,
        "role": "doctor" if inp.as_doctor else "user",
        "token_version": 0,
        "onboarded": False,
        "private_mode": False,
        "profile": {"preferred_name": inp.preferred_name, "likes": [], "important_people": [], "goals": [],
                     "communication_style": "warm"},
        "trusted_contact": None,
        "consent": None,
        "country": None,
        "checkin_frequency": "daily",
        "last_checkin": None,
        "created_at": now_iso(),
    }
    await db.users.insert_one(doc)
    return {"token": create_token(uid, 0), "user": _public_user(doc)}


@api.post("/auth/login")
async def login(inp: LoginInput):
    user = await db.users.find_one({"email": inp.email.lower()})
    if not user or not verify_password(inp.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"token": create_token(user["id"], user.get("token_version", 0)), "user": _public_user(user)}


@api.post("/auth/logout")
async def logout(user=Depends(get_current_user)):
    """Bumping token_version invalidates every token already issued for this user —
    including any that leaked into a URL or a proxy log."""
    await db.users.update_one({"id": user["id"]}, {"$inc": {"token_version": 1}})
    return {"ok": True}


def _reset_email_html(link: str) -> str:
    return f"""
    <div style="font-family:system-ui,sans-serif;max-width:480px;margin:0 auto;color:#1a1a1c">
      <h2 style="font-weight:500">Reset your CampionAI password</h2>
      <p style="color:#555;line-height:1.6">We got a request to reset your password. Tap the button below to choose a new one. This link expires in 30 minutes.</p>
      <p style="margin:28px 0">
        <a href="{link}" style="background:#1a1a1c;color:#fff;text-decoration:none;padding:12px 22px;border-radius:999px;font-weight:500">Reset password</a>
      </p>
      <p style="color:#888;font-size:13px;line-height:1.6">If you didn't ask for this, you can safely ignore this email — your password won't change.</p>
      <p style="color:#aaa;font-size:12px;word-break:break-all">{link}</p>
    </div>
    """


@api.post("/auth/forgot-password")
async def forgot_password(inp: ForgotPasswordInput, request: Request):
    """Always returns a generic success so we never reveal whether an email is registered.
    If Resend isn't configured yet, the reset link is returned as a dev fallback so the
    flow stays testable — this auto-disables the moment RESEND_API_KEY is set."""
    resp = {"ok": True, "message": "If that email is registered, a reset link is on its way."}
    user = await db.users.find_one({"email": inp.email.lower()})
    if not user:
        return resp

    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    await db.password_resets.insert_one({
        "id": new_id(), "user_id": user["id"], "token": token,
        "expires_at": expires, "used": False, "created_at": now_iso(),
    })

    origin = (request.headers.get("origin") or "").rstrip("/")
    if not origin:
        ref = request.headers.get("referer") or ""
        origin = ref.split("/reset-password")[0].rstrip("/") if ref else ""
    reset_link = f"{origin}/reset-password?token={token}" if origin else f"/reset-password?token={token}"

    if os.environ.get("RESEND_API_KEY", "").strip():
        try:
            await send_email(user["email"], "Reset your CampionAI password", _reset_email_html(reset_link))
        except Exception as e:
            logger.error(f"reset email failed: {e}")
    else:
        logger.warning(f"[dev] password reset link for {user['email']}: {reset_link}")
        resp["dev_reset_link"] = reset_link
        resp["email_configured"] = False
    return resp


@api.post("/auth/reset-password")
async def reset_password(inp: ResetPasswordInput):
    rec = await db.password_resets.find_one({"token": inp.token})
    if not rec or rec.get("used"):
        raise HTTPException(status_code=400, detail="This reset link is invalid or has already been used.")
    try:
        expired = datetime.fromisoformat(rec["expires_at"]) < datetime.now(timezone.utc)
    except Exception:
        expired = True
    if expired:
        raise HTTPException(status_code=400, detail="This reset link has expired — please request a new one.")
    user = await db.users.find_one({"id": rec["user_id"]})
    if not user:
        raise HTTPException(status_code=400, detail="Account not found.")
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_password(inp.new_password), "auth_provider": "both" if not user.get("password_hash") else user.get("auth_provider", "email")},
         "$inc": {"token_version": 1}},
    )
    await db.password_resets.update_one({"id": rec["id"]}, {"$set": {"used": True, "used_at": now_iso()}})
    return {"ok": True, "message": "Your password has been reset. You can sign in now."}


EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"


@api.post("/auth/google/session")
async def google_session(inp: GoogleSessionInput):
    """Emergent-managed Google sign-in. Exchanges the one-time session_id for the
    user's Google profile (server-side), upserts the user into our existing users
    collection (matched by email), and issues the SAME app JWT as email/password
    login so the rest of the app works unchanged."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(EMERGENT_SESSION_URL, headers={"X-Session-ID": inp.session_id})
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.error(f"google session exchange error: {e}")
        raise HTTPException(status_code=401, detail="Could not verify Google sign-in")

    email = (data.get("email") or "").lower().strip()
    name = data.get("name") or (email.split("@")[0] if email else "Friend")
    picture = data.get("picture")
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    user = await db.users.find_one({"email": email})
    if not user:
        uid = new_id()
        doc = {
            "id": uid,
            "email": email,
            "password_hash": None,
            "auth_provider": "google",
            "picture": picture,
            "is_admin": False,
            "onboarded": False,
            "private_mode": False,
            "profile": {"preferred_name": name, "likes": [], "important_people": [], "goals": [],
                         "communication_style": "warm"},
            "trusted_contact": None,
            "consent": None,
            "country": None,
            "checkin_frequency": "daily",
            "last_checkin": None,
            "created_at": now_iso(),
        }
        await db.users.insert_one(doc)
        user = doc
    else:
        # Link Google to an existing (possibly password-based) account; keep data.
        updates = {}
        if picture and not user.get("picture"):
            updates["picture"] = picture
        if not user.get("auth_provider"):
            updates["auth_provider"] = "google" if not user.get("password_hash") else "both"
        if updates:
            await db.users.update_one({"id": user["id"]}, {"$set": updates})
            user.update(updates)

    return {"token": create_token(user["id"], user.get("token_version", 0)), "user": _public_user(user)}


@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return _public_user(user)


def _public_user(u):
    return {
        "id": u["id"], "email": u["email"], "is_admin": u.get("is_admin", False),
        "role": u.get("role", "user"),
        "onboarded": u.get("onboarded", False), "private_mode": u.get("private_mode", False),
        "profile": u.get("profile", {}), "trusted_contact": u.get("trusted_contact"),
        "country": u.get("country"), "checkin_frequency": u.get("checkin_frequency", "daily"),
        "plus": _plus_state(u),
    }


# ---------------- Onboarding / profile ----------------
@api.post("/onboarding")
async def onboarding(inp: OnboardingInput, user=Depends(get_current_user)):
    if not inp.age_confirmed:
        raise HTTPException(status_code=400, detail="You must confirm you are 18 or older.")
    if not inp.safety_consent:
        raise HTTPException(status_code=400, detail="Safety consent is required to continue.")
    update = {
        "onboarded": True,
        "country": inp.country,
        "checkin_frequency": inp.checkin_frequency,
        "trusted_contact": inp.trusted_contact.model_dump(),
        "consent": {"safety_alert": True, "age_confirmed": True, "timestamp": now_iso()},
        "profile.preferred_name": inp.preferred_name,
        "profile.communication_style": inp.communication_style,
    }
    await db.users.update_one({"id": user["id"]}, {"$set": update})
    fresh = await db.users.find_one({"id": user["id"]})
    return _public_user(fresh)


@api.get("/profile")
async def get_profile(user=Depends(get_current_user)):
    return _public_user(user)


@api.put("/profile")
async def update_profile(inp: ProfileUpdate, user=Depends(get_current_user)):
    data = inp.model_dump(exclude_none=True)
    setter = {}
    for k in ["preferred_name", "work", "education", "likes", "important_people", "goals", "communication_style"]:
        if k in data:
            setter[f"profile.{k}"] = data[k]
    for k in ["checkin_frequency", "country"]:
        if k in data:
            setter[k] = data[k]
    if "trusted_contact" in data:
        setter["trusted_contact"] = data["trusted_contact"]
    if setter:
        await db.users.update_one({"id": user["id"]}, {"$set": setter})
    fresh = await db.users.find_one({"id": user["id"]})
    return _public_user(fresh)


@api.put("/settings/private-mode")
async def set_private_mode(inp: PrivateModeInput, user=Depends(get_current_user)):
    await db.users.update_one({"id": user["id"]}, {"$set": {"private_mode": inp.enabled}})
    return {"private_mode": inp.enabled}


# ---------------- Meta ----------------
@api.get("/meta/countries")
async def meta_countries():
    return country_list()


@api.get("/meta/detect-country")
async def detect_country(request: Request):
    code = request.headers.get("CF-IPCountry") or request.headers.get("cf-ipcountry")
    if code and code.upper() in COUNTRY_NAMES:
        return {"country": code.upper(), "name": COUNTRY_NAMES[code.upper()]}
    return {"country": None, "name": None}


@api.get("/meta/hotlines")
async def meta_hotlines(country: str = None, user=Depends(get_current_user)):
    cc = country or user.get("country")
    return {"country": cc, "hotlines": get_hotlines(cc)}


# ---------------- Sessions ----------------
@api.get("/sessions")
async def list_sessions(user=Depends(get_current_user)):
    return await db.sessions.find({"user_id": user["id"]}, {"_id": 0}).sort("updated_at", -1).to_list(100)


@api.post("/sessions")
async def create_session(inp: SessionCreate, user=Depends(get_current_user)):
    doc = {
        "id": new_id(), "user_id": user["id"],
        "title": inp.title or "New conversation",
        "private": inp.private or user.get("private_mode", False),
        "created_at": now_iso(), "updated_at": now_iso(),
    }
    await db.sessions.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str, user=Depends(get_current_user)):
    sess = await db.sessions.find_one({"id": session_id, "user_id": user["id"]}, {"_id": 0})
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    msgs = await db.messages.find({"session_id": session_id}, {"_id": 0}).sort("created_at", 1).to_list(1000)
    return {"session": sess, "messages": msgs}


@api.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user=Depends(get_current_user)):
    await db.sessions.delete_one({"id": session_id, "user_id": user["id"]})
    await db.messages.delete_many({"session_id": session_id})
    await db.memories.delete_many({"user_id": user["id"], "session_id": session_id, "tier": {"$ne": "LONG_TERM"}})
    return {"ok": True}


# ---------------- Chat (SSE stream) ----------------
@api.post("/chat/stream")
async def chat_stream(inp: ChatInput, user=Depends(get_current_user)):
    private = inp.private or user.get("private_mode", False)
    session_id = inp.session_id
    if session_id:
        sess = await db.sessions.find_one({"id": session_id, "user_id": user["id"]})
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session_id = new_id()
        await db.sessions.insert_one({
            "id": session_id, "user_id": user["id"],
            "title": inp.message[:40] or "New conversation",
            "private": private, "created_at": now_iso(), "updated_at": now_iso(),
        })

    user_msg = {
        "id": new_id(), "session_id": session_id, "user_id": user["id"],
        "role": "user", "content": inp.message, "private": private,
        "image_path": inp.image_path, "created_at": now_iso(),
    }
    await db.messages.insert_one(dict(user_msg))

    image_b64 = None
    if inp.image_path:
        try:
            raw_bytes, _ct = get_object(inp.image_path)
            image_b64 = base64.b64encode(raw_bytes).decode("utf-8")
        except Exception as e:
            logger.error(f"image load failed: {e}")

    risk = await classify_message(router_engine, inp.message or "shared an image", session_id)

    transcript = await recent_transcript(session_id)
    memory_ctx = "" if private else await build_memory_context(db, user["id"])
    system = build_system_prompt(user, memory_ctx, transcript, risk)

    if not private and _plus_state(user)["active"] and risk == "none":
        coach = await _wellness_coach_context(user)
        if coach:
            system += (
                "\n\nWELLNESS COACH: This person is on CampionAI Plus. Where it feels natural (not forced), "
                "gently reference or encourage their plan below. Celebrate what they've done, softly nudge what's pending. "
                "Never nag.\n" + coach
            )

    escalation = None
    if risk == "high":
        escalation = await _trigger_escalation(user, session_id, inp.message)

    async def gen():
        yield _sse({"type": "meta", "session_id": session_id, "risk": risk, "private": private})
        full = ""
        try:
            async for chunk in router_engine.stream(system, inp.message or "I'm sharing an image with you — take a look.", tier=("powerful" if risk in ("high", "medium") else "medium"), session_id=session_id, image_b64=image_b64):
                full += chunk
                yield _sse({"type": "delta", "content": chunk})
        except Exception as e:
            logger.exception("stream error")
            fallback = "I'm right here with you. I had a little trouble responding just then — can you tell me a bit more?"
            full = full or fallback
            yield _sse({"type": "delta", "content": full})

        assistant_msg = {
            "id": new_id(), "session_id": session_id, "user_id": user["id"],
            "role": "assistant", "content": full, "risk": risk, "private": private, "created_at": now_iso(),
        }
        await db.messages.insert_one(dict(assistant_msg))
        await db.sessions.update_one({"id": session_id}, {"$set": {"updated_at": now_iso()}})

        saved = []
        if not private:
            saved = await extract_memories(router_engine, db, user["id"], session_id, inp.message, private)

        yield _sse({"type": "done", "escalation": escalation, "memories_saved": len(saved), "risk": risk})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"})


def _sse(obj):
    return f"data: {json.dumps(obj)}\n\n"


async def _wellness_coach_context(user) -> str:
    today = datetime.now(timezone.utc).date().isoformat()
    plan = await db.wellness_plans.find_one({"user_id": user["id"], "date": today}, {"_id": 0})
    if not plan:
        return ""
    done = [i["title"] for i in plan["items"] if i.get("done")]
    pending = [i["title"] for i in plan["items"] if not i.get("done")]
    parts = []
    if done:
        parts.append("Done today: " + ", ".join(done))
    if pending:
        parts.append("Still pending: " + ", ".join(pending))
    return "Today's wellness plan — " + "; ".join(parts) if parts else ""


async def _find_crisis_doctor(user):
    """Prefer a verified doctor who is online in the user's country, then any online
    doctor, then any verified doctor at all. Returns (doctor, is_online)."""
    country = (user.get("country") or "").upper()
    verified = await db.doctors.find({"status": "verified"}, {"_id": 0}).to_list(200)
    if not verified:
        return None, False
    online = [d for d in verified if doctor_is_online(d)]
    for pool in (
        [d for d in online if d.get("country") == country],
        online,
        [d for d in verified if d.get("country") == country],
        verified,
    ):
        if pool:
            pool.sort(key=lambda d: (not d.get("is_volunteer"), -float(d.get("rating_avg", 0) or 0)))
            return pool[0], doctor_is_online(pool[0])
    return None, False


async def _trigger_escalation(user, session_id, trigger_text):
    tc = user.get("trusted_contact")
    hotlines = get_hotlines(user.get("country"))
    prof, prof_online = await _find_crisis_doctor(user)
    name = user.get("profile", {}).get("preferred_name") or "someone you care about"
    actions = ["Crisis hotlines surfaced"]
    tc_notified = False
    prof_notified = False

    if tc:
        subject = f"CampionAI safety alert regarding {name}"
        text = (
            f"CampionAI safety alert: {name} may be going through a serious crisis right now and listed you as their "
            f"trusted contact. Please reach out to them as soon as you can. If it's an emergency, call your local emergency number."
        )
        html = (
            f"<div style='font-family:sans-serif;line-height:1.6'><h2 style='color:#E11D48'>CampionAI safety alert</h2>"
            f"<p><b>{name}</b> may be going through a serious crisis and listed you as their trusted contact.</p>"
            f"<p>Please reach out to them as soon as you can. If it's an emergency, call your local emergency number.</p>"
            f"<p style='color:#888;font-size:12px'>You are receiving this because you were named as a trusted emergency contact in CampionAI.</p></div>"
        )
        results = await alert_contact(tc.get("name", ""), tc.get("email"), tc.get("phone"), subject, text, html)
        tc_notified = any(r.get("sent") for r in results)
        actions.append(summarize(results, f"Trusted contact ({tc.get('name')})"))

    if prof:
        subject = f"CampionAI handoff: a user may need support"
        text = f"CampionAI detected a high-risk conversation for user {user['email']}. Please review for professional follow-up."
        html = f"<div style='font-family:sans-serif'><h3>CampionAI professional handoff</h3><p>High-risk conversation detected for <b>{user['email']}</b>. Please review for follow-up.</p></div>"
        presults = await alert_contact(prof.get("name", ""), prof.get("email") or prof.get("contact"), prof.get("phone"), subject, text, html)
        prof_notified = any(r.get("sent") for r in presults)
        actions.append(summarize(presults, f"Doctor ({prof.get('name')})"))

    event = {
        "id": new_id(), "user_id": user["id"], "user_email": user["email"], "session_id": session_id,
        "risk_level": "high", "trigger_text": trigger_text[:500],
        "actions_taken": actions, "resolved": False, "created_at": now_iso(),
    }
    await db.safety_events.insert_one(dict(event))
    return {
        "triggered": True,
        "trusted_contact": tc,
        "trusted_contact_notified": tc_notified,
        "professional": public_doctor(prof) if prof else None,
        "professional_notified": prof_notified,
        "hotlines": hotlines,
        # A crisis consult is never capped and never gated on billing state.
        "consult_offer": ({
            "doctor_id": prof["id"],
            "doctor_name": prof.get("name"),
            "online_now": prof_online,
            "free": True,
        } if prof else None),
        "message": "You matter, and you don't have to go through this alone. I've surfaced people who can help right now.",
    }


# ---------------- Check-in engine (deterministic scheduling) ----------------
@api.get("/checkin")
async def checkin(user=Depends(get_current_user)):
    freq = user.get("checkin_frequency", "daily")
    interval = CHECKIN_INTERVALS.get(freq)
    if interval is None:
        return {"due": False}
    last = user.get("last_checkin")
    if last:
        last_dt = datetime.fromisoformat(last)
        if datetime.now(timezone.utc) - last_dt < timedelta(hours=interval):
            return {"due": False}
    memory_ctx = await build_memory_context(db, user["id"])
    name = user.get("profile", {}).get("preferred_name") or "there"

    # Pull recent moments from the last few conversations for a truly personal reference
    recent_user_msgs = await db.messages.find(
        {"user_id": user["id"], "role": "user", "private": {"$ne": True}}, {"_id": 0, "content": 1}
    ).sort("created_at", -1).to_list(6)
    recent_session = await db.sessions.find_one(
        {"user_id": user["id"]}, {"_id": 0, "updated_at": 1}, sort=[("updated_at", -1)]
    )
    days_since = ""
    if recent_session and recent_session.get("updated_at"):
        try:
            gap = datetime.now(timezone.utc) - datetime.fromisoformat(recent_session["updated_at"])
            if gap.days >= 2:
                days_since = f"It's been about {gap.days} days since you last talked. "
        except Exception:
            pass
    recent_block = ""
    if recent_user_msgs:
        snippets = " | ".join(m["content"][:120] for m in reversed(recent_user_msgs))
        recent_block = f"\nRecent things they mentioned: {snippets}"

    sys = (
        "You are CampionAI reaching out first with a proactive, thoughtful check-in with your friend. "
        "Write ONE short, warm, specific opening message (1-2 sentences). "
        "If you can, gently reference a real recent moment or something you know about them so it feels personal, not generic. "
        "Vary your opening — don't always start with 'Hey'. Sound like a caring friend, never a notification. Avoid emojis. "
        f"{days_since}"
        + ("\n" + memory_ctx if memory_ctx else "")
        + recent_block
    )
    try:
        msg = await router_engine.complete(sys, f"Reach out to {name} now.", tier="medium", session_id=f"checkin-{user['id']}-{now_iso()}")
    except Exception:
        msg = f"{name}, you crossed my mind today — how are you really doing?"
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_checkin": now_iso()}})
    return {"due": True, "message": msg.strip()}


# ---------------- Memory controls ----------------
@api.get("/memories")
async def list_memories(user=Depends(get_current_user)):
    mems = await db.memories.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return mems


@api.put("/memories/{memory_id}")
async def update_memory(memory_id: str, inp: MemoryUpdate, user=Depends(get_current_user)):
    data = inp.model_dump(exclude_none=True)
    res = await db.memories.update_one({"id": memory_id, "user_id": user["id"]}, {"$set": data}) if data else None
    if res is not None and res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"ok": True}


@api.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str, user=Depends(get_current_user)):
    res = await db.memories.delete_one({"id": memory_id, "user_id": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"ok": True}


# ---------------- Human handoff ----------------
@api.post("/safety/handoff")
async def request_handoff(user=Depends(get_current_user)):
    prof, _prof_online = await _find_crisis_doctor(user)
    profile = user.get("profile", {})
    summary = {
        "preferred_name": profile.get("preferred_name"),
        "communication_style": profile.get("communication_style"),
        "goals": profile.get("goals", []),
        "important_people": profile.get("important_people", []),
        "consented": True,
    }
    actions = ["User-initiated handoff"]
    if prof:
        subject = "CampionAI: a user requested to talk with you"
        text = f"{profile.get('preferred_name') or user['email']} requested a human handoff via CampionAI and consented to share a brief summary. Please follow up."
        html = (
            f"<div style='font-family:sans-serif;line-height:1.6'><h3>CampionAI handoff request</h3>"
            f"<p><b>{profile.get('preferred_name') or user['email']}</b> requested to talk with a human and consented to share a summary.</p>"
            f"<p><b>Style:</b> {profile.get('communication_style','—')}<br/><b>Goals:</b> {', '.join(profile.get('goals', [])) or '—'}</p></div>"
        )
        results = await alert_contact(prof.get("name", ""), prof.get("email") or prof.get("contact"), prof.get("phone"), subject, text, html)
        actions.append(summarize(results, f"Doctor ({prof.get('name')})"))
    else:
        actions.append("Matched: pending")
    event = {
        "id": new_id(), "user_id": user["id"], "user_email": user["email"], "session_id": None,
        "risk_level": "handoff_request", "trigger_text": "User requested human handoff",
        "actions_taken": actions, "resolved": False, "created_at": now_iso(),
    }
    await db.safety_events.insert_one(dict(event))
    return {"professional": prof, "consented_summary": summary, "hotlines": get_hotlines(user.get("country"))}


# ---------------- Voice (Fish Audio TTS + browser STT) ----------------
async def _voice_settings():
    doc = await db.voice_settings.find_one({"id": "global"}, {"_id": 0}) or {}
    key = doc.get("fish_audio_api_key") or os.environ.get("FISH_AUDIO_API_KEY", "")
    return {
        "enabled": doc.get("enabled", True) and bool(key),
        "voice_id": doc.get("voice_id") or os.environ.get("FISH_AUDIO_VOICE_ID", ""),
        "key": key,
    }


@api.get("/voice/status")
async def voice_status(user=Depends(get_current_user)):
    s = await _voice_settings()
    return {"enabled": s["enabled"]}


@api.post("/voice/tts")
async def voice_tts(inp: TTSInput, user=Depends(get_current_user)):
    s = await _voice_settings()
    if not s["enabled"] or not s["key"]:
        raise HTTPException(status_code=400, detail="Voice is not configured. Add a Fish Audio key in Admin > Voice.")
    try:
        audio = await synthesize(inp.text, s["key"], s["voice_id"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Voice synthesis failed: {e}")
    return Response(content=audio, media_type="audio/mpeg")


@api.get("/safety/events")
async def my_safety_events(user=Depends(get_current_user)):
    return await db.safety_events.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)


# ---------------- Data controls ----------------
@api.get("/data/export")
async def export_data(user=Depends(get_current_user)):
    sessions = await db.sessions.find({"user_id": user["id"]}, {"_id": 0}).to_list(1000)
    messages = await db.messages.find({"user_id": user["id"]}, {"_id": 0}).to_list(100000)
    memories = await db.memories.find({"user_id": user["id"]}, {"_id": 0}).to_list(10000)
    return {
        "exported_at": now_iso(),
        "profile": _public_user(user),
        "sessions": sessions, "messages": messages, "memories": memories,
    }


@api.delete("/data/delete-everything")
async def delete_everything(user=Depends(get_current_user)):
    await db.sessions.delete_many({"user_id": user["id"]})
    await db.messages.delete_many({"user_id": user["id"]})
    await db.memories.delete_many({"user_id": user["id"]})
    await db.safety_events.delete_many({"user_id": user["id"]})
    await db.users.delete_one({"id": user["id"]})
    return {"ok": True, "deleted": True}


# ---------------- Admin ----------------
@api.get("/admin/stats")
async def admin_stats(admin=Depends(get_admin_user)):
    return {
        "users": await db.users.count_documents({}),
        "sessions": await db.sessions.count_documents({}),
        "messages": await db.messages.count_documents({}),
        "memories": await db.memories.count_documents({}),
        "safety_events": await db.safety_events.count_documents({}),
        "doctors": await db.doctors.count_documents({"status": "verified"}),
        "doctors_pending": await db.doctors.count_documents({"status": "pending"}),
        "consults": await db.consult_sessions.count_documents({"status": "completed"}),
        "open_safety_events": await db.safety_events.count_documents({"resolved": False}),
    }


@api.get("/admin/model-config")
async def get_model_config(admin=Depends(get_admin_user)):
    routes = dict(DEFAULT_ROUTES)
    async for doc in db.model_config.find({}, {"_id": 0}):
        routes[doc["tier"]] = {"provider": doc["provider"], "model": doc["model"]}
    return routes


@api.put("/admin/model-config")
async def set_model_config(inp: ModelRouteConfig, admin=Depends(get_admin_user)):
    await db.model_config.update_one(
        {"tier": inp.tier},
        {"$set": {"tier": inp.tier, "provider": inp.provider, "model": inp.model}},
        upsert=True,
    )
    return {"ok": True}


@api.get("/admin/provider-settings")
async def get_provider_settings(admin=Depends(get_admin_user)):
    s = await db.provider_settings.find_one({"id": "global"}, {"_id": 0})
    if not s:
        s = {"llm_provider": os.environ.get("LLM_PROVIDER", "emergent"), "openrouter_api_key": ""}
    s["openrouter_api_key_set"] = bool(s.get("openrouter_api_key"))
    s.pop("openrouter_api_key", None)
    return s


@api.put("/admin/provider-settings")
async def set_provider_settings(inp: ProviderSettings, admin=Depends(get_admin_user)):
    existing = await db.provider_settings.find_one({"id": "global"}, {"_id": 0}) or {}
    has_key = bool(inp.openrouter_api_key or existing.get("openrouter_api_key") or os.environ.get("OPENROUTER_API_KEY"))
    if inp.llm_provider == "openrouter" and not has_key:
        raise HTTPException(status_code=400, detail="Add an OpenRouter API key before switching to OpenRouter.")
    setter = {"id": "global", "llm_provider": inp.llm_provider}
    if inp.openrouter_api_key:
        setter["openrouter_api_key"] = inp.openrouter_api_key
    await db.provider_settings.update_one({"id": "global"}, {"$set": setter}, upsert=True)
    return {"ok": True}


@api.get("/admin/openrouter-models")
async def admin_openrouter_models(admin=Depends(get_admin_user)):
    s = await db.provider_settings.find_one({"id": "global"}, {"_id": 0})
    key = (s or {}).get("openrouter_api_key", "") or os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise HTTPException(status_code=400, detail="Add an OpenRouter API key first.")
    try:
        return {"models": await list_openrouter_models(key)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch OpenRouter models: {e}")


@api.get("/admin/safety-events")
async def admin_safety_events(admin=Depends(get_admin_user)):
    return await db.safety_events.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)


@api.put("/admin/safety-events/{eid}/resolve")
async def resolve_safety_event(eid: str, admin=Depends(get_admin_user)):
    res = await db.safety_events.update_one({"id": eid}, {"$set": {"resolved": True, "resolved_at": now_iso()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Safety event not found")
    return {"ok": True}


@api.get("/admin/voice-settings")
async def get_voice_settings(admin=Depends(get_admin_user)):
    doc = await db.voice_settings.find_one({"id": "global"}, {"_id": 0}) or {}
    key = doc.get("fish_audio_api_key") or os.environ.get("FISH_AUDIO_API_KEY", "")
    return {
        "enabled": doc.get("enabled", True),
        "voice_id": doc.get("voice_id") or os.environ.get("FISH_AUDIO_VOICE_ID", ""),
        "key_set": bool(key),
    }


@api.put("/admin/voice-settings")
async def set_voice_settings(inp: VoiceSettingsInput, admin=Depends(get_admin_user)):
    setter = {"id": "global", "enabled": inp.enabled}
    if inp.voice_id is not None:
        setter["voice_id"] = inp.voice_id
    if inp.fish_audio_api_key:
        setter["fish_audio_api_key"] = inp.fish_audio_api_key
    await db.voice_settings.update_one({"id": "global"}, {"$set": setter}, upsert=True)
    return {"ok": True}


@api.get("/admin/integrations")
async def integrations_status(admin=Depends(get_admin_user)):
    voice = await db.voice_settings.find_one({"id": "global"}, {"_id": 0}) or {}
    fish_key = voice.get("fish_audio_api_key") or os.environ.get("FISH_AUDIO_API_KEY", "")
    return {
        "email_resend": bool(os.environ.get("RESEND_API_KEY", "").strip()),
        "sms_twilio": bool(os.environ.get("TWILIO_ACCOUNT_SID", "").strip() and os.environ.get("TWILIO_AUTH_TOKEN", "").strip() and os.environ.get("TWILIO_FROM_NUMBER", "").strip()),
        "voice_fish": bool(fish_key),
        "paypal": bool(os.environ.get("PAYPAL_CLIENT_ID", "").strip() and os.environ.get("PAYPAL_SECRET", "").strip()),
        "paypal_webhook": bool(os.environ.get("PAYPAL_WEBHOOK_ID", "").strip()),
        "paypal_plans": bool((await db.provider_settings.find_one({"id": "global"}, {"_id": 0}) or {}).get("paypal_plans")),
        "kyc": bool(os.environ.get("KYC_API_KEY", "").strip()),
        "turn": bool(os.environ.get("TURN_SECRET", "").strip()),
    }


# ---------------- Uploads (object storage) ----------------
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def safe_ext(filename: str) -> str:
    """Storage-key-safe extension. filename is attacker-controlled and may contain
    slashes or dot-segments, which would escape the user's object-store prefix."""
    raw = filename.rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""
    return re.sub(r"[^a-z0-9]", "", raw)[:8] or "bin"


async def read_capped(file: UploadFile) -> bytes:
    """Read an upload in chunks so an oversized body is rejected, not fully buffered."""
    chunks, size = [], 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")
        chunks.append(chunk)
    return b"".join(chunks)


@api.post("/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    ext = safe_ext(file.filename)
    content_type = file.content_type or MIME_TYPES.get(ext, "application/octet-stream")
    data = await read_capped(file)
    path = f"{APP_NAME}/uploads/{user['id']}/{new_id()}.{ext}"
    try:
        result = put_object(path, data, content_type)
    except Exception as e:
        logger.error(f"upload failed: {e}")
        raise HTTPException(status_code=502, detail="Upload failed")
    doc = {
        "id": new_id(), "user_id": user["id"], "storage_path": result["path"],
        "original_filename": file.filename, "content_type": content_type,
        "size": result.get("size", len(data)), "is_image": content_type.startswith("image/"),
        "is_deleted": False, "created_at": now_iso(),
    }
    await db.files.insert_one(dict(doc))
    return {"file_id": doc["id"], "path": result["path"], "content_type": content_type, "is_image": doc["is_image"]}


@api.get("/files/{path:path}")
async def serve_file(path: str, auth: str = Query(None)):
    if not auth:
        raise HTTPException(status_code=401, detail="Missing auth")
    # ponytail: token still arrives as a query param so <img src> works. It now honours
    # revocation, but it still lands in access logs — swap for signed short-lived URLs.
    user = await authenticate(auth)
    record = await db.files.find_one({"storage_path": path, "user_id": user["id"], "is_deleted": False}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        data, content_type = get_object(path)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")
    return Response(content=data, media_type=record.get("content_type", content_type))


# ---------------- Payments (PayPal only) ----------------
TRIAL_DAYS = 14
RENEWAL_GRACE_DAYS = 2  # a late renewal webhook must not lock someone out mid-cycle

PACKAGES = {
    "plus_monthly": {"amount": 9.0, "type": "subscription", "period_days": 30, "label": "CampionAI Plus · Monthly"},
    "plus_yearly": {"amount": 86.40, "type": "subscription", "period_days": 365, "label": "CampionAI Plus · Yearly"},
    "donate_5": {"amount": 5.0, "type": "donation", "label": "Supporter"},
    "donate_15": {"amount": 15.0, "type": "donation", "label": "Sustainer"},
    "donate_30": {"amount": 30.0, "type": "donation", "label": "Champion"},
}

PLAN_KEY_ALIAS = {"monthly": "plus_monthly", "yearly": "plus_yearly"}


async def _paypal_plan_ids():
    s = await db.provider_settings.find_one({"id": "global"}, {"_id": 0}) or {}
    return s.get("paypal_plans") or {}


@api.get("/pricing")
async def pricing():
    """Single source of truth for prices. The UI renders from this, so changing a
    price never means editing the frontend."""
    plans = await _paypal_plan_ids()
    monthly = PACKAGES["plus_monthly"]["amount"]
    yearly = PACKAGES["plus_yearly"]["amount"]
    return {
        "currency": "USD",
        "paypal_client_id": os.environ.get("PAYPAL_CLIENT_ID", "").strip() or None,
        "trial_days": TRIAL_DAYS,
        "plans": [
            {"id": "plus_monthly", "label": PACKAGES["plus_monthly"]["label"], "amount": monthly,
             "per": "/mo", "note": "Billed monthly", "paypal_plan_id": plans.get("plus_monthly")},
            {"id": "plus_yearly", "label": PACKAGES["plus_yearly"]["label"], "amount": yearly,
             "per": "/yr", "note": f"Just ${yearly / 12:.2f}/mo · billed yearly", "featured": True,
             "save": f"Save {round((1 - yearly / (monthly * 12)) * 100)}%",
             "paypal_plan_id": plans.get("plus_yearly")},
        ],
        "donations": [{"id": k, "amount": v["amount"], "label": v["label"]}
                      for k, v in PACKAGES.items() if v["type"] == "donation"],
    }


async def _claim_transaction(session_key: str):
    """Atomically claim an unprocessed transaction.

    Returns the doc if THIS caller won the claim, else None. The webhook and the
    client confirm call routinely race here; whoever loses must do nothing.
    """
    return await db.payment_transactions.find_one_and_update(
        {"session_id": session_key, "granted": {"$ne": True}},
        {"$set": {"granted": True, "status": "completed", "payment_status": "paid", "updated_at": now_iso()}},
        return_document=ReturnDocument.AFTER,
    )


async def _record_donation(record):
    if record.get("anonymous") or not record.get("user_id"):
        return
    amount = float(record.get("amount", 0) or 0)
    name = record.get("donor_name") or "A supporter"
    avatar = f"https://ui-avatars.com/api/?name={name.replace(' ', '+')}&background=1a1a1c&color=fafafa&bold=true"
    await db.donors.update_one(
        {"user_id": record["user_id"]},
        {"$inc": {"total": amount}, "$set": {"name": name, "avatar": avatar, "last_at": now_iso()}},
        upsert=True,
    )


# ---------------- Subscription lifecycle ----------------
PAYPAL_ACTIVE = ("ACTIVE", "APPROVED")


async def _sync_subscription(user_id: str, subscription_id: str, plan_key: str, sub=None):
    """Mirror PayPal's subscription record onto the user. PayPal is the authority for
    status and renewal date — the app no longer computes a period itself."""
    sub = sub if sub is not None else await paypal_get_subscription(subscription_id)
    if not sub:
        return None
    status = (sub.get("status") or "").upper()
    billing = sub.get("billing_info") or {}
    pkg = PACKAGES.get(plan_key, PACKAGES["plus_monthly"])

    user = await db.users.find_one({"id": user_id}, {"_id": 0, "plus": 1}) or {}
    current_until = (user.get("plus") or {}).get("until")

    until = None
    if status in PAYPAL_ACTIVE:
        next_billing = billing.get("next_billing_time")
        if next_billing:
            try:
                until = (datetime.fromisoformat(next_billing.replace("Z", "+00:00"))
                         + timedelta(days=RENEWAL_GRACE_DAYS)).isoformat()
            except Exception:
                until = None
        if not until:
            until = (datetime.now(timezone.utc) + timedelta(days=pkg["period_days"])).isoformat()
        app_status = "active"
    elif status == "SUSPENDED":
        app_status = "past_due"
        until = current_until  # keep access while they fix the payment method
    elif status in ("CANCELLED", "EXPIRED"):
        app_status = "cancelled"
        until = current_until  # already paid through the current period
    else:
        app_status = "pending"
        until = current_until

    await db.users.update_one({"id": user_id}, {"$set": {
        "plus.status": app_status,
        "plus.until": until,
        "plus.paypal_subscription_id": subscription_id,
        "plus.plan_key": plan_key,
        "plus.paypal_status": status,
        "plus.trial_used": True,
        "plus.last_synced": now_iso(),
    }})
    return app_status


@api.post("/paypal/activate")
async def paypal_activate(inp: PaypalActivate, user=Depends(get_current_user)):
    """Fast-path confirm right after the PayPal button approves, so the UI updates
    without waiting for the webhook. The webhook remains the authority."""
    plan_key = PLAN_KEY_ALIAS.get(inp.plan_key, inp.plan_key)
    if plan_key not in ("plus_monthly", "plus_yearly"):
        raise HTTPException(status_code=400, detail="Unknown plan")
    try:
        sub = await paypal_get_subscription(inp.subscription_id)
    except Exception as e:
        logger.error(f"paypal verify error: {e}")
        raise HTTPException(status_code=400, detail="Could not verify PayPal subscription")
    if sub is None:
        raise HTTPException(status_code=400, detail="PayPal is not configured")
    if (sub.get("status") or "").upper() not in PAYPAL_ACTIVE:
        raise HTTPException(status_code=400, detail=f"Subscription not active ({sub.get('status')})")

    session_key = f"paypal-sub-{inp.subscription_id}"
    existing = await db.payment_transactions.find_one({"session_id": session_key}, {"_id": 0})
    if not existing:
        await db.payment_transactions.insert_one({
            "session_id": session_key, "user_id": user["id"], "package_id": plan_key,
            "amount": float(PACKAGES[plan_key]["amount"]), "currency": "usd", "type": "subscription",
            "provider": "paypal", "paypal_subscription_id": inp.subscription_id,
            "status": "completed", "payment_status": "paid", "granted": True,
            "description": PACKAGES[plan_key]["label"],
            "created_at": now_iso(), "updated_at": now_iso(),
        })
    await _sync_subscription(user["id"], inp.subscription_id, plan_key, sub=sub)
    fresh = await db.users.find_one({"id": user["id"]})
    return _plus_state(fresh)


@api.post("/plus/cancel")
async def plus_cancel(user=Depends(get_current_user)):
    """Cancels at PayPal immediately; app access continues to the paid-through date."""
    plus = user.get("plus", {}) or {}
    sub_id = plus.get("paypal_subscription_id")
    if not sub_id:
        raise HTTPException(status_code=400, detail="No active subscription to cancel")
    try:
        await paypal_cancel_subscription(sub_id, "Cancelled from CampionAI")
    except Exception as e:
        logger.error(f"paypal cancel failed: {e}")
        raise HTTPException(status_code=502, detail="Could not cancel with PayPal — please try again")
    await db.users.update_one({"id": user["id"]}, {"$set": {
        "plus.status": "cancelled", "plus.cancel_at_period_end": True, "plus.paypal_status": "CANCELLED",
    }})
    fresh = await db.users.find_one({"id": user["id"]})
    return _plus_state(fresh)


@api.post("/plus/resume")
async def plus_resume(user=Depends(get_current_user)):
    """Only a SUSPENDED subscription can be resumed. A cancelled one is gone at PayPal
    and needs a fresh subscription — say so rather than pretending."""
    plus = user.get("plus", {}) or {}
    sub_id = plus.get("paypal_subscription_id")
    if not sub_id:
        raise HTTPException(status_code=400, detail="No subscription found")
    sub = await paypal_get_subscription(sub_id)
    if not sub:
        raise HTTPException(status_code=400, detail="PayPal is not configured")
    if (sub.get("status") or "").upper() != "SUSPENDED":
        raise HTTPException(status_code=400, detail="This subscription cannot be resumed — please subscribe again")
    await paypal_activate_subscription(sub_id)
    await _sync_subscription(user["id"], sub_id, plus.get("plan_key", "plus_monthly"))
    fresh = await db.users.find_one({"id": user["id"]})
    return _plus_state(fresh)


@api.get("/plus/billing")
async def plus_billing(user=Depends(get_current_user)):
    """Local ledger, enriched with PayPal's own transaction list when available."""
    local = await db.payment_transactions.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)

    remote = []
    sub_id = (user.get("plus", {}) or {}).get("paypal_subscription_id")
    if sub_id:
        try:
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=365 * 3)
            for t in await paypal_subscription_transactions(
                sub_id, start.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ")
            ):
                amt = (t.get("amount_with_breakdown") or {}).get("gross_amount") or {}
                remote.append({
                    "id": t.get("id"), "date": t.get("time"), "status": t.get("status"),
                    "amount": float(amt.get("value", 0) or 0), "currency": amt.get("currency_code", "USD"),
                    "description": "Subscription payment",
                })
        except Exception as e:
            logger.error(f"paypal transactions failed: {e}")

    return {"plus": _plus_state(user), "payments": local, "paypal_payments": remote}


# ---------------- Donations (PayPal Orders) ----------------
@api.post("/donations/order")
async def donation_order(inp: DonationOrder, user=Depends(get_current_user)):
    amount = round(float(inp.amount), 2)
    donor_name = (user.get("profile", {}) or {}).get("preferred_name") or user["email"].split("@")[0]
    try:
        order = await paypal_create_order(amount, "Donation to CampionAI", custom_id=user["id"])
    except Exception as e:
        logger.error(f"paypal order failed: {e}")
        raise HTTPException(status_code=502, detail="Could not start the donation")
    if not order:
        raise HTTPException(status_code=400, detail="PayPal is not configured")
    await db.payment_transactions.insert_one({
        "session_id": f"paypal-order-{order['id']}", "user_id": user["id"], "package_id": "donation",
        "amount": amount, "currency": "usd", "type": "donation", "provider": "paypal",
        "anonymous": bool(inp.anonymous), "donor_name": donor_name,
        "description": "Donation", "status": "initiated", "payment_status": "pending", "granted": False,
        "created_at": now_iso(), "updated_at": now_iso(),
    })
    return {"order_id": order["id"]}


@api.post("/donations/capture/{order_id}")
async def donation_capture(order_id: str, user=Depends(get_current_user)):
    session_key = f"paypal-order-{order_id}"
    record = await db.payment_transactions.find_one({"session_id": session_key}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Order not found")
    if record.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your order")
    try:
        captured = await paypal_capture_order(order_id)
    except Exception as e:
        logger.error(f"paypal capture failed: {e}")
        raise HTTPException(status_code=502, detail="Could not complete the donation")
    if (captured or {}).get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail="Payment was not completed")
    claimed = await _claim_transaction(session_key)
    if claimed:
        await _record_donation(claimed)
    return {"ok": True, "amount": record["amount"]}


@api.post("/contact")
async def submit_contact(inp: ContactInput):
    doc = {
        "id": new_id(),
        "name": inp.name.strip()[:200],
        "email": str(inp.email),
        "subject": (inp.subject or "").strip()[:300],
        "message": inp.message.strip()[:5000],
        "created_at": now_iso(),
        "handled": False,
    }
    await db.contact_messages.insert_one(doc)
    logger.info(f"contact message received from {doc['email']}")
    return {"ok": True, "message": "Thanks for reaching out — we'll get back to you soon."}


@api.get("/donors/top")
async def top_donors():
    donors = await db.donors.find({}, {"_id": 0}).sort("total", -1).to_list(10)
    return [{"name": d.get("name"), "avatar": d.get("avatar"), "total": round(d.get("total", 0), 2)} for d in donors]


# ---------------- PayPal webhook (the authority) ----------------
SUB_EVENTS = {
    "BILLING.SUBSCRIPTION.ACTIVATED", "BILLING.SUBSCRIPTION.RE-ACTIVATED",
    "BILLING.SUBSCRIPTION.CANCELLED", "BILLING.SUBSCRIPTION.SUSPENDED",
    "BILLING.SUBSCRIPTION.EXPIRED", "BILLING.SUBSCRIPTION.UPDATED",
}


@api.post("/webhook/paypal")
async def paypal_webhook(request: Request):
    body = await request.body()
    if not await paypal_verify_webhook(request.headers, body):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    try:
        event = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed webhook")

    etype = event.get("event_type", "")
    resource = event.get("resource", {}) or {}
    logger.info(f"paypal webhook: {etype}")

    # Replay guard — PayPal retries, and a retried ACTIVATED must not re-grant.
    event_id = event.get("id")
    if event_id:
        seen = await db.webhook_events.find_one_and_update(
            {"id": event_id},
            {"$setOnInsert": {"id": event_id, "type": etype, "received_at": now_iso()}},
            upsert=True, return_document=ReturnDocument.BEFORE,
        )
        if seen:
            return {"status": "duplicate"}

    if etype in SUB_EVENTS:
        sub_id = resource.get("id")
        if sub_id:
            tx = await db.payment_transactions.find_one({"paypal_subscription_id": sub_id}, {"_id": 0})
            if tx and tx.get("user_id"):
                await _sync_subscription(tx["user_id"], sub_id, tx.get("package_id", "plus_monthly"), sub=resource)
            else:
                logger.warning(f"webhook for unknown subscription {sub_id}")

    elif etype == "PAYMENT.SALE.COMPLETED":
        sub_id = resource.get("billing_agreement_id")
        if sub_id:
            tx = await db.payment_transactions.find_one({"paypal_subscription_id": sub_id}, {"_id": 0})
            if tx and tx.get("user_id"):
                plan_key = tx.get("package_id", "plus_monthly")
                amount = float((resource.get("amount") or {}).get("total", 0) or 0)
                sale_key = f"paypal-sale-{resource.get('id')}"
                await db.payment_transactions.update_one(
                    {"session_id": sale_key},
                    {"$setOnInsert": {
                        "session_id": sale_key, "user_id": tx["user_id"], "package_id": plan_key,
                        "amount": amount, "currency": "usd", "type": "subscription", "provider": "paypal",
                        "paypal_subscription_id": sub_id, "description": "Subscription renewal",
                        "status": "completed", "payment_status": "paid", "granted": True,
                        "created_at": now_iso(), "updated_at": now_iso(),
                    }}, upsert=True,
                )
                # Re-read from PayPal so `until` tracks the real next billing date.
                await _sync_subscription(tx["user_id"], sub_id, plan_key)

    elif etype == "BILLING.SUBSCRIPTION.PAYMENT.FAILED":
        sub_id = resource.get("id")
        tx = await db.payment_transactions.find_one({"paypal_subscription_id": sub_id}, {"_id": 0}) if sub_id else None
        if tx and tx.get("user_id"):
            await db.users.update_one({"id": tx["user_id"]}, {"$set": {"plus.status": "past_due"}})
            u = await db.users.find_one({"id": tx["user_id"]}, {"_id": 0, "email": 1, "profile": 1})
            if u:
                name = (u.get("profile") or {}).get("preferred_name") or "there"
                await alert_contact(
                    name, u.get("email"), None,
                    "CampionAI Plus — payment issue",
                    "We could not process your latest CampionAI Plus payment. Please update your payment method in PayPal to keep your plan active.",
                    "<div style='font-family:sans-serif;line-height:1.6'><h3>Payment issue</h3>"
                    "<p>We could not process your latest CampionAI Plus payment. Update your payment method in PayPal to keep your plan active.</p></div>",
                )

    return {"status": "ok"}


# ---------------- Plus (subscription + 14-day trial) ----------------
def _plus_state(user):
    plus = user.get("plus", {}) or {}
    now = datetime.now(timezone.utc)
    active, status = False, plus.get("status", "none")
    until = plus.get("until")
    trial_ends = plus.get("trial_ends_at")
    if until:
        try:
            if datetime.fromisoformat(until) > now:
                active, status = True, "active"
        except Exception:
            pass
    if not active and trial_ends:
        try:
            if datetime.fromisoformat(trial_ends) > now:
                active, status = True, "trialing"
        except Exception:
            pass
    return {
        "active": active, "status": status, "until": until,
        "trial_ends_at": trial_ends, "trial_used": plus.get("trial_used", False),
        "plan_key": plus.get("plan_key"),
        "paypal_status": plus.get("paypal_status"),
        "cancel_at_period_end": plus.get("cancel_at_period_end", False),
        "has_subscription": bool(plus.get("paypal_subscription_id")),
    }


@api.get("/plus/status")
async def plus_status(user=Depends(get_current_user)):
    return _plus_state(user)


@api.post("/plus/start-trial")
async def start_trial(user=Depends(get_current_user)):
    plus = user.get("plus", {}) or {}
    if plus.get("trial_used") or plus.get("until"):
        raise HTTPException(status_code=400, detail="Trial already used")
    trial_ends = (datetime.now(timezone.utc) + timedelta(days=TRIAL_DAYS)).isoformat()
    await db.users.update_one({"id": user["id"]}, {"$set": {
        "plus.status": "trialing", "plus.trial_ends_at": trial_ends, "plus.trial_used": True,
    }})
    fresh = await db.users.find_one({"id": user["id"]})
    return _plus_state(fresh)


async def require_plus(user=Depends(get_current_user)):
    if not _plus_state(user)["active"]:
        raise HTTPException(status_code=402, detail="CampionAI Plus required")
    return user


# ---------------- Wellness ----------------
PLAN_SYSTEM = """You are CampionAI creating a personalized daily wellness plan for your friend.
Return ONLY a JSON array of 4-6 items. Each item:
{"type": "meditation|yoga|breathing|movement|task", "title": "<short>", "detail": "<one gentle sentence>", "duration_min": <int>, "time_of_day": "morning|afternoon|evening"}
Base it on their goals/profile if given. Mix calming practices (meditation/yoga/breathing) with 1-2 real-life behavioral tasks (e.g. a short walk, message a friend). Keep it doable and kind. JSON array only."""


async def _generate_plan(user, date_str):
    profile = user.get("profile", {})
    ctx = f"Name: {profile.get('preferred_name')}. Goals: {', '.join(profile.get('goals', [])) or 'general wellbeing'}. Likes: {', '.join(profile.get('likes', [])) or '—'}."
    try:
        raw = await router_engine.complete(PLAN_SYSTEM, ctx, tier="medium", session_id=f"plan-{user['id']}-{date_str}")
    except Exception:
        raw = "[]"
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
    s, e = raw.find("["), raw.rfind("]")
    items = []
    if s != -1 and e != -1:
        try:
            items = json.loads(raw[s:e + 1])
        except Exception:
            items = []
    if not items:
        items = [
            {"type": "breathing", "title": "Morning reset", "detail": "Three minutes of slow box breathing to start gently.", "duration_min": 3, "time_of_day": "morning"},
            {"type": "movement", "title": "Short walk", "detail": "A 15-minute walk, phone in your pocket.", "duration_min": 15, "time_of_day": "afternoon"},
            {"type": "meditation", "title": "Evening wind-down", "detail": "A 10-minute body scan before bed.", "duration_min": 10, "time_of_day": "evening"},
            {"type": "task", "title": "Reach out", "detail": "Send one message to someone you care about.", "duration_min": 5, "time_of_day": "afternoon"},
        ]
    for it in items:
        it["done"] = False
    doc = {"id": new_id(), "user_id": user["id"], "date": date_str, "items": items, "generated_at": now_iso()}
    return doc


@api.get("/wellness/plan")
async def get_plan(user=Depends(require_plus)):
    today = datetime.now(timezone.utc).date().isoformat()
    plan = await db.wellness_plans.find_one({"user_id": user["id"], "date": today}, {"_id": 0})
    if not plan:
        plan = await _generate_plan(user, today)
        await db.wellness_plans.insert_one(dict(plan))
        plan.pop("_id", None)
    return plan


@api.post("/wellness/plan/regenerate")
async def regenerate_plan(user=Depends(require_plus)):
    today = datetime.now(timezone.utc).date().isoformat()
    plan = await _generate_plan(user, today)
    await db.wellness_plans.update_one({"user_id": user["id"], "date": today}, {"$set": dict(plan)}, upsert=True)
    return plan


@api.put("/wellness/plan/toggle")
async def toggle_plan_item(inp: PlanItemToggle, user=Depends(require_plus)):
    today = datetime.now(timezone.utc).date().isoformat()
    plan = await db.wellness_plans.find_one({"user_id": user["id"], "date": today})
    if not plan or inp.item_index >= len(plan["items"]):
        raise HTTPException(status_code=404, detail="Item not found")
    plan["items"][inp.item_index]["done"] = not plan["items"][inp.item_index].get("done", False)
    await db.wellness_plans.update_one({"id": plan["id"]}, {"$set": {"items": plan["items"]}})
    return {"ok": True, "items": plan["items"]}


@api.post("/wellness/plan/item")
async def add_plan_item(inp: PlanItemAdd, user=Depends(require_plus)):
    """Let a user hand-add their own to-do to today's plan (not just AI-generated)."""
    today = datetime.now(timezone.utc).date().isoformat()
    plan = await db.wellness_plans.find_one({"user_id": user["id"], "date": today})
    if not plan:
        plan = await _generate_plan(user, today)
        await db.wellness_plans.insert_one(dict(plan))
    item = {
        "type": inp.type or "task", "title": inp.title, "detail": inp.detail or "",
        "duration_min": int(inp.duration_min or 10), "time_of_day": inp.time_of_day or "morning",
        "done": False, "custom": True,
    }
    items = plan["items"] + [item]
    await db.wellness_plans.update_one({"id": plan["id"]}, {"$set": {"items": items}})
    return {"ok": True, "items": items}


@api.delete("/wellness/plan/item/{index}")
async def delete_plan_item(index: int, user=Depends(require_plus)):
    today = datetime.now(timezone.utc).date().isoformat()
    plan = await db.wellness_plans.find_one({"user_id": user["id"], "date": today})
    if not plan or index < 0 or index >= len(plan["items"]):
        raise HTTPException(status_code=404, detail="Item not found")
    items = [it for i, it in enumerate(plan["items"]) if i != index]
    await db.wellness_plans.update_one({"id": plan["id"]}, {"$set": {"items": items}})
    return {"ok": True, "items": items}


@api.put("/wellness/plan/reorder")
async def reorder_plan_items(inp: PlanReorder, user=Depends(require_plus)):
    today = datetime.now(timezone.utc).date().isoformat()
    plan = await db.wellness_plans.find_one({"user_id": user["id"], "date": today})
    if not plan:
        raise HTTPException(status_code=404, detail="No plan yet")
    n = len(plan["items"])
    if sorted(inp.order) != list(range(n)):
        raise HTTPException(status_code=400, detail="Invalid order")
    items = [plan["items"][i] for i in inp.order]
    await db.wellness_plans.update_one({"id": plan["id"]}, {"$set": {"items": items}})
    return {"ok": True, "items": items}


@api.get("/wellness/streak")
async def wellness_streak(user=Depends(require_plus)):
    """Consecutive days (ending today or yesterday) where every plan item was done."""
    plans = await db.wellness_plans.find(
        {"user_id": user["id"]}, {"_id": 0, "date": 1, "items": 1}
    ).sort("date", -1).to_list(400)
    done_by_date = {}
    for p in plans:
        items = p.get("items") or []
        done_by_date[p["date"]] = bool(items) and all(i.get("done") for i in items)
    today = datetime.now(timezone.utc).date()
    # Allow the streak to "hold" if today isn't complete yet — start from today,
    # but if today isn't done, don't break it (count from yesterday).
    current = 0
    d = today
    if not done_by_date.get(d.isoformat()):
        d = today - timedelta(days=1)
    while done_by_date.get(d.isoformat()):
        current += 1
        d = d - timedelta(days=1)
    # Best streak across history
    best = 0
    run = 0
    all_days = sorted(done_by_date.keys())
    prev = None
    for ds in all_days:
        cur = datetime.fromisoformat(ds).date()
        if done_by_date[ds]:
            if prev is not None and (cur - prev).days == 1:
                run += 1
            else:
                run = 1
            best = max(best, run)
            prev = cur
        else:
            prev = None
            run = 0
    return {"current": current, "best": best, "today_complete": done_by_date.get(today.isoformat(), False)}


FOOD_SYSTEM = """You estimate nutrition from a casual meal description. Return ONLY JSON:
{"calories": <int>, "protein_g": <int>, "carbs_g": <int>, "fat_g": <int>, "summary": "<short readable name>"}
Estimate reasonably for typical portions. JSON only."""


@api.post("/wellness/food")
async def log_food(inp: FoodInput, user=Depends(require_plus)):
    date_str = inp.date or datetime.now(timezone.utc).date().isoformat()
    try:
        raw = await router_engine.complete(FOOD_SYSTEM, inp.text, tier="cheap", session_id=f"food-{user['id']}")
    except Exception:
        raw = "{}"
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
    s, e = raw.find("{"), raw.rfind("}")
    est = {}
    if s != -1 and e != -1:
        try:
            est = json.loads(raw[s:e + 1])
        except Exception:
            est = {}
    doc = {
        "id": new_id(), "user_id": user["id"], "date": date_str, "text": inp.text,
        "calories": int(est.get("calories", 0) or 0), "protein_g": int(est.get("protein_g", 0) or 0),
        "carbs_g": int(est.get("carbs_g", 0) or 0), "fat_g": int(est.get("fat_g", 0) or 0),
        "summary": est.get("summary", inp.text[:40]), "meal": inp.meal or "snack", "created_at": now_iso(),
    }
    await db.food_logs.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@api.put("/wellness/food/{fid}")
async def edit_food(fid: str, inp: FoodEdit, user=Depends(require_plus)):
    updates = {k: v for k, v in inp.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    res = await db.food_logs.update_one({"id": fid, "user_id": user["id"]}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Log not found")
    doc = await db.food_logs.find_one({"id": fid, "user_id": user["id"]}, {"_id": 0})
    return doc


@api.get("/wellness/food")
async def get_food(date: str = None, user=Depends(require_plus)):
    date_str = date or datetime.now(timezone.utc).date().isoformat()
    logs = await db.food_logs.find({"user_id": user["id"], "date": date_str}, {"_id": 0}).sort("created_at", 1).to_list(200)
    totals = {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}
    for l in logs:
        for k in totals:
            totals[k] += l.get(k, 0)
    return {"date": date_str, "logs": logs, "totals": totals}


@api.delete("/wellness/food/{fid}")
async def delete_food(fid: str, user=Depends(require_plus)):
    await db.food_logs.delete_one({"id": fid, "user_id": user["id"]})
    return {"ok": True}


@api.get("/wellness/events")
async def get_events(date: str = None, user=Depends(require_plus)):
    q = {"user_id": user["id"]}
    if date:
        q["date"] = date
    return await db.wellness_events.find(q, {"_id": 0}).sort("start", 1).to_list(500)


@api.post("/wellness/events")
async def add_event(inp: EventInput, user=Depends(require_plus)):
    date_str = inp.start[:10] if len(inp.start) >= 10 else datetime.now(timezone.utc).date().isoformat()
    doc = {"id": new_id(), "user_id": user["id"], "date": date_str, **inp.model_dump(), "created_at": now_iso()}
    await db.wellness_events.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@api.delete("/wellness/events/{eid}")
async def delete_event(eid: str, user=Depends(require_plus)):
    await db.wellness_events.delete_one({"id": eid, "user_id": user["id"]})
    return {"ok": True}


@api.post("/chat/feedback")
async def chat_feedback(inp: ChatFeedback, user=Depends(get_current_user)):
    """Lightweight thumbs up/down on an assistant reply — stored for later review."""
    await db.message_feedback.insert_one({
        "id": new_id(), "user_id": user["id"], "session_id": inp.session_id,
        "content": (inp.content or "")[:2000], "rating": inp.rating, "created_at": now_iso(),
    })
    return {"ok": True}


# ---------- Mood journal ----------
@api.post("/wellness/mood")
async def log_mood(inp: MoodInput, user=Depends(require_plus)):
    """One mood entry per day — logging again updates today's."""
    date_str = inp.date or datetime.now(timezone.utc).date().isoformat()
    doc = {
        "id": new_id(), "user_id": user["id"], "date": date_str,
        "mood": inp.mood, "note": (inp.note or "")[:280], "created_at": now_iso(),
    }
    await db.mood_entries.update_one(
        {"user_id": user["id"], "date": date_str},
        {"$set": {"mood": inp.mood, "note": doc["note"], "updated_at": now_iso()},
         "$setOnInsert": {"id": doc["id"], "user_id": user["id"], "date": date_str, "created_at": now_iso()}},
        upsert=True,
    )
    return doc


@api.get("/wellness/mood/trends")
async def mood_trends(days: int = 30, user=Depends(require_plus)):
    days = max(7, min(days, 90))
    start = (datetime.now(timezone.utc).date() - timedelta(days=days - 1)).isoformat()
    rows = await db.mood_entries.find(
        {"user_id": user["id"], "date": {"$gte": start}}, {"_id": 0, "date": 1, "mood": 1, "note": 1}
    ).sort("date", 1).to_list(200)
    moods = [r["mood"] for r in rows]
    avg = round(sum(moods) / len(moods), 1) if moods else None
    today = datetime.now(timezone.utc).date().isoformat()
    return {
        "series": rows, "average": avg, "count": len(rows),
        "today": next((r for r in rows if r["date"] == today), None),
    }


# ---------- Gratitude jar ----------
@api.post("/wellness/gratitude")
async def add_gratitude(inp: GratitudeInput, user=Depends(require_plus)):
    doc = {"id": new_id(), "user_id": user["id"], "text": inp.text.strip()[:280], "created_at": now_iso()}
    await db.gratitude.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@api.get("/wellness/gratitude")
async def list_gratitude(user=Depends(require_plus)):
    items = await db.gratitude.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"items": items, "count": len(items)}


@api.get("/wellness/gratitude/random")
async def random_gratitude(user=Depends(require_plus)):
    import random as _random
    items = await db.gratitude.find({"user_id": user["id"]}, {"_id": 0}).to_list(200)
    return {"item": _random.choice(items) if items else None}


@api.delete("/wellness/gratitude/{gid}")
async def delete_gratitude(gid: str, user=Depends(require_plus)):
    await db.gratitude.delete_one({"id": gid, "user_id": user["id"]})
    return {"ok": True}


# ---------- Habit badges ----------
BADGES = [
    {"id": "first_step", "label": "First step", "icon": "sprout", "metric": "days_active", "threshold": 1},
    {"id": "week_warrior", "label": "One week", "icon": "flame", "metric": "best_streak", "threshold": 7},
    {"id": "month_strong", "label": "30 days", "icon": "medal", "metric": "best_streak", "threshold": 30},
    {"id": "centurion", "label": "100 days", "icon": "trophy", "metric": "best_streak", "threshold": 100},
    {"id": "grateful_heart", "label": "10 gratitudes", "icon": "heart", "metric": "gratitude_count", "threshold": 10},
    {"id": "mood_tracker", "label": "14 moods logged", "icon": "smile", "metric": "mood_count", "threshold": 14},
]


@api.get("/wellness/badges")
async def wellness_badges(user=Depends(require_plus)):
    streak = await wellness_streak(user)  # reuse computed streak
    mood_count = await db.mood_entries.count_documents({"user_id": user["id"]})
    gratitude_count = await db.gratitude.count_documents({"user_id": user["id"]})
    active_days = len(await db.wellness_plans.find({"user_id": user["id"]}, {"_id": 0, "date": 1}).to_list(400))
    metrics = {
        "best_streak": streak["best"], "days_active": active_days,
        "mood_count": mood_count, "gratitude_count": gratitude_count,
    }
    out = []
    for b in BADGES:
        val = metrics.get(b["metric"], 0)
        out.append({**b, "value": val, "earned": val >= b["threshold"],
                    "progress": min(1.0, round(val / b["threshold"], 2))})
    return {"badges": out, "earned_count": sum(1 for b in out if b["earned"])}


@api.get("/")
async def root():
    return {"service": "CampionAI", "status": "ok"}


# ---------------- Doctor consultation system ----------------
api.include_router(doctors_router(db, get_current_user, get_admin_user, get_doctor_user))
api.include_router(consults_router(
    db, get_current_user, get_doctor_user, _plus_state,
    paypal_create_order, paypal_capture_order, _claim_transaction,
))
api.include_router(signaling_router(db, get_current_user, authenticate))

app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


INDEXES = [
    ("users", [("email", 1)], {"unique": True}),
    ("users", [("id", 1)], {"unique": True}),
    ("sessions", [("user_id", 1), ("updated_at", -1)], {}),
    ("messages", [("session_id", 1), ("created_at", -1)], {}),
    ("messages", [("user_id", 1), ("created_at", -1)], {}),
    ("memories", [("user_id", 1), ("tier", 1), ("importance", -1)], {}),
    ("files", [("storage_path", 1), ("user_id", 1)], {}),
    ("safety_events", [("user_id", 1), ("created_at", -1)], {}),
    ("payment_transactions", [("session_id", 1)], {"unique": True}),
    ("payment_transactions", [("user_id", 1), ("created_at", -1)], {}),
    # Doctor consultation system
    ("doctors", [("user_id", 1)], {"unique": True, "sparse": True}),
    ("doctors", [("status", 1), ("country", 1), ("languages", 1), ("is_online", -1)], {}),
    ("doctor_availability", [("doctor_id", 1), ("weekday", 1)], {}),
    ("consult_sessions", [("user_id", 1), ("created_at", -1)], {}),
    ("consult_sessions", [("doctor_id", 1), ("status", 1)], {}),
    ("consult_sessions", [("status", 1), ("scheduled_at", 1)], {}),
    ("consult_messages", [("session_id", 1), ("created_at", 1)], {}),
    ("doctor_ratings", [("session_id", 1)], {"unique": True}),
    ("doctor_ratings", [("doctor_id", 1), ("created_at", -1)], {}),
    ("doctor_payouts", [("doctor_id", 1), ("created_at", -1)], {}),
]


INDEX_PING_TIMEOUT_SEC = 5


async def ensure_indexes():
    """Every query in this app filters by user_id/doctor_id/session_id. Without these
    Mongo collection-scans each one.

    Probe once before the loop: each create_index against an unreachable Mongo blocks
    for the full server-selection timeout (30s by default), so without this a brief
    outage turned startup into a ~10-minute hang instead of a fast, loud failure.
    """
    try:
        await asyncio.wait_for(db.command("ping"), timeout=INDEX_PING_TIMEOUT_SEC)
    except Exception as e:
        logger.error(f"Mongo unreachable, skipping index setup: {str(e)[:160]}")
        return

    for coll, keys, opts in INDEXES:
        try:
            await db[coll].create_index(keys, **opts)
        except Exception as e:
            # A unique index over pre-existing duplicates fails; log rather than block boot.
            logger.warning(f"index {coll}{keys} skipped: {str(e)[:120]}")


async def ensure_paypal_plans():
    """Create the billing plans once, then cache their ids. Idempotent — subsequent
    boots find the existing plans rather than creating duplicates."""
    settings = await db.provider_settings.find_one({"id": "global"}, {"_id": 0}) or {}
    if settings.get("paypal_plans"):
        return
    try:
        plans = await paypal_ensure_plans()
    except Exception as e:
        logger.error(f"paypal plan setup failed: {e}")
        return
    if plans:
        await db.provider_settings.update_one({"id": "global"}, {"$set": {"paypal_plans": plans}}, upsert=True)
        logger.info(f"PayPal plans ready: {list(plans)}")
    else:
        logger.warning("PayPal not configured — subscriptions are unavailable until credentials are set")


@app.on_event("startup")
async def seed():
    await ensure_indexes()
    await ensure_paypal_plans()
    try:
        init_storage()
        logger.info("Object storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
    admin_email = "admin@campionai.com"
    if not await db.users.find_one({"email": admin_email}):
        await db.users.insert_one({
            "id": new_id(), "email": admin_email, "password_hash": hash_password(os.environ.get("ADMIN_PASSWORD", "Admin@12345")),
            "is_admin": True, "role": "admin", "token_version": 0, "onboarded": True, "private_mode": False,
            "profile": {"preferred_name": "Admin", "likes": [], "important_people": [], "goals": [],
                         "communication_style": "warm"},
            "trusted_contact": {"name": "Ops", "relationship": "team", "phone": "", "email": ""},
            "consent": {"safety_alert": True, "age_confirmed": True, "timestamp": now_iso()},
            "country": "US", "checkin_frequency": "off", "last_checkin": None, "created_at": now_iso(),
        })
        logger.info("Seeded admin user")
    # No professional is seeded. The crisis path routes to real verified doctors only
    # (db.doctors); a fictional "verified" clinician backing a live escalation is worse
    # than none, because the escalation UI reports on it.


@app.on_event("shutdown")
async def shutdown():
    client.close()
