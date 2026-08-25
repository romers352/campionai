"""PayPal REST client — the only payment rail.

Covers recurring subscriptions (catalog products, billing plans, cancel, transaction
history), one-time orders (donations, consult fees), and webhook signature verification.

Every call degrades gracefully: with no credentials configured, functions return None
rather than raising, so the app runs unpaid instead of falling over.
"""
import os
import json
import logging
import httpx

logger = logging.getLogger("campionai.paypal")

PRODUCT_NAME = "CampionAI Plus"

# Plan definitions. `key` doubles as the PayPal-Request-Id seed so repeated boots
# do not create duplicate plans.
PLAN_DEFS = {
    "plus_monthly": {"label": "CampionAI Plus · Monthly", "amount": "9.00", "unit": "MONTH", "count": 1},
    "plus_yearly": {"label": "CampionAI Plus · Yearly", "amount": "86.40", "unit": "YEAR", "count": 1},
}


def _base():
    return "https://api-m.paypal.com" if os.environ.get("PAYPAL_MODE", "sandbox") == "live" else "https://api-m.sandbox.paypal.com"


def _creds():
    return os.environ.get("PAYPAL_CLIENT_ID", "").strip(), os.environ.get("PAYPAL_SECRET", "").strip()


def configured() -> bool:
    return all(_creds())


async def _token():
    cid, sec = _creds()
    if not (cid and sec):
        return None
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{_base()}/v1/oauth2/token", data={"grant_type": "client_credentials"}, auth=(cid, sec))
        r.raise_for_status()
        return r.json()["access_token"]


async def _call(method: str, path: str, *, json_body=None, params=None, request_id=None):
    """Authenticated PayPal call. Returns parsed JSON, or None when unconfigured."""
    tok = await _token()
    if not tok:
        return None
    headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    if request_id:
        headers["PayPal-Request-Id"] = request_id
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.request(method, f"{_base()}{path}", headers=headers, json=json_body, params=params)
        r.raise_for_status()
        return r.json() if r.content else {}


# ---------------- Subscriptions ----------------
async def get_subscription(subscription_id: str):
    """Returns the subscription dict, or None if PayPal creds aren't configured."""
    return await _call("GET", f"/v1/billing/subscriptions/{subscription_id}")


async def cancel_subscription(subscription_id: str, reason: str = "Cancelled by user"):
    return await _call("POST", f"/v1/billing/subscriptions/{subscription_id}/cancel", json_body={"reason": reason[:127]})


async def activate_subscription(subscription_id: str, reason: str = "Reactivated by user"):
    """Only valid for a SUSPENDED subscription; PayPal rejects it for CANCELLED."""
    return await _call("POST", f"/v1/billing/subscriptions/{subscription_id}/activate", json_body={"reason": reason[:127]})


async def subscription_transactions(subscription_id: str, start_time: str, end_time: str):
    data = await _call("GET", f"/v1/billing/subscriptions/{subscription_id}/transactions",
                       params={"start_time": start_time, "end_time": end_time})
    return (data or {}).get("transactions", [])


async def _ensure_product():
    """Find or create the catalog product that plans hang off."""
    existing = await _call("GET", "/v1/catalogs/products", params={"page_size": 20})
    if existing is None:
        return None
    for p in existing.get("products", []):
        if p.get("name") == PRODUCT_NAME:
            return p["id"]
    created = await _call("POST", "/v1/catalogs/products", request_id="campionai-plus-product", json_body={
        "name": PRODUCT_NAME,
        "description": "Daily wellness coaching inside CampionAI",
        "type": "SERVICE",
        "category": "SOFTWARE",
    })
    return (created or {}).get("id")


async def ensure_plans() -> dict:
    """Idempotently create the monthly/yearly billing plans. Returns {key: plan_id}.

    Called at startup; the result is cached in provider_settings so this is a lookup
    on subsequent boots rather than a round trip per plan.
    """
    if not configured():
        return {}
    product_id = await _ensure_product()
    if not product_id:
        return {}
    listing = await _call("GET", "/v1/billing/plans", params={"product_id": product_id, "page_size": 20})
    by_name = {p["name"]: p["id"] for p in (listing or {}).get("plans", []) if p.get("status") == "ACTIVE"}

    out = {}
    for key, d in PLAN_DEFS.items():
        if d["label"] in by_name:
            out[key] = by_name[d["label"]]
            continue
        created = await _call("POST", "/v1/billing/plans", request_id=f"campionai-{key}-v1", json_body={
            "product_id": product_id,
            "name": d["label"],
            "status": "ACTIVE",
            "billing_cycles": [{
                "frequency": {"interval_unit": d["unit"], "interval_count": d["count"]},
                "tenure_type": "REGULAR",
                "sequence": 1,
                "total_cycles": 0,  # 0 = renew forever
                "pricing_scheme": {"fixed_price": {"value": d["amount"], "currency_code": "USD"}},
            }],
            "payment_preferences": {
                "auto_bill_outstanding": True,
                "setup_fee_failure_action": "CONTINUE",
                "payment_failure_threshold": 3,
            },
        })
        if created and created.get("id"):
            out[key] = created["id"]
    return out


# ---------------- One-time orders (donations, consult fees) ----------------
async def create_order(amount: float, description: str, custom_id: str = None, return_url: str = None, cancel_url: str = None):
    body = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {"currency_code": "USD", "value": f"{amount:.2f}"},
            "description": description[:127],
            **({"custom_id": custom_id[:127]} if custom_id else {}),
        }],
    }
    if return_url and cancel_url:
        body["payment_source"] = {"paypal": {"experience_context": {
            "return_url": return_url, "cancel_url": cancel_url, "user_action": "PAY_NOW",
        }}}
    return await _call("POST", "/v2/checkout/orders", json_body=body)


async def capture_order(order_id: str):
    return await _call("POST", f"/v2/checkout/orders/{order_id}/capture", json_body={})


async def get_order(order_id: str):
    return await _call("GET", f"/v2/checkout/orders/{order_id}")


# ---------------- Webhooks ----------------
async def verify_webhook(headers, body: bytes) -> bool:
    """Verify a webhook against PayPal. Returns False when it cannot be proven genuine —
    including when PAYPAL_WEBHOOK_ID is unset, so an unconfigured deploy cannot be
    tricked into granting access by a forged POST."""
    webhook_id = os.environ.get("PAYPAL_WEBHOOK_ID", "").strip()
    if not webhook_id or not configured():
        logger.warning("paypal webhook rejected: PAYPAL_WEBHOOK_ID not configured")
        return False
    try:
        payload = {
            "auth_algo": headers.get("paypal-auth-algo"),
            "cert_url": headers.get("paypal-cert-url"),
            "transmission_id": headers.get("paypal-transmission-id"),
            "transmission_sig": headers.get("paypal-transmission-sig"),
            "transmission_time": headers.get("paypal-transmission-time"),
            "webhook_id": webhook_id,
            "webhook_event": json.loads(body),
        }
        if not all(payload[k] for k in ("auth_algo", "cert_url", "transmission_id", "transmission_sig", "transmission_time")):
            return False
        res = await _call("POST", "/v1/notifications/verify-webhook-signature", json_body=payload)
        return (res or {}).get("verification_status") == "SUCCESS"
    except Exception as e:
        logger.error(f"webhook verification failed: {e}")
        return False
