import os
import uuid
import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = BASE_URL + "/api"

ADMIN_EMAIL = "admin@campionai.com"
ADMIN_PASSWORD = "Admin@12345"


@pytest.fixture(scope="session")
def api():
    return API


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _register(client, onboard=True, country="US", freq="daily"):
    email = f"TEST_{uuid.uuid4().hex[:10]}@campionai-qa.com"
    password = "Test@12345"
    r = client.post(f"{API}/auth/register", json={"email": email, "password": password, "preferred_name": "Tester"})
    assert r.status_code == 200, r.text
    data = r.json()
    token = data["token"]
    if onboard:
        ro = client.post(f"{API}/onboarding", json={
            "preferred_name": "Tester", "age_confirmed": True, "communication_style": "warm",
            "country": country, "checkin_frequency": freq,
            "trusted_contact": {"name": "Alex Friend", "relationship": "friend", "phone": "+15551234567", "email": "alex@example.com"},
            "safety_consent": True,
        }, headers={"Authorization": f"Bearer {token}"})
        assert ro.status_code == 200, ro.text
    return {"email": email, "password": password, "token": token, "user": data["user"]}


@pytest.fixture(scope="session")
def fresh_user(client):
    return _register(client, onboard=True)


@pytest.fixture(scope="session")
def user_headers(fresh_user):
    return {"Authorization": f"Bearer {fresh_user['token']}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def admin_headers(client):
    r = client.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if r.status_code != 200:
        pytest.fail(f"Admin login failed: {r.status_code} {r.text[:300]}")
    body = r.json()
    assert body["user"]["is_admin"] is True
    return {"Authorization": f"Bearer {body['token']}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def register_user(client):
    return lambda **kw: _register(client, **kw)
