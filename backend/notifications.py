"""Real-world alert delivery: email (Resend) + SMS (Twilio).
Degrades gracefully: if a channel is not configured, it is skipped and reported, never raised."""
import os
import asyncio
import logging

logger = logging.getLogger("campionai.notify")


def _resend_key():
    return os.environ.get("RESEND_API_KEY", "").strip()


def _twilio_creds():
    return (
        os.environ.get("TWILIO_ACCOUNT_SID", "").strip(),
        os.environ.get("TWILIO_AUTH_TOKEN", "").strip(),
        os.environ.get("TWILIO_FROM_NUMBER", "").strip(),
    )


async def send_email(to: str, subject: str, html: str) -> dict:
    key = _resend_key()
    if not key or not to:
        return {"channel": "email", "sent": False, "reason": "not_configured" if not key else "no_recipient"}
    try:
        import resend
        resend.api_key = key
        params = {
            "from": os.environ.get("SENDER_EMAIL", "onboarding@resend.dev"),
            "to": [to],
            "subject": subject,
            "html": html,
        }
        res = await asyncio.to_thread(resend.Emails.send, params)
        return {"channel": "email", "sent": True, "id": res.get("id") if isinstance(res, dict) else None}
    except Exception as e:
        logger.error(f"email send failed: {e}")
        return {"channel": "email", "sent": False, "reason": str(e)[:120]}


async def send_sms(to: str, body: str) -> dict:
    sid, token, from_num = _twilio_creds()
    if not (sid and token and from_num) or not to:
        return {"channel": "sms", "sent": False, "reason": "not_configured" if not (sid and token and from_num) else "no_recipient"}
    try:
        from twilio.rest import Client
        client = Client(sid, token)
        msg = await asyncio.to_thread(
            lambda: client.messages.create(to=to, from_=from_num, body=body)
        )
        return {"channel": "sms", "sent": True, "sid": msg.sid}
    except Exception as e:
        logger.error(f"sms send failed: {e}")
        return {"channel": "sms", "sent": False, "reason": str(e)[:120]}


async def alert_contact(name: str, email: str | None, phone: str | None, subject: str, text: str, html: str):
    """Fire email + SMS in parallel to one recipient. Returns list of result dicts."""
    tasks = []
    if email:
        tasks.append(send_email(email, subject, html))
    if phone:
        tasks.append(send_sms(phone, text))
    if not tasks:
        return []
    return await asyncio.gather(*tasks, return_exceptions=False)


def summarize(results, label: str) -> str:
    sent = [r["channel"] for r in results if r.get("sent")]
    if sent:
        return f"{label}: alert sent via {', '.join(sent)}"
    return f"{label}: alert queued (delivery not configured)"
