import os
import json
import base64
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, UploadFile, File, Query
from fastapi.responses import StreamingResponse, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from models import (
    RegisterInput, LoginInput, OnboardingInput, ProfileUpdate, ChatInput,
    SessionCreate, MemoryUpdate, ModelRouteConfig, ProfessionalInput,
    ProviderSettings, PrivateModeInput, VoiceSettingsInput, TTSInput,
    CheckoutInput, FoodInput, EventInput, PlanItemToggle, PaypalActivate, now_iso, new_id,
)
from auth import (
    hash_password, verify_password, create_token,
    build_get_current_user, build_get_admin_user,
)
from hotlines import get_hotlines, country_list, COUNTRY_NAMES
from llm_router import ModelRouter, DEFAULT_ROUTES, list_openrouter_models
from safety import classify_message
from memory_engine import extract_memories, build_memory_context
from notifications import alert_contact, summarize
from voice import synthesize
from storage import put_object, get_object, init_storage, APP_NAME, MIME_TYPES
from paypal_client import get_subscription as paypal_get_subscription, verify_webhook_signature as paypal_verify_webhook
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("campionai")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="CampionAI")
api = APIRouter(prefix="/api")

router_engine = ModelRouter(db)
get_current_user = build_get_current_user(db)
get_admin_user = build_get_admin_user(get_current_user)

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
    return {"token": create_token(uid), "user": _public_user(doc)}


@api.post("/auth/login")
async def login(inp: LoginInput):
    user = await db.users.find_one({"email": inp.email.lower()})
    if not user or not verify_password(inp.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"token": create_token(user["id"]), "user": _public_user(user)}


@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return _public_user(user)


def _public_user(u):
    return {
        "id": u["id"], "email": u["email"], "is_admin": u.get("is_admin", False),
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


async def _trigger_escalation(user, session_id, trigger_text):
    tc = user.get("trusted_contact")
    hotlines = get_hotlines(user.get("country"))
    prof = await db.professionals.find_one({"verified": True}, {"_id": 0})
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
        presults = await alert_contact(prof.get("name", ""), prof.get("contact"), prof.get("phone"), subject, text, html)
        prof_notified = any(r.get("sent") for r in presults)
        actions.append(summarize(presults, f"Professional ({prof.get('name')})"))

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
        "professional": prof,
        "professional_notified": prof_notified,
        "hotlines": hotlines,
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
    prof = await db.professionals.find_one({"verified": True}, {"_id": 0})
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
        results = await alert_contact(prof.get("name", ""), prof.get("contact"), prof.get("phone"), subject, text, html)
        actions.append(summarize(results, f"Professional ({prof.get('name')})"))
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
        "professionals": await db.professionals.count_documents({}),
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


@api.get("/admin/professionals")
async def list_professionals(admin=Depends(get_admin_user)):
    return await db.professionals.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)


@api.post("/admin/professionals")
async def add_professional(inp: ProfessionalInput, admin=Depends(get_admin_user)):
    doc = {"id": new_id(), **inp.model_dump(), "created_at": now_iso()}
    await db.professionals.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@api.delete("/admin/professionals/{pid}")
async def delete_professional(pid: str, admin=Depends(get_admin_user)):
    res = await db.professionals.delete_one({"id": pid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Professional not found")
    return {"ok": True}


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
    }


# ---------------- Uploads (object storage) ----------------
@api.post("/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    ext = (file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "bin")
    content_type = file.content_type or MIME_TYPES.get(ext, "application/octet-stream")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
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
    from auth import decode_token
    uid = decode_token(auth)
    record = await db.files.find_one({"storage_path": path, "user_id": uid, "is_deleted": False}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        data, content_type = get_object(path)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")
    return Response(content=data, media_type=record.get("content_type", content_type))


# ---------------- Payments (Stripe Flow B) ----------------
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "sk_test_emergent")

PACKAGES = {
    "plus_monthly": {"amount": 9.0, "type": "subscription", "period_days": 30, "label": "CampionAI Plus · Monthly"},
    "plus_yearly": {"amount": 86.40, "type": "subscription", "period_days": 365, "label": "CampionAI Plus · Yearly"},
    "donate_5": {"amount": 5.0, "type": "donation", "label": "Supporter"},
    "donate_15": {"amount": 15.0, "type": "donation", "label": "Sustainer"},
    "donate_30": {"amount": 30.0, "type": "donation", "label": "Champion"},
}


async def _grant_access(record):
    """Idempotently grant Plus access / record donation once a transaction is paid."""
    if record.get("granted"):
        return
    pkg = PACKAGES.get(record.get("package_id"))
    is_sub = (pkg and pkg["type"] == "subscription")
    if is_sub and record.get("user_id"):
        user = await db.users.find_one({"id": record["user_id"]})
        plus = (user or {}).get("plus", {}) or {}
        base = datetime.now(timezone.utc)
        cur = plus.get("until")
        if cur:
            try:
                cur_dt = datetime.fromisoformat(cur)
                if cur_dt > base:
                    base = cur_dt
            except Exception:
                pass
        period = pkg["period_days"]
        until = base + timedelta(days=period)
        await db.users.update_one({"id": record["user_id"]}, {"$set": {
            "plus.status": "active", "plus.until": until.isoformat(),
            "plus.last_payment": now_iso(), "plus.trial_used": True,
        }})
    elif record.get("type") == "donation" and not record.get("anonymous") and record.get("user_id"):
        amount = float(record.get("amount", 0) or 0)
        name = record.get("donor_name") or "A supporter"
        avatar = f"https://ui-avatars.com/api/?name={name.replace(' ', '+')}&background=1a1a1c&color=fafafa&bold=true"
        await db.donors.update_one(
            {"user_id": record["user_id"]},
            {"$inc": {"total": amount}, "$set": {"name": name, "avatar": avatar, "last_at": now_iso()}},
            upsert=True,
        )
    await db.payment_transactions.update_one({"session_id": record["session_id"]}, {"$set": {"granted": True}})


@api.post("/payments/checkout")
async def payments_checkout(inp: CheckoutInput, request: Request, user=Depends(get_current_user)):
    pkg = PACKAGES.get(inp.package_id)
    is_custom = inp.package_id == "donate_custom"
    if not pkg and not is_custom:
        raise HTTPException(status_code=400, detail="Unknown package")
    if is_custom:
        amount = round(float(inp.amount or 0), 2)
        if amount < 1:
            raise HTTPException(status_code=400, detail="Minimum donation is $1")
        if amount > 10000:
            raise HTTPException(status_code=400, detail="Maximum donation is $10,000")
        ptype = "donation"
    else:
        amount = float(pkg["amount"])
        ptype = pkg["type"]
    host = str(request.base_url)
    webhook_url = f"{host}api/webhook/stripe"
    checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    success_url = f"{inp.origin_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{inp.origin_url}/payment/cancel"
    donor_name = (user.get("profile", {}) or {}).get("preferred_name") or user["email"].split("@")[0]
    req = CheckoutSessionRequest(
        amount=amount, currency="usd",
        success_url=success_url, cancel_url=cancel_url,
        metadata={"user_id": user["id"], "package_id": inp.package_id, "type": ptype},
    )
    session = await checkout.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "user_id": user["id"], "package_id": inp.package_id,
        "amount": amount, "currency": "usd", "type": ptype,
        "anonymous": bool(inp.anonymous), "donor_name": donor_name,
        "status": "initiated", "payment_status": "pending", "granted": False,
        "created_at": now_iso(), "updated_at": now_iso(),
    })
    return {"checkout_url": session.url, "session_id": session.session_id}


@api.get("/donors/top")
async def top_donors():
    donors = await db.donors.find({}, {"_id": 0}).sort("total", -1).to_list(10)
    return [{"name": d.get("name"), "avatar": d.get("avatar"), "total": round(d.get("total", 0), 2)} for d in donors]


@api.post("/paypal/activate")
async def paypal_activate(inp: PaypalActivate, user=Depends(get_current_user)):
    plan_key = "plus_yearly" if inp.plan_key == "yearly" else "plus_monthly"
    pkg = PACKAGES[plan_key]
    # Verify server-side when PayPal creds are configured
    try:
        sub = await paypal_get_subscription(inp.subscription_id)
    except Exception as e:
        logger.error(f"paypal verify error: {e}")
        raise HTTPException(status_code=400, detail="Could not verify PayPal subscription")
    if sub is None:
        raise HTTPException(status_code=400, detail="PayPal is not configured")
    if sub.get("status") not in ("ACTIVE", "APPROVED"):
        raise HTTPException(status_code=400, detail=f"Subscription not active ({sub.get('status')})")
    session_key = f"paypal-{inp.subscription_id}"
    existing = await db.payment_transactions.find_one({"session_id": session_key}, {"_id": 0})
    if not existing:
        tx = {
            "session_id": session_key, "user_id": user["id"], "package_id": plan_key,
            "amount": float(pkg["amount"]), "currency": "usd", "type": "subscription",
            "provider": "paypal", "paypal_subscription_id": inp.subscription_id,
            "status": "completed", "payment_status": "paid", "granted": False,
            "created_at": now_iso(), "updated_at": now_iso(),
        }
        await db.payment_transactions.insert_one(dict(tx))
        existing = tx
    await _grant_access(existing)
    fresh = await db.users.find_one({"id": user["id"]})
    return _plus_state(fresh)


@api.get("/payments/status/{session_id}")
async def payments_status(session_id: str, request: Request, user=Depends(get_current_user)):
    record = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if record.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your transaction")
    if record.get("payment_status") != "paid":
        try:
            host = str(request.base_url)
            checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{host}api/webhook/stripe")
            status = await checkout.get_checkout_status(session_id)
            if status.payment_status == "paid" or status.status == "complete":
                await db.payment_transactions.update_one(
                    {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                    {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now_iso()}},
                )
                record = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
                await _grant_access(record)
                record = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        except Exception as e:
            logger.error(f"stripe status error: {e}")
    return {"session_id": record["session_id"], "status": record["status"], "payment_status": record["payment_status"], "type": record.get("type")}


@api.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        host = str(request.base_url)
        checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{host}api/webhook/stripe")
        resp = await checkout.handle_webhook(body, sig)
    except Exception as e:
        logger.error(f"webhook error: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook")
    if resp.payment_status == "paid":
        await db.payment_transactions.update_one(
            {"session_id": resp.session_id, "payment_status": {"$ne": "paid"}},
            {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now_iso()}},
        )
        record = await db.payment_transactions.find_one({"session_id": resp.session_id}, {"_id": 0})
        if record:
            await _grant_access(record)
    return {"status": "ok"}


@api.post("/webhook/paypal")
async def paypal_webhook(request: Request):
    raw = await request.body()
    # LIVE: verify the signature with PayPal before trusting the event.
    try:
        verified = await paypal_verify_webhook(request.headers, raw)
    except Exception as e:
        logger.error(f"paypal webhook verify error: {e}")
        verified = False
    if not verified:
        logger.warning("paypal webhook signature not verified — rejecting")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        event = json.loads(raw.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    etype = event.get("event_type", "")
    resource = event.get("resource", {}) or {}
    # Subscription id lives in resource.id for BILLING.SUBSCRIPTION.* and in
    # resource.billing_agreement_id for PAYMENT.SALE.COMPLETED.
    sub_id = resource.get("id") if etype.startswith("BILLING.SUBSCRIPTION") else resource.get("billing_agreement_id")
    logger.info(f"paypal webhook: {etype} sub={sub_id}")

    if not sub_id:
        return {"status": "ignored"}

    tx = await db.payment_transactions.find_one({"paypal_subscription_id": sub_id}, {"_id": 0})
    user_id = tx.get("user_id") if tx else None
    now = datetime.now(timezone.utc)

    if etype == "BILLING.SUBSCRIPTION.ACTIVATED":
        if tx:
            await db.payment_transactions.update_one({"session_id": tx["session_id"]}, {"$set": {"status": "completed", "payment_status": "paid", "granted": False, "updated_at": now_iso()}})
            fresh = await db.payment_transactions.find_one({"session_id": tx["session_id"]}, {"_id": 0})
            await _grant_access(fresh)
    elif etype == "PAYMENT.SALE.COMPLETED":
        # Recurring renewal payment — extend the paid period.
        if tx and user_id:
            pkg = PACKAGES.get(tx.get("package_id")) or {}
            period = pkg.get("period_days", 30)
            user = await db.users.find_one({"id": user_id})
            plus = (user or {}).get("plus", {}) or {}
            base = now
            cur = plus.get("until")
            if cur:
                try:
                    cur_dt = datetime.fromisoformat(cur)
                    if cur_dt > base:
                        base = cur_dt
                except Exception:
                    pass
            until = base + timedelta(days=period)
            await db.users.update_one({"id": user_id}, {"$set": {
                "plus.status": "active", "plus.until": until.isoformat(), "plus.last_payment": now_iso(),
            }})
    elif etype == "BILLING.SUBSCRIPTION.CANCELLED":
        # Keep remaining paid time; just mark as cancelled (won't auto-renew).
        if user_id:
            await db.users.update_one({"id": user_id}, {"$set": {"plus.status": "cancelled"}})
        if tx:
            await db.payment_transactions.update_one({"session_id": tx["session_id"]}, {"$set": {"status": "cancelled", "updated_at": now_iso()}})
    elif etype in ("BILLING.SUBSCRIPTION.SUSPENDED", "BILLING.SUBSCRIPTION.EXPIRED"):
        # Revoke access immediately.
        if user_id:
            status = "suspended" if "SUSPENDED" in etype else "expired"
            await db.users.update_one({"id": user_id}, {"$set": {"plus.status": status, "plus.until": now.isoformat()}})
        if tx:
            await db.payment_transactions.update_one({"session_id": tx["session_id"]}, {"$set": {"status": "cancelled", "updated_at": now_iso()}})
    elif etype == "BILLING.SUBSCRIPTION.PAYMENT.FAILED":
        # Grace period — flag but don't revoke yet.
        if user_id:
            await db.users.update_one({"id": user_id}, {"$set": {"plus.status": "past_due"}})

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
    return {"active": active, "status": status, "until": until, "trial_ends_at": trial_ends, "trial_used": plus.get("trial_used", False)}


@api.get("/plus/status")
async def plus_status(user=Depends(get_current_user)):
    return _plus_state(user)


@api.post("/plus/start-trial")
async def start_trial(user=Depends(get_current_user)):
    plus = user.get("plus", {}) or {}
    if plus.get("trial_used") or plus.get("until"):
        raise HTTPException(status_code=400, detail="Trial already used")
    trial_ends = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
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
        "summary": est.get("summary", inp.text[:40]), "created_at": now_iso(),
    }
    await db.food_logs.insert_one(dict(doc))
    doc.pop("_id", None)
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


@api.get("/")
async def root():
    return {"service": "CampionAI", "status": "ok"}


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def seed():
    try:
        init_storage()
        logger.info("Object storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
    admin_email = "admin@campionai.com"
    if not await db.users.find_one({"email": admin_email}):
        await db.users.insert_one({
            "id": new_id(), "email": admin_email, "password_hash": hash_password("Admin@12345"),
            "is_admin": True, "onboarded": True, "private_mode": False,
            "profile": {"preferred_name": "Admin", "likes": [], "important_people": [], "goals": [],
                         "communication_style": "warm"},
            "trusted_contact": {"name": "Ops", "relationship": "team", "phone": "", "email": ""},
            "consent": {"safety_alert": True, "age_confirmed": True, "timestamp": now_iso()},
            "country": "US", "checkin_frequency": "off", "last_checkin": None, "created_at": now_iso(),
        })
        logger.info("Seeded admin user")
    if await db.professionals.count_documents({}) == 0:
        await db.professionals.insert_one({
            "id": new_id(), "name": "Dr. Maya Reyes", "credentials": "Licensed Clinical Psychologist (PsyD)",
            "specialty": "Crisis support & anxiety", "contact": "maya.reyes@campionai-verified.org",
            "verified": True, "availability": "on-call", "created_at": now_iso(),
        })
        logger.info("Seeded verified professional")


@app.on_event("shutdown")
async def shutdown():
    client.close()
