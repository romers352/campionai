"""PayPal REST helper (subscriptions). Verifies a subscription server-side when
client credentials are configured; degrades gracefully otherwise."""
import os
import httpx


def _base():
    return "https://api-m.paypal.com" if os.environ.get("PAYPAL_MODE", "sandbox") == "live" else "https://api-m.sandbox.paypal.com"


def _creds():
    return os.environ.get("PAYPAL_CLIENT_ID", "").strip(), os.environ.get("PAYPAL_SECRET", "").strip()


async def _token():
    cid, sec = _creds()
    if not (cid and sec):
        return None
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{_base()}/v1/oauth2/token", data={"grant_type": "client_credentials"}, auth=(cid, sec))
        r.raise_for_status()
        return r.json()["access_token"]


async def get_subscription(subscription_id: str):
    """Returns the subscription dict, or None if PayPal creds aren't configured."""
    tok = await _token()
    if not tok:
        return None
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{_base()}/v1/billing/subscriptions/{subscription_id}", headers={"Authorization": f"Bearer {tok}"})
        r.raise_for_status()
        return r.json()


async def verify_webhook_signature(headers, raw_body: bytes) -> bool:
    """Verify a PayPal webhook using the verify-webhook-signature API.
    Returns True only when PayPal confirms SUCCESS. If creds/webhook id are
    missing we return False (caller decides how strict to be)."""
    tok = await _token()
    webhook_id = os.environ.get("PAYPAL_WEBHOOK_ID", "").strip()
    if not (tok and webhook_id):
        return False

    def _h(name):
        # header lookup is case-insensitive via Starlette's Headers
        return headers.get(name) or headers.get(name.lower())

    import json as _json
    payload = {
        "auth_algo": _h("PayPal-Auth-Algo"),
        "cert_url": _h("PayPal-Cert-Url"),
        "transmission_id": _h("PayPal-Transmission-Id"),
        "transmission_sig": _h("PayPal-Transmission-Sig"),
        "transmission_time": _h("PayPal-Transmission-Time"),
        "webhook_id": webhook_id,
        "webhook_event": _json.loads(raw_body.decode("utf-8")),
    }
    if not all([payload["auth_algo"], payload["cert_url"], payload["transmission_id"],
                payload["transmission_sig"], payload["transmission_time"]]):
        return False
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{_base()}/v1/notifications/verify-webhook-signature",
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
            json=payload,
        )
        r.raise_for_status()
        return r.json().get("verification_status") == "SUCCESS"
