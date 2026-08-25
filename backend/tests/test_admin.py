# Admin: stats, model config, provider settings, professionals, safety events, RBAC
import requests


def test_admin_rbac(api, user_headers, client):
    for path in ["/admin/stats", "/admin/professionals", "/admin/safety-events", "/admin/model-config"]:
        r = client.get(f"{api}{path}", headers=user_headers)
        assert r.status_code == 403, f"{path} -> {r.status_code}"
    r = requests.get(f"{api}/admin/stats", timeout=30)
    assert r.status_code in (401, 403)


def test_admin_stats(api, admin_headers, client):
    r = client.get(f"{api}/admin/stats", headers=admin_headers)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("users", "sessions", "messages", "memories", "safety_events", "professionals", "open_safety_events"):
        assert k in d and isinstance(d[k], int)
    assert d["users"] >= 1


def test_model_config_update(api, admin_headers, client):
    r = client.get(f"{api}/admin/model-config", headers=admin_headers)
    assert r.status_code == 200
    routes = r.json()
    assert "medium" in routes and "provider" in routes["medium"]
    original = routes["cheap"]
    up = client.put(f"{api}/admin/model-config", json={"tier": "cheap", "provider": "emergent", "model": "gpt-4o-mini"}, headers=admin_headers)
    assert up.status_code == 200, up.text
    after = client.get(f"{api}/admin/model-config", headers=admin_headers).json()
    assert after["cheap"]["model"] == "gpt-4o-mini"
    # restore
    client.put(f"{api}/admin/model-config", json={"tier": "cheap", **original}, headers=admin_headers)


def test_provider_settings(api, admin_headers, client):
    r = client.get(f"{api}/admin/provider-settings", headers=admin_headers)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["llm_provider"] in ("emergent", "openrouter")
    assert "openrouter_api_key" not in d
    assert isinstance(d["openrouter_api_key_set"], bool)
    up = client.put(f"{api}/admin/provider-settings", json={"llm_provider": "emergent"}, headers=admin_headers)
    assert up.status_code == 200


def test_professionals_crud(api, admin_headers, client):
    payload = {"name": "TEST_Dr Who", "credentials": "MD", "specialty": "crisis",
               "contact": "who@example.com", "verified": True, "availability": "on-call"}
    c = client.post(f"{api}/admin/professionals", json=payload, headers=admin_headers)
    assert c.status_code == 200, c.text
    doc = c.json()
    assert doc["name"] == payload["name"] and "id" in doc and "_id" not in doc
    lst = client.get(f"{api}/admin/professionals", headers=admin_headers).json()
    assert any(p["id"] == doc["id"] for p in lst)
    d = client.delete(f"{api}/admin/professionals/{doc['id']}", headers=admin_headers)
    assert d.status_code == 200
    lst2 = client.get(f"{api}/admin/professionals", headers=admin_headers).json()
    assert all(p["id"] != doc["id"] for p in lst2)


def test_safety_events_and_resolve(api, admin_headers, client):
    r = client.get(f"{api}/admin/safety-events", headers=admin_headers)
    assert r.status_code == 200, r.text
    evs = r.json()
    assert isinstance(evs, list) and len(evs) >= 1, "expected safety events from chat tests"
    ev = next((e for e in evs if not e.get("resolved")), evs[0])
    up = client.put(f"{api}/admin/safety-events/{ev['id']}/resolve", headers=admin_headers)
    assert up.status_code == 200
    after = client.get(f"{api}/admin/safety-events", headers=admin_headers).json()
    match = next(e for e in after if e["id"] == ev["id"])
    assert match["resolved"] is True
    assert "resolved_at" in match
