"""Iteration 3: redesign regression + Real Alerts (graceful degradation), Voice, Smarter check-ins."""
import json
import time
import uuid

import pytest
import requests

from conftest import API, ADMIN_EMAIL, ADMIN_PASSWORD


def _sse_events(resp):
    events = []
    for raw in resp.iter_lines(decode_unicode=True):
        if raw and raw.startswith("data: "):
            events.append(json.loads(raw[6:]))
    return events


# ---------------- Regression: register -> onboard -> chat stream ----------------
class TestChatRegression:
    def test_register_onboard_and_stream(self, client):
        email = f"TEST_{uuid.uuid4().hex[:8]}@campionqa.com"
        r = client.post(f"{API}/auth/register", json={"email": email, "password": "Test@12345", "preferred_name": "Rae"})
        assert r.status_code == 200, r.text
        token = r.json()["token"]
        assert r.json()["user"]["onboarded"] is False
        h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        ro = client.post(f"{API}/onboarding", json={
            "preferred_name": "Rae", "age_confirmed": True, "communication_style": "warm",
            "country": "US", "checkin_frequency": "daily",
            "trusted_contact": {"name": "Sam", "relationship": "friend", "phone": "+15550001111", "email": "sam@example.com"},
            "safety_consent": True,
        }, headers=h)
        assert ro.status_code == 200, ro.text
        assert ro.json()["onboarded"] is True

        with requests.post(f"{API}/chat/stream", json={"message": "Hi! I just started a new job as a nurse in Seattle."},
                           headers=h, stream=True, timeout=180) as resp:
            assert resp.status_code == 200, resp.text
            events = _sse_events(resp)
        assert events[0]["type"] == "meta"
        assert events[0]["risk"] in ("none", "low", "medium", "high")
        deltas = "".join(e.get("content", "") for e in events if e["type"] == "delta")
        assert len(deltas) > 10, f"no streamed reply: {events[:3]}"
        done = [e for e in events if e["type"] == "done"]
        assert done, "no done event"
        assert done[0]["escalation"] is None

        mem = client.get(f"{API}/memories", headers=h)
        assert mem.status_code == 200
        assert isinstance(mem.json(), list)

    def test_existing_user_login(self, client):
        r = client.post(f"{API}/auth/login", json={"email": "test@campionai.com", "password": "Test@12345"})
        assert r.status_code == 200, r.text
        assert r.json()["user"]["email"] == "test@campionai.com"
        assert "token" in r.json()


# ---------------- Escalation with no delivery keys ----------------
class TestEscalationGraceful:
    def test_high_risk_escalation_and_event(self, client, user_headers, admin_headers):
        with requests.post(f"{API}/chat/stream", json={"message": "I keep thinking about killing myself"},
                           headers=user_headers, stream=True, timeout=180) as resp:
            assert resp.status_code == 200, resp.text
            events = _sse_events(resp)
        meta = events[0]
        assert meta["risk"] == "high", f"expected high risk, got {meta}"
        done = [e for e in events if e["type"] == "done"][0]
        esc = done["escalation"]
        assert esc and esc["triggered"] is True
        assert esc["hotlines"] and len(esc["hotlines"]) > 0
        assert esc["trusted_contact"] is not None
        assert esc["professional"] is not None

        evs = client.get(f"{API}/safety/events", headers=user_headers)
        assert evs.status_code == 200
        mine = [e for e in evs.json() if e["risk_level"] == "high"]
        assert mine, "no high-risk safety event logged"
        actions = " ".join(mine[0]["actions_taken"])
        assert "Crisis hotlines surfaced" in actions
        assert "delivery not configured" in actions, f"expected graceful action strings, got {actions}"

        # admin sees it too
        ae = client.get(f"{API}/admin/safety-events", headers=admin_headers)
        assert ae.status_code == 200
        assert any(e["id"] == mine[0]["id"] for e in ae.json())

    def test_handoff_logs_event(self, client, user_headers):
        r = client.post(f"{API}/safety/handoff", headers=user_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["professional"] is not None
        assert body["consented_summary"]["consented"] is True
        assert isinstance(body["hotlines"], list) and body["hotlines"]
        evs = client.get(f"{API}/safety/events", headers=user_headers).json()
        ho = [e for e in evs if e["risk_level"] == "handoff_request"]
        assert ho, "handoff event not logged"
        assert "User-initiated handoff" in ho[0]["actions_taken"]
        assert any("delivery not configured" in a or "alert sent" in a for a in ho[0]["actions_taken"])


# ---------------- Smarter check-in ----------------
class TestCheckin:
    def test_checkin_due_and_personalized(self, client, register_user):
        u = register_user(onboard=True, freq="daily")
        h = {"Authorization": f"Bearer {u['token']}", "Content-Type": "application/json"}
        # give the user prior context
        with requests.post(f"{API}/chat/stream", json={"message": "My dog Biscuit had surgery yesterday and I'm anxious about it."},
                           headers=h, stream=True, timeout=180) as resp:
            assert resp.status_code == 200
            _sse_events(resp)
        r = client.get(f"{API}/checkin", headers=h)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["due"] is True, body
        assert isinstance(body["message"], str) and len(body["message"]) > 10
        # second call should not be due (last_checkin persisted)
        r2 = client.get(f"{API}/checkin", headers=h)
        assert r2.status_code == 200
        assert r2.json()["due"] is False

    def test_checkin_off(self, client, register_user):
        u = register_user(onboard=True, freq="off")
        h = {"Authorization": f"Bearer {u['token']}"}
        r = client.get(f"{API}/checkin", headers=h)
        assert r.status_code == 200
        assert r.json() == {"due": False}


# ---------------- Voice ----------------
class TestVoice:
    def test_voice_status_disabled(self, client, user_headers):
        r = client.get(f"{API}/voice/status", headers=user_headers)
        assert r.status_code == 200, r.text
        assert r.json() == {"enabled": False}

    def test_tts_400_when_unconfigured(self, client, user_headers):
        r = client.post(f"{API}/voice/tts", json={"text": "hello there"}, headers=user_headers)
        assert r.status_code == 400, f"{r.status_code} {r.text[:300]}"
        assert "not configured" in r.json()["detail"].lower()

    def test_voice_endpoints_require_auth(self, client):
        assert client.get(f"{API}/voice/status").status_code in (401, 403)
        assert client.post(f"{API}/voice/tts", json={"text": "x"}).status_code in (401, 403)


# ---------------- Admin voice settings + integrations ----------------
class TestAdminVoiceAlerts:
    def test_integrations_all_unconfigured(self, client, admin_headers):
        r = client.get(f"{API}/admin/integrations", headers=admin_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ["email_resend", "sms_twilio", "voice_fish"]:
            assert k in body
            assert body[k] is False, f"{k} unexpectedly configured"

    def test_get_and_persist_voice_settings(self, client, admin_headers):
        r = client.get(f"{API}/admin/voice-settings", headers=admin_headers)
        assert r.status_code == 200, r.text
        orig = r.json()
        assert set(["enabled", "voice_id", "key_set"]).issubset(orig.keys())
        assert orig["key_set"] is False

        p = client.put(f"{API}/admin/voice-settings",
                       json={"enabled": True, "voice_id": "TEST_voice_123"}, headers=admin_headers)
        assert p.status_code == 200, p.text
        g = client.get(f"{API}/admin/voice-settings", headers=admin_headers).json()
        assert g["enabled"] is True
        assert g["voice_id"] == "TEST_voice_123"
        assert g["key_set"] is False
        # voice/status must still be false because no key
        # restore
        p2 = client.put(f"{API}/admin/voice-settings", json={"enabled": orig["enabled"], "voice_id": orig["voice_id"]},
                        headers=admin_headers)
        assert p2.status_code == 200
        g2 = client.get(f"{API}/admin/voice-settings", headers=admin_headers).json()
        assert g2["voice_id"] == orig["voice_id"]

    def test_voice_settings_admin_only(self, client, user_headers):
        assert client.get(f"{API}/admin/voice-settings", headers=user_headers).status_code == 403
        assert client.put(f"{API}/admin/voice-settings", json={"enabled": True}, headers=user_headers).status_code == 403
        assert client.get(f"{API}/admin/integrations", headers=user_headers).status_code == 403


# ---------------- Admin regression ----------------
class TestAdminRegression:
    def test_model_routing_save(self, client, admin_headers):
        r = client.get(f"{API}/admin/model-config", headers=admin_headers)
        assert r.status_code == 200
        routes = r.json()
        assert "medium" in routes
        orig = routes["medium"]
        p = client.put(f"{API}/admin/model-config",
                       json={"tier": "medium", "provider": orig["provider"], "model": orig["model"]},
                       headers=admin_headers)
        assert p.status_code == 200, p.text
        assert client.get(f"{API}/admin/model-config", headers=admin_headers).json()["medium"] == orig

    def test_professional_add_delete(self, client, admin_headers):
        r = client.post(f"{API}/admin/professionals", json={
            "name": "TEST_Dr QA", "credentials": "PsyD", "specialty": "QA",
            "contact": "qa@example.com", "verified": False, "availability": "on-call",
        }, headers=admin_headers)
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        assert "_id" not in r.json()
        lst = client.get(f"{API}/admin/professionals", headers=admin_headers).json()
        assert any(p["id"] == pid for p in lst)
        d = client.delete(f"{API}/admin/professionals/{pid}", headers=admin_headers)
        assert d.status_code == 200
        lst2 = client.get(f"{API}/admin/professionals", headers=admin_headers).json()
        assert not any(p["id"] == pid for p in lst2)
        assert client.delete(f"{API}/admin/professionals/{pid}", headers=admin_headers).status_code == 404

    def test_resolve_safety_event(self, client, admin_headers):
        evs = client.get(f"{API}/admin/safety-events", headers=admin_headers).json()
        open_evs = [e for e in evs if not e.get("resolved")]
        if not open_evs:
            pytest.skip("no open safety events")
        eid = open_evs[0]["id"]
        r = client.put(f"{API}/admin/safety-events/{eid}/resolve", headers=admin_headers)
        assert r.status_code == 200, r.text
        after = client.get(f"{API}/admin/safety-events", headers=admin_headers).json()
        assert [e for e in after if e["id"] == eid][0]["resolved"] is True

    def test_admin_stats(self, client, admin_headers):
        r = client.get(f"{API}/admin/stats", headers=admin_headers)
        assert r.status_code == 200
        for k in ["users", "sessions", "messages", "memories", "safety_events", "professionals"]:
            assert isinstance(r.json()[k], int)
