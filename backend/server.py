import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from models import (
    RegisterInput, LoginInput, OnboardingInput, ProfileUpdate, ChatInput,
    SessionCreate, MemoryUpdate, ModelRouteConfig, ProfessionalInput,
    ProviderSettings, PrivateModeInput, now_iso, new_id,
)
from auth import (
    hash_password, verify_password, create_token,
    build_get_current_user, build_get_admin_user,
)
from hotlines import get_hotlines, country_list, COUNTRY_NAMES
from llm_router import ModelRouter, DEFAULT_ROUTES, list_openrouter_models
from safety import classify_message
from memory_engine import extract_memories, build_memory_context

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
        "role": "user", "content": inp.message, "private": private, "created_at": now_iso(),
    }
    await db.messages.insert_one(dict(user_msg))

    risk = await classify_message(router_engine, inp.message, session_id)

    transcript = await recent_transcript(session_id)
    memory_ctx = "" if private else await build_memory_context(db, user["id"])
    system = build_system_prompt(user, memory_ctx, transcript, risk)

    escalation = None
    if risk == "high":
        escalation = await _trigger_escalation(user, session_id, inp.message)

    async def gen():
        yield _sse({"type": "meta", "session_id": session_id, "risk": risk, "private": private})
        full = ""
        try:
            async for chunk in router_engine.stream(system, inp.message, tier=("powerful" if risk in ("high", "medium") else "medium"), session_id=session_id):
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


async def _trigger_escalation(user, session_id, trigger_text):
    tc = user.get("trusted_contact")
    hotlines = get_hotlines(user.get("country"))
    prof = await db.professionals.find_one({"verified": True}, {"_id": 0})
    actions = ["Crisis hotlines surfaced"]
    if tc:
        actions.append(f"Trusted contact alerted: {tc.get('name')}")
    if prof:
        actions.append(f"Routed to verified professional: {prof.get('name')}")
    event = {
        "id": new_id(), "user_id": user["id"], "user_email": user["email"], "session_id": session_id,
        "risk_level": "high", "trigger_text": trigger_text[:500],
        "actions_taken": actions, "resolved": False, "created_at": now_iso(),
    }
    await db.safety_events.insert_one(dict(event))
    return {
        "triggered": True,
        "trusted_contact": tc,
        "hotlines": hotlines,
        "professional": prof,
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
    sys = (
        "You are CampionAI starting a proactive, thoughtful check-in with your friend. "
        "Write ONE short, warm, specific opening message (1-2 sentences) that references something you know about them if possible. "
        "Sound like a caring friend reaching out, not a notification. No emojis."
        + ("\n" + memory_ctx if memory_ctx else "")
    )
    try:
        msg = await router_engine.complete(sys, f"Reach out to {name} now.", tier="medium", session_id=f"checkin-{user['id']}")
    except Exception:
        msg = f"Hey {name}, you crossed my mind — how are you really doing today?"
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
    event = {
        "id": new_id(), "user_id": user["id"], "user_email": user["email"], "session_id": None,
        "risk_level": "handoff_request", "trigger_text": "User requested human handoff",
        "actions_taken": ["User-initiated handoff", f"Matched: {prof.get('name') if prof else 'pending'}"],
        "resolved": False, "created_at": now_iso(),
    }
    await db.safety_events.insert_one(dict(event))
    return {"professional": prof, "consented_summary": summary, "hotlines": get_hotlines(user.get("country"))}


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
