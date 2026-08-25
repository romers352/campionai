"""Memory decision engine. Uses the cheap model to extract durable facts and score them,
then decides: DO_NOT_STORE / TEMPORARY / SESSION / LONG_TERM."""
import json
from models import now_iso, new_id

EXTRACT_SYSTEM = """You extract durable personal facts from a chat message to help an AI companion remember its friend.
Return ONLY a JSON array (no prose). Each item:
{"content": "<short third-person fact>", "category": "<work|education|relationships|goals|likes|health_signal|event|preference|other>",
 "importance": 0-1, "sensitivity": 0-1, "confidence": 0-1, "stability": 0-1}
Rules:
- Only extract facts worth remembering long-term (name, job, studies, key people, goals, strong preferences, major events).
- Do NOT extract greetings, small talk, or transient states as long-term. Mood/stress -> category "health_signal" with low stability (these are SIGNALS, never diagnoses).
- If nothing worth remembering, return [].
Return [] or a JSON array only."""


def _tier_for(item: dict) -> str:
    imp = item.get("importance", 0)
    stab = item.get("stability", 0)
    conf = item.get("confidence", 0)
    if conf < 0.35 or imp < 0.3:
        return "DO_NOT_STORE"
    if item.get("category") == "health_signal" or stab < 0.4:
        return "SESSION"
    if imp >= 0.6 and stab >= 0.5:
        return "LONG_TERM"
    return "TEMPORARY"


async def extract_memories(router, db, user_id: str, session_id: str, text: str, private: bool):
    if private:
        return []  # Private Mode: never persist long-term memory
    try:
        raw = await router.complete(EXTRACT_SYSTEM, text, tier="cheap", session_id=f"mem-{session_id}")
    except Exception:
        return []
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        items = json.loads(raw[start:end + 1])
    except Exception:
        return []
    stored = []
    for item in items:
        if not isinstance(item, dict) or not item.get("content"):
            continue
        decision = _tier_for(item)
        if decision == "DO_NOT_STORE":
            continue
        doc = {
            "id": new_id(),
            "user_id": user_id,
            "session_id": session_id,
            "content": item["content"],
            "category": item.get("category", "other"),
            "tier": decision,
            "importance": round(float(item.get("importance", 0)), 2),
            "sensitivity": round(float(item.get("sensitivity", 0)), 2),
            "confidence": round(float(item.get("confidence", 0)), 2),
            "stability": round(float(item.get("stability", 0)), 2),
            "created_at": now_iso(),
        }
        await db.memories.insert_one(doc)
        doc.pop("_id", None)
        stored.append(doc)
    return stored


async def build_memory_context(db, user_id: str) -> str:
    mems = await db.memories.find(
        {"user_id": user_id, "tier": "LONG_TERM"}, {"_id": 0}
    ).sort("importance", -1).to_list(40)
    if not mems:
        return ""
    lines = [f"- ({m['category']}) {m['content']}" for m in mems]
    return "What you remember about them:\n" + "\n".join(lines)
