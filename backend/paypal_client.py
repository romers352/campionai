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
