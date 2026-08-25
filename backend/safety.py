"""Deterministic-first safety classifier. Keyword layer is the guaranteed net;
model verification only *upgrades* risk, never silently downgrades a keyword hit."""
import re

# Explicit high-risk (active intent / plan / means)
HIGH_PATTERNS = [
    r"\bkill (myself|me)\b",
    r"\bkilling myself\b",
    r"\bend (my|it) (life|all)\b",
    r"\bend my life\b",
    r"\btake my (own )?life\b",
    r"\bwant to die\b",
    r"\bwanna die\b",
    r"\bwish i (was|were) dead\b",
    r"\bsuicid",
    r"\bcommit suicide\b",
    r"\bhurt myself\b",
    r"\bharm myself\b",
    r"\bself[- ]harm",
    r"\bcut(ting)? myself\b",
    r"\boverdose\b",
    r"\bno reason to live\b",
    r"\bdon'?t want to (be here|live|exist)\b",
    r"\bbetter off (dead|without me)\b",
    r"\bkms\b",
    r"\bunalive\b",
    r"\bhang myself\b",
    r"\bjump off\b",
    r"\bslit my\b",
]

# Softer distress signals -> medium, model verifier may upgrade
MEDIUM_PATTERNS = [
    r"\bhopeless\b",
    r"\bcan'?t go on\b",
    r"\bcan'?t take (it|this) anymore\b",
    r"\bgiving up\b",
    r"\bgive up on everything\b",
    r"\bworthless\b",
    r"\bnobody (would care|cares)\b",
    r"\bno( one)? point\b",
    r"\bempty inside\b",
    r"\bnumb\b",
    r"\bdesperate\b",
    r"\bbreaking point\b",
]

HIGH_RE = [re.compile(p, re.IGNORECASE) for p in HIGH_PATTERNS]
MEDIUM_RE = [re.compile(p, re.IGNORECASE) for p in MEDIUM_PATTERNS]


def keyword_classify(text: str) -> str:
    t = text or ""
    for r in HIGH_RE:
        if r.search(t):
            return "high"
    for r in MEDIUM_RE:
        if r.search(t):
            return "medium"
    return "none"


CLASSIFY_SYSTEM = (
    "You are a safety triage classifier for a companion app. You do NOT diagnose. "
    "Read the user's latest message and rate imminent risk of self-harm or harm to others. "
    "Respond with ONLY one word: NONE, LOW, MEDIUM, or HIGH. "
    "HIGH = expresses intent, plan, or active desire to die / self-harm / harm others. "
    "MEDIUM = significant emotional distress or passive ideation without plan. "
    "LOW = mild sadness/stress. NONE = neutral/positive. When uncertain between two, choose the HIGHER."
)

LEVEL_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}


async def classify_message(router, text: str, session_id: str) -> str:
    """Combine deterministic keywords with model verifier. Never downgrade a high keyword hit."""
    kw = keyword_classify(text)
    if kw == "high":
        return "high"
    try:
        raw = await router.complete(CLASSIFY_SYSTEM, text, tier="powerful", session_id=f"safety-{session_id}")
        model_level = (raw or "").strip().lower().split()[0] if raw else "none"
        if model_level not in LEVEL_ORDER:
            model_level = kw if kw != "none" else "none"
    except Exception:
        model_level = kw
    # take the max of keyword and model assessment
    final = kw if LEVEL_ORDER.get(kw, 0) >= LEVEL_ORDER.get(model_level, 0) else model_level
    return final
