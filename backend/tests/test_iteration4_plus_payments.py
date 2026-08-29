"""Iteration 4: CampionAI Plus (wellness) gating, trial, plan/food/schedule, payments (Stripe Flow B)."""
import json
import uuid

import pytest
import requests

from conftest import API


def _register_onboarded(client, name="Nova"):
    email = f"TEST_{uuid.uuid4().hex[:8]}@campionqa.com"
    r = client.post(f"{API}/auth/register", json={"email": email, "password": "Test@12345", "preferred_name": name})
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    ro = client.post(f"{API}/onboarding", json={
        "preferred_name": name, "age_confirmed": True, "communication_style": "warm",
        "country": "US", "checkin_frequency": "daily",
        "trusted_contact": {"name": "Sam", "relationship": "friend", "phone": "+15550001111", "email": "sam@example.com"},
        "safety_consent": True,
    }, headers=h)
    assert ro.status_code == 200, ro.text
    return {"email": email, "token": token, "headers": h}


@pytest.fixture(scope="module")
def free_user(client):
    """User with NO Plus access (trial not started)."""
    return _register_onboarded(client, "Free")


@pytest.fixture(scope="module")
def plus_user(client):
    """User who started the 14-day trial."""
    u = _register_onboarded(client, "Plus")
    r = client.post(f"{API}/plus/start-trial", headers=u["headers"])
    assert r.status_code == 200, r.text
    return u


# ---------------- Plus gating (402) ----------------
class TestPlusGating:
    def test_status_none_for_new_user(self, client, free_user):
        r = client.get(f"{API}/plus/status", headers=free_user["headers"])
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["active"] is False
        assert d["trial_used"] is False
        assert d["until"] is None and d["trial_ends_at"] is None

    @pytest.mark.parametrize("path", ["/wellness/plan", "/wellness/food", "/wellness/events"])
    def test_gated_endpoints_402(self, client, free_user, path):
        r = client.get(f"{API}{path}", headers=free_user["headers"])
        assert r.status_code == 402, f"{path} -> {r.status_code} {r.text[:200]}"
        assert "Plus" in r.json().get("detail", "")

    def test_gated_post_402(self, client, free_user):
        r = client.post(f"{API}/wellness/food", json={"text": "TEST_apple"}, headers=free_user["headers"])
        assert r.status_code == 402
        r2 = client.post(f"{API}/wellness/plan/regenerate", headers=free_user["headers"])
        assert r2.status_code == 402

    def test_unauth_401(self, client):
        r = client.get(f"{API}/wellness/plan")
        assert r.status_code in (401, 403), r.status_code


# ---------------- 14-day trial ----------------
class TestTrial:
    def test_start_trial_grants_access(self, client):
        u = _register_onboarded(client, "Trialer")
        r = client.post(f"{API}/plus/start-trial", headers=u["headers"])
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["active"] is True
        assert d["status"] == "trialing"
        assert d["trial_used"] is True
        assert d["trial_ends_at"]

        # persisted on /plus/status and /auth/me
        s = client.get(f"{API}/plus/status", headers=u["headers"]).json()
        assert s["active"] is True and s["status"] == "trialing"
        me = client.get(f"{API}/auth/me", headers=u["headers"])
        assert me.status_code == 200
        assert me.json()["plus"]["active"] is True

        # one-time only
        r2 = client.post(f"{API}/plus/start-trial", headers=u["headers"])
        assert r2.status_code in (400, 402), r2.status_code

    def test_existing_user_trial_already_used(self, client):
        r = client.post(f"{API}/auth/login", json={"email": "test@campionai.com", "password": "Test@12345"})
        assert r.status_code == 200, r.text
        h = {"Authorization": f"Bearer {r.json()['token']}", "Content-Type": "application/json"}
        st = client.get(f"{API}/plus/status", headers=h).json()
        assert st["trial_used"] is True
        r2 = client.post(f"{API}/plus/start-trial", headers=h)
        assert r2.status_code in (400, 402)


# ---------------- Wellness plan ----------------
class TestWellnessPlan:
    def test_plan_autogenerates(self, client, plus_user):
        r = client.get(f"{API}/wellness/plan", headers=plus_user["headers"], timeout=180)
        assert r.status_code == 200, r.text
        plan = r.json()
        assert "_id" not in plan
        items = plan["items"]
        assert 4 <= len(items) <= 6, f"expected 4-6 items got {len(items)}"
        valid = {"meditation", "yoga", "breathing", "movement", "task"}
        for it in items:
            assert it["type"] in valid, it
            assert it["title"] and it["detail"]
            assert isinstance(it["duration_min"], int)
            assert it["done"] is False

        # idempotent for the day
        r2 = client.get(f"{API}/wellness/plan", headers=plus_user["headers"], timeout=60)
        assert r2.json()["id"] == plan["id"]

    def test_toggle_item(self, client, plus_user):
        client.get(f"{API}/wellness/plan", headers=plus_user["headers"], timeout=180)
        r = client.put(f"{API}/wellness/plan/toggle", json={"item_index": 0}, headers=plus_user["headers"])
        assert r.status_code == 200, r.text
        assert r.json()["items"][0]["done"] is True
        # persisted
        assert client.get(f"{API}/wellness/plan", headers=plus_user["headers"]).json()["items"][0]["done"] is True
        # toggle back
        r2 = client.put(f"{API}/wellness/plan/toggle", json={"item_index": 0}, headers=plus_user["headers"])
        assert r2.json()["items"][0]["done"] is False

    def test_toggle_out_of_range_404(self, client, plus_user):
        r = client.put(f"{API}/wellness/plan/toggle", json={"item_index": 99}, headers=plus_user["headers"])
        assert r.status_code == 404, r.status_code

    def test_regenerate(self, client, plus_user):
        old = client.get(f"{API}/wellness/plan", headers=plus_user["headers"], timeout=180).json()
        r = client.post(f"{API}/wellness/plan/regenerate", headers=plus_user["headers"], timeout=180)
        assert r.status_code == 200, r.text
        new = r.json()
        assert new["id"] != old["id"]
        assert 4 <= len(new["items"]) <= 6
        # GET returns the regenerated plan (single doc per day)
        after = client.get(f"{API}/wellness/plan", headers=plus_user["headers"]).json()
        assert after["id"] == new["id"], "regenerate did not replace today's plan"


# ---------------- Food log (AI macros) ----------------
class TestFoodLog:
    def test_log_food_and_totals(self, client, plus_user):
        h = plus_user["headers"]
        r = client.post(f"{API}/wellness/food", json={"text": "paneer tikka and 2 rotis"}, headers=h, timeout=180)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "_id" not in d
        assert d["calories"] > 0, f"AI returned no calories: {d}"
        assert d["protein_g"] > 0 and d["carbs_g"] > 0
        assert isinstance(d["fat_g"], int)
        assert d["summary"]
        fid = d["id"]

        lst = client.get(f"{API}/wellness/food", headers=h).json()
        ids = [x["id"] for x in lst["logs"]]
        assert fid in ids
        expected = sum(x["calories"] for x in lst["logs"])
        assert lst["totals"]["calories"] == expected

        # second log increases totals
        before = lst["totals"]["calories"]
        r2 = client.post(f"{API}/wellness/food", json={"text": "one banana"}, headers=h, timeout=180)
        assert r2.status_code == 200
        after = client.get(f"{API}/wellness/food", headers=h).json()
        assert after["totals"]["calories"] == before + r2.json()["calories"]

        # delete updates totals
        dr = client.delete(f"{API}/wellness/food/{fid}", headers=h)
        assert dr.status_code == 200
        final = client.get(f"{API}/wellness/food", headers=h).json()
        assert fid not in [x["id"] for x in final["logs"]]
        assert final["totals"]["calories"] == after["totals"]["calories"] - d["calories"]

    def test_food_cross_user_isolation(self, client, plus_user):
        other = _register_onboarded(client, "Other")
        client.post(f"{API}/plus/start-trial", headers=other["headers"])
        mine = client.post(f"{API}/wellness/food", json={"text": "TEST_oats bowl"}, headers=plus_user["headers"], timeout=180).json()
        theirs = client.get(f"{API}/wellness/food", headers=other["headers"]).json()
        assert mine["id"] not in [x["id"] for x in theirs["logs"]]
        # other user cannot delete my log
        client.delete(f"{API}/wellness/food/{mine['id']}", headers=other["headers"])
        still = client.get(f"{API}/wellness/food", headers=plus_user["headers"]).json()
        assert mine["id"] in [x["id"] for x in still["logs"]], "cross-user delete leaked"
        client.delete(f"{API}/wellness/food/{mine['id']}", headers=plus_user["headers"])


# ---------------- Schedule ----------------
class TestSchedule:
    def test_event_crud_and_sorting(self, client, plus_user):
        h = plus_user["headers"]
        import datetime as dt
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        e2 = client.post(f"{API}/wellness/events", json={"title": "TEST_late yoga", "start": f"{today}T18:30", "type": "task"}, headers=h)
        e1 = client.post(f"{API}/wellness/events", json={"title": "TEST_early walk", "start": f"{today}T07:15", "type": "task"}, headers=h)
        assert e1.status_code == 200 and e2.status_code == 200, (e1.text, e2.text)
        assert e1.json()["date"] == today
        assert "_id" not in e1.json()

        lst = client.get(f"{API}/wellness/events?date={today}", headers=h)
        assert lst.status_code == 200
        evs = lst.json()
        starts = [e["start"] for e in evs]
        assert starts == sorted(starts), f"events not sorted: {starts}"
        titles = [e["title"] for e in evs]
        assert "TEST_early walk" in titles and "TEST_late yoga" in titles

        for eid in (e1.json()["id"], e2.json()["id"]):
            assert client.delete(f"{API}/wellness/events/{eid}", headers=h).status_code == 200
        after = client.get(f"{API}/wellness/events?date={today}", headers=h).json()
        assert e1.json()["id"] not in [e["id"] for e in after]


# ---------------- Payments ----------------
class TestPayments:
    @pytest.mark.parametrize("pkg,amount", [("plus_monthly", 9.0), ("plus_yearly", 86.40), ("donate_15", 15.0)])
    def test_checkout_creates_stripe_session(self, client, free_user, pkg, amount):
        r = client.post(f"{API}/payments/checkout",
                        json={"package_id": pkg, "origin_url": "https://stripe-removal-flow.preview.emergentagent.com"},
                        headers=free_user["headers"], timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["checkout_url"].startswith("https://"), d
        assert "stripe" in d["checkout_url"], d["checkout_url"]
        assert d["session_id"]

        st = client.get(f"{API}/payments/status/{d['session_id']}", timeout=60)
        assert st.status_code == 200, st.text
        s = st.json()
        assert s["session_id"] == d["session_id"]
        assert s["payment_status"] in ("pending", "unpaid"), s
        assert s["status"] in ("initiated", "open", "pending"), s

    def test_checkout_invalid_package(self, client, free_user):
        r = client.post(f"{API}/payments/checkout", json={"package_id": "hacker_1", "origin_url": "https://x.com"},
                        headers=free_user["headers"])
        assert r.status_code == 400, r.status_code

    def test_checkout_requires_auth(self, client):
        r = client.post(f"{API}/payments/checkout", json={"package_id": "donate_5", "origin_url": "https://x.com"})
        assert r.status_code in (401, 403), r.status_code

    def test_status_unknown_session_404(self, client):
        r = client.get(f"{API}/payments/status/cs_test_doesnotexist_{uuid.uuid4().hex[:8]}")
        assert r.status_code == 404, r.status_code

    def test_checkout_does_not_grant_access(self, client, free_user):
        """Creating a session must NOT grant Plus before payment."""
        s = client.get(f"{API}/plus/status", headers=free_user["headers"]).json()
        assert s["active"] is False, s
        r = client.get(f"{API}/wellness/plan", headers=free_user["headers"])
        assert r.status_code == 402


# ---------------- Proactive coaching in chat (must not break chat) ----------------
class TestProactiveCoaching:
    def test_chat_stream_works_for_plus_user(self, client, plus_user):
        client.get(f"{API}/wellness/plan", headers=plus_user["headers"], timeout=180)
        chunks, done = [], None
        with requests.post(f"{API}/chat/stream", json={"message": "Hey, how's my day looking?"},
                           headers=plus_user["headers"], stream=True, timeout=180) as resp:
            assert resp.status_code == 200, resp.text
            for raw in resp.iter_lines(decode_unicode=True):
                if raw and raw.startswith("data: "):
                    ev = json.loads(raw[6:])
                    if ev.get("type") == "delta":
                        chunks.append(ev.get("content", ""))
                    if ev.get("type") == "done":
                        done = ev
        text = "".join(chunks)
        assert len(text) > 10, f"empty stream: {text!r}"
        assert done is not None, "no done event"
