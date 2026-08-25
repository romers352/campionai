# Chat SSE streaming, memory extraction, safety escalation, checkin, handoff, data controls
import json
import time
import requests
import pytest


def _stream(api, headers, message, session_id=None, timeout=180):
    body = {"message": message}
    if session_id:
        body["session_id"] = session_id
    r = requests.post(f"{api}/chat/stream", json=body, headers=headers, stream=True, timeout=timeout)
    assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
    events = []
    for line in r.iter_lines(decode_unicode=True):
        if line and line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


@pytest.fixture(scope="module")
def chat_state():
    return {}


def test_chat_normal_stream(api, user_headers, chat_state):
    events = _stream(api, user_headers, "Hey! I just started a new job as a nurse at Mercy Hospital and my name is Sam.")
    kinds = [e["type"] for e in events]
    assert kinds[0] == "meta", kinds[:3]
    assert "delta" in kinds, kinds
    assert kinds[-1] == "done"
    meta = events[0]
    assert meta["risk"] in ("none", "low", "medium", "high")
    assert meta["private"] is False
    chat_state["session_id"] = meta["session_id"]
    reply = "".join(e["content"] for e in events if e["type"] == "delta")
    assert len(reply.strip()) > 5, f"empty reply: {reply!r}"
    done = events[-1]
    assert done["escalation"] is None
    chat_state["memories_saved"] = done["memories_saved"]


def test_history_persists(api, user_headers, client, chat_state):
    sid = chat_state.get("session_id")
    assert sid, "no session from previous test"
    r = client.get(f"{api}/sessions/{sid}/messages", headers=user_headers)
    assert r.status_code == 200, r.text
    d = r.json()
    roles = [m["role"] for m in d["messages"]]
    assert roles[:2] == ["user", "assistant"]
    assert all("_id" not in m for m in d["messages"])
    # session listed
    ls = client.get(f"{api}/sessions", headers=user_headers)
    assert ls.status_code == 200
    assert any(s["id"] == sid for s in ls.json())


def test_memories_saved_and_deletable(api, user_headers, client, chat_state):
    r = client.get(f"{api}/memories", headers=user_headers)
    assert r.status_code == 200, r.text
    mems = r.json()
    assert isinstance(mems, list)
    assert len(mems) > 0, "no memories extracted from durable-fact message"
    m = mems[0]
    for k in ("id", "content", "category", "tier", "importance"):
        assert k in m
    assert m["tier"] in ("SESSION", "TEMPORARY", "LONG_TERM")
    before = len(mems)
    d = client.delete(f"{api}/memories/{m['id']}", headers=user_headers)
    assert d.status_code == 200
    after = client.get(f"{api}/memories", headers=user_headers).json()
    assert len(after) == before - 1
    assert all(x["id"] != m["id"] for x in after)


def test_private_mode_no_memory_persist(api, user_headers, client):
    client.put(f"{api}/settings/private-mode", json={"enabled": True}, headers=user_headers)
    before = len(client.get(f"{api}/memories", headers=user_headers).json())
    events = _stream(api, user_headers, "By the way I am studying astrophysics at MIT and love hiking.")
    assert events[0]["private"] is True
    assert events[-1]["memories_saved"] == 0
    after = len(client.get(f"{api}/memories", headers=user_headers).json())
    assert after == before
    client.put(f"{api}/settings/private-mode", json={"enabled": False}, headers=user_headers)


def test_high_risk_escalation(api, register_user, client):
    u = register_user(onboard=True)
    h = {"Authorization": f"Bearer {u['token']}", "Content-Type": "application/json"}
    events = _stream(api, h, "I keep thinking about killing myself")
    assert events[0]["risk"] == "high"
    done = events[-1]
    esc = done["escalation"]
    assert esc and esc["triggered"] is True
    assert "988" in str(esc["hotlines"])
    assert esc["trusted_contact"]["name"] == "Alex Friend"
    assert esc["professional"] and esc["professional"]["verified"] is True
    assert "_id" not in esc["professional"]

    ev = client.get(f"{api}/safety/events", headers=h)
    assert ev.status_code == 200
    evs = ev.json()
    assert len(evs) >= 1
    assert evs[0]["risk_level"] == "high"
    # actions_taken now uses notifications.summarize() wording (graceful when no delivery keys)
    assert any("Trusted contact" in a for a in evs[0]["actions_taken"])
    assert any("alert queued (delivery not configured)" in a or "alert sent via" in a for a in evs[0]["actions_taken"])


def test_handoff(api, user_headers, client):
    r = client.post(f"{api}/safety/handoff", headers=user_headers)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["professional"] and d["professional"]["name"]
    assert "988" in str(d["hotlines"])
    assert d["consented_summary"]["consented"] is True


def test_checkin_due_then_not_due(api, register_user, client):
    u = register_user(onboard=True, freq="daily")
    h = {"Authorization": f"Bearer {u['token']}", "Content-Type": "application/json"}
    r = client.get(f"{api}/checkin", headers=h, timeout=120)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["due"] is True
    assert isinstance(d["message"], str) and len(d["message"]) > 5
    r2 = client.get(f"{api}/checkin", headers=h, timeout=120)
    assert r2.json()["due"] is False


def test_checkin_off(api, register_user, client):
    u = register_user(onboard=True, freq="off")
    h = {"Authorization": f"Bearer {u['token']}"}
    r = client.get(f"{api}/checkin", headers=h)
    assert r.status_code == 200
    assert r.json()["due"] is False


def test_chat_invalid_session_404(api, user_headers, client):
    r = client.post(f"{api}/chat/stream", json={"message": "hi", "session_id": "does-not-exist"}, headers=user_headers)
    assert r.status_code == 404


def test_cross_user_session_isolation(api, register_user, client, chat_state):
    other = register_user(onboard=True)
    h = {"Authorization": f"Bearer {other['token']}"}
    sid = chat_state.get("session_id")
    r = client.get(f"{api}/sessions/{sid}/messages", headers=h)
    assert r.status_code == 404


def test_export_and_delete_everything(api, register_user, client):
    u = register_user(onboard=True)
    h = {"Authorization": f"Bearer {u['token']}", "Content-Type": "application/json"}
    _stream(api, h, "I have a golden retriever named Biscuit.")
    exp = client.get(f"{api}/data/export", headers=h)
    assert exp.status_code == 200, exp.text
    d = exp.json()
    for k in ("exported_at", "profile", "sessions", "messages", "memories"):
        assert k in d
    assert len(d["messages"]) >= 2
    dele = client.delete(f"{api}/data/delete-everything", headers=h)
    assert dele.status_code == 200 and dele.json()["deleted"] is True
    me = client.get(f"{api}/auth/me", headers=h)
    assert me.status_code in (401, 404), me.status_code
    lg = client.post(f"{api}/auth/login", json={"email": u["email"], "password": u["password"]})
    assert lg.status_code == 401
