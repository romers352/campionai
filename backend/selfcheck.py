"""Dependency-free self-checks for the logic that would fail silently.

Run: python selfcheck.py

Deliberately not pytest — backend/tests/ talks to a deployed instance, while these
are pure-function checks that must run anywhere, including in a pre-commit hook.
"""
import asyncio
import base64
import hashlib
import hmac
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ---------------- upload path safety ----------------
def check_safe_ext():
    from server import safe_ext  # noqa: E402  (import here so env is set first)

    # The bug this guards: filename is attacker-controlled, and rsplit(".")[-1] on
    # "photo.jpg/../../victim/x" yields a path that escapes the user's storage prefix.
    assert safe_ext("photo.jpg") == "jpg"
    assert safe_ext("scan.PNG") == "png"
    for bad in ("photo.jpg/../../../victim/evil", "a.jpg/../../x", "a.b/c", "a../..", "a.%2e%2e", "a.<script>"):
        assert "/" not in safe_ext(bad), bad
        assert ".." not in safe_ext(bad), bad
    assert safe_ext("noextension") == "bin"
    assert safe_ext("") == "bin"
    assert safe_ext(None) == "bin"
    assert safe_ext("a." + "x" * 50) == "x" * 8      # bounded length
    assert safe_ext("a.!!!") == "bin"                 # nothing survives -> fallback
    print("  ok  safe_ext blocks traversal, bounds length, always non-empty")


# ---------------- TURN credentials ----------------
def check_turn_credentials():
    os.environ["TURN_HOST"] = "turn.example.com:3478"
    os.environ["TURN_SECRET"] = "s3cret"
    import importlib
    import signaling
    importlib.reload(signaling)

    servers = signaling.ice_servers("user-123")
    turn = [s for s in servers if any("turn:" in u for u in s["urls"])]
    assert turn, "TURN server missing when TURN_HOST/TURN_SECRET are set"
    username, credential = turn[0]["username"], turn[0]["credential"]

    expiry, uid = username.split(":", 1)
    assert uid == "user-123"
    assert int(expiry) > 0, "username must carry an expiry — static creds get scraped"
    expected = base64.b64encode(
        hmac.new(b"s3cret", username.encode(), hashlib.sha1).digest()).decode()
    assert credential == expected, "credential must be HMAC-SHA1(secret, username)"

    # Without a secret there must be no TURN entry at all (STUN only).
    os.environ.pop("TURN_SECRET")
    importlib.reload(signaling)
    assert not [s for s in signaling.ice_servers("u") if any("turn:" in u for u in s["urls"])]
    assert signaling.ice_servers("u"), "STUN must always be present"
    print("  ok  TURN creds are time-limited HMACs; absent when unconfigured")


# ---------------- doctor presence ----------------
def check_presence():
    from datetime import datetime, timezone, timedelta
    from doctors import is_online, PRESENCE_TIMEOUT_SEC

    now = datetime.now(timezone.utc)
    fresh = (now - timedelta(seconds=10)).isoformat()
    stale = (now - timedelta(seconds=PRESENCE_TIMEOUT_SEC + 30)).isoformat()

    assert is_online({"is_online": True, "last_seen": fresh})
    # The flag alone is not enough — a crashed tab leaves is_online True forever.
    assert not is_online({"is_online": True, "last_seen": stale})
    assert not is_online({"is_online": True, "last_seen": None})
    assert not is_online({"is_online": False, "last_seen": fresh})
    assert not is_online({"is_online": True, "last_seen": "garbage"})
    print("  ok  presence requires the flag AND a recent heartbeat")


# ---------------- doctor privacy ----------------
def check_public_doctor():
    from doctors import public_doctor

    d = {
        "id": "d1", "name": "Dr Who", "email": "private@example.com",
        "licence_number": "LIC-999", "licence_doc_path": "campionai/uploads/x.pdf",
        "kyc": {"session_id": "kyc-abc"}, "user_id": "u-1",
        "is_online": False, "session_price": 40, "rating_avg": 4.5, "rating_count": 2,
    }
    pub = public_doctor(d)
    for leaked in ("email", "licence_number", "licence_doc_path", "kyc", "user_id"):
        assert leaked not in pub, f"public doctor payload leaks {leaked}"
    assert pub["session_price"] == 40.0 and pub["rating_avg"] == 4.5
    print("  ok  public doctor payload hides contact, licence and KYC data")


# ---------------- consult access gating ----------------
def check_access_rules():
    """Crisis is never gated. Volunteers are capped for free users. Paid doctors
    split by the configured commission."""
    from fastapi import HTTPException
    from consults import resolve_access

    class FakeColl:
        def __init__(self, count=0):
            self._count = count

        async def count_documents(self, q):
            # The cap must not count crisis sessions — assert the query says so.
            assert q.get("kind") == {"$ne": "crisis"}, "cap query must exclude crisis sessions"
            return self._count

    class FakeDB:
        def __init__(self, used):
            self.consult_sessions = FakeColl(used)

    settings = {"commission_pct": 15.0, "free_volunteer_sessions_per_month": 2}

    async def run(used, doctor, kind, plus_active):
        return await resolve_access(FakeDB(used), settings, {"id": "u1"}, doctor, kind, plus_active)

    volunteer = {"is_volunteer": True, "session_price": 0}
    paid = {"is_volunteer": False, "session_price": 40}

    loop = asyncio.new_event_loop()
    try:
        # Crisis: allowed even at the cap, even with no Plus.
        r = loop.run_until_complete(run(99, volunteer, "crisis", False))
        assert r["price"] == 0 and r["requires_payment"] is False

        # Free user under the cap.
        r = loop.run_until_complete(run(1, volunteer, "instant", False))
        assert r["requires_payment"] is False

        # Free user at the cap -> 402.
        try:
            loop.run_until_complete(run(2, volunteer, "instant", False))
            raise AssertionError("expected the monthly cap to block a third session")
        except HTTPException as e:
            assert e.status_code == 402

        # Plus user ignores the cap.
        r = loop.run_until_complete(run(99, volunteer, "instant", True))
        assert r["requires_payment"] is False

        # Paid doctor: 15% commission, doctor keeps the rest, and it must add up.
        r = loop.run_until_complete(run(0, paid, "scheduled", False))
        assert r["requires_payment"] is True
        assert r["price"] == 40.0 and r["commission"] == 6.0 and r["doctor_earning"] == 34.0
        assert round(r["commission"] + r["doctor_earning"], 2) == r["price"]
    finally:
        loop.close()
    print("  ok  crisis uncapped, volunteers capped, commission splits exactly")


# ---------------- the privacy invariant ----------------
def check_consult_chat_isolated():
    """Consult chat must never be written to `messages`: recent_transcript() and
    extract_memories() both read that collection unconditionally, so a stray write
    would feed clinical conversation into the AI's long-term memory."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "signaling.py"), encoding="utf-8").read()
    writes = re.findall(r"db\.(\w+)\.(?:insert_one|insert_many|update_one|update_many)", src)
    assert "messages" not in writes, f"signaling.py writes to db.messages: {writes}"
    assert "consult_messages" in writes, "signaling.py should persist chat to consult_messages"
    print("  ok  signaling writes consult chat to consult_messages, never messages")


if __name__ == "__main__":
    os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
    os.environ.setdefault("DB_NAME", "selfcheck")
    os.environ.setdefault("JWT_SECRET", "selfcheck-secret")

    checks = [
        check_safe_ext, check_turn_credentials, check_presence,
        check_public_doctor, check_access_rules, check_consult_chat_isolated,
    ]
    print("CampionAI self-checks")
    failed = 0
    for c in checks:
        try:
            c()
        except Exception as e:
            failed += 1
            print(f"  FAIL  {c.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(checks) - failed}/{len(checks)} passed")
    sys.exit(1 if failed else 0)
