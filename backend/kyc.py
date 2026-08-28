"""Identity verification (KYC) for doctor applicants.

Scope note: this proves the applicant is the person on their government ID. It does
NOT prove they hold a medical licence — no provider does that globally. Licence
review stays manual in Admin, so approval is two-gated: KYC pass + licence review.

Default provider is Didit; base URL, workflow id, and header name are all env-driven
so swapping to Veriff/Persona is configuration, not a rewrite.

Degrades gracefully: with no key configured, create_session() returns None and the
application simply sits at kyc.status == "not_configured" for a human to handle.
"""
import os
import hmac
import hashlib
import logging
import httpx

logger = logging.getLogger("campionai.kyc")

PROVIDER = os.environ.get("KYC_PROVIDER", "didit").strip().lower()
BASE_URL = os.environ.get("KYC_BASE_URL", "https://verification.didit.me/v2").rstrip("/")
API_KEY_HEADER = os.environ.get("KYC_API_KEY_HEADER", "x-api-key")

# Provider decision strings -> our three states.
APPROVED = {"approved", "accept", "accepted", "verified", "clear", "success"}
DECLINED = {"declined", "denied", "rejected", "failed", "abandoned", "expired"}


def _key():
    return os.environ.get("KYC_API_KEY", "").strip()


def configured() -> bool:
    return bool(_key())


def _headers():
    return {API_KEY_HEADER: _key(), "Content-Type": "application/json"}


def normalize_status(raw: str) -> str:
    v = (raw or "").strip().lower()
    if v in APPROVED:
        return "approved"
    if v in DECLINED:
        return "declined"
    return "pending"


async def create_session(user_id: str, callback_url: str = None) -> dict | None:
    """Start a hosted verification. Returns {session_id, url} or None if unconfigured."""
    if not configured():
        return None
    body = {"vendor_data": user_id}
    workflow = os.environ.get("KYC_WORKFLOW_ID", "").strip()
    if workflow:
        body["workflow_id"] = workflow
    if callback_url:
        body["callback"] = callback_url
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{BASE_URL}/session/", json=body, headers=_headers())
            r.raise_for_status()
            data = r.json()
        session_id = data.get("session_id") or data.get("id")
        url = data.get("url") or data.get("verification_url")
        if not session_id or not url:
            logger.error(f"kyc session response missing fields: {list(data)}")
            return None
        return {"session_id": session_id, "url": url}
    except Exception as e:
        logger.error(f"kyc session creation failed: {e}")
        return None


async def get_status(session_id: str) -> str:
    """Returns approved | declined | pending. Never raises — an unreachable provider
    must not flip an applicant to approved."""
    if not configured() or not session_id:
        return "pending"
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{BASE_URL}/session/{session_id}/decision/", headers=_headers())
            r.raise_for_status()
            data = r.json()
        return normalize_status(data.get("status") or data.get("decision", {}).get("status"))
    except Exception as e:
        logger.error(f"kyc status check failed: {e}")
        return "pending"


def verify_webhook(body: bytes, signature: str, timestamp: str = None) -> bool:
    """HMAC-SHA256 over the raw body. Returns False when it cannot be proven genuine,
    including when no secret is configured — an unverified POST must never approve
    a doctor."""
    secret = os.environ.get("KYC_WEBHOOK_SECRET", "").strip()
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip().lower().removeprefix("sha256="))
