# Auth: register/login/me + onboarding validation
import uuid
import requests


def test_register_returns_token_and_not_onboarded(api, client):
    email = f"TEST_{uuid.uuid4().hex[:10]}@campionai-qa.com"
    r = client.post(f"{api}/auth/register", json={"email": email, "password": "Test@12345", "preferred_name": "Newbie"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert isinstance(d["token"], str) and len(d["token"]) > 10
    assert d["user"]["email"] == email.lower()
    assert d["user"]["onboarded"] is False
    assert d["user"]["is_admin"] is False
    assert "_id" not in d["user"]

    # /auth/me with token
    me = client.get(f"{api}/auth/me", headers={"Authorization": f"Bearer {d['token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == email.lower()

    # duplicate registration
    dup = client.post(f"{api}/auth/register", json={"email": email, "password": "Test@12345", "preferred_name": "x"})
    assert dup.status_code == 400

    # login works
    lg = client.post(f"{api}/auth/login", json={"email": email, "password": "Test@12345"})
    assert lg.status_code == 200
    assert lg.json()["user"]["id"] == d["user"]["id"]


def test_login_bad_password(api, client):
    r = client.post(f"{api}/auth/login", json={"email": "admin@campionai.com", "password": "wrong-pass"})
    assert r.status_code == 401


def test_me_requires_auth(api):
    r = requests.get(f"{api}/auth/me", timeout=30)
    assert r.status_code in (401, 403)


def test_onboarding_rejects_missing_consents(api, client):
    email = f"TEST_{uuid.uuid4().hex[:10]}@campionai-qa.com"
    tok = client.post(f"{api}/auth/register", json={"email": email, "password": "Test@12345", "preferred_name": "C"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    payload = {
        "preferred_name": "C", "age_confirmed": False, "communication_style": "warm",
        "country": "US", "checkin_frequency": "daily",
        "trusted_contact": {"name": "A", "relationship": "friend", "phone": "1", "email": "a@b.com"},
        "safety_consent": True,
    }
    r = client.post(f"{api}/onboarding", json=payload, headers=h)
    assert r.status_code == 400, r.text

    payload["age_confirmed"] = True
    payload["safety_consent"] = False
    r2 = client.post(f"{api}/onboarding", json=payload, headers=h)
    assert r2.status_code == 400, r2.text

    payload["safety_consent"] = True
    r3 = client.post(f"{api}/onboarding", json=payload, headers=h)
    assert r3.status_code == 200, r3.text
    u = r3.json()
    assert u["onboarded"] is True
    assert u["country"] == "US"
    assert u["trusted_contact"]["name"] == "A"


def test_profile_update_persists(api, user_headers, client):
    r = client.put(f"{api}/profile", json={"preferred_name": "TEST_Renamed", "work": "barista", "goals": ["sleep more"]}, headers=user_headers)
    assert r.status_code == 200, r.text
    assert r.json()["profile"]["preferred_name"] == "TEST_Renamed"
    g = client.get(f"{api}/profile", headers=user_headers)
    assert g.status_code == 200
    p = g.json()["profile"]
    assert p["work"] == "barista"
    assert p["goals"] == ["sleep more"]


def test_private_mode_toggle(api, user_headers, client):
    r = client.put(f"{api}/settings/private-mode", json={"enabled": True}, headers=user_headers)
    assert r.status_code == 200 and r.json()["private_mode"] is True
    me = client.get(f"{api}/auth/me", headers=user_headers)
    assert me.json()["private_mode"] is True
    r2 = client.put(f"{api}/settings/private-mode", json={"enabled": False}, headers=user_headers)
    assert r2.json()["private_mode"] is False


def test_hotlines_us(api, user_headers, client):
    r = client.get(f"{api}/meta/hotlines", headers=user_headers)
    assert r.status_code == 200
    d = r.json()
    assert d["country"] == "US"
    text = str(d["hotlines"])
    assert "988" in text
