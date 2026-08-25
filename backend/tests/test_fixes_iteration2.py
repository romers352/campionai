"""Iteration-2 regression tests for the backend validation fixes."""
import uuid
import requests


# ---- PUT /api/settings/private-mode now uses a Pydantic model ----
class TestPrivateModeValidation:
    def test_toggle_on_and_off(self, api, client, user_headers):
        r = client.put(f"{api}/settings/private-mode", json={"enabled": True}, headers=user_headers)
        assert r.status_code == 200, r.text
        assert r.json()["private_mode"] is True
        me = client.get(f"{api}/auth/me", headers=user_headers)
        assert me.status_code == 200
        assert me.json()["private_mode"] is True

        r = client.put(f"{api}/settings/private-mode", json={"enabled": False}, headers=user_headers)
        assert r.status_code == 200
        assert r.json()["private_mode"] is False
        assert client.get(f"{api}/auth/me", headers=user_headers).json()["private_mode"] is False

    def test_junk_body_rejected(self, api, client, user_headers):
        r = client.put(f"{api}/settings/private-mode", json={"foo": "bar"}, headers=user_headers)
        assert r.status_code == 422, f"expected 422 validation error, got {r.status_code} {r.text[:200]}"

    def test_wrong_type_rejected(self, api, client, user_headers):
        r = client.put(f"{api}/settings/private-mode", json={"enabled": "notabool"}, headers=user_headers)
        assert r.status_code == 422, r.text
        # state unchanged
        assert client.get(f"{api}/auth/me", headers=user_headers).json()["private_mode"] is False


# ---- Provider settings / openrouter model listing validation ----
class TestProviderValidation:
    def test_switch_to_openrouter_without_key_is_400(self, api, client, admin_headers):
        cur = client.get(f"{api}/admin/provider-settings", headers=admin_headers)
        assert cur.status_code == 200, cur.text
        body = cur.json()
        if body.get("openrouter_api_key_set"):
            import pytest
            pytest.skip("OpenRouter key already configured; cannot assert the no-key path")
        r = client.put(f"{api}/admin/provider-settings",
                       json={"llm_provider": "openrouter", "openrouter_api_key": ""},
                       headers=admin_headers)
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text[:200]}"
        assert "openrouter" in r.json().get("detail", "").lower()
        # provider unchanged
        after = client.get(f"{api}/admin/provider-settings", headers=admin_headers).json()
        assert after["llm_provider"] != "openrouter"

    def test_openrouter_models_without_key_is_400(self, api, client, admin_headers):
        cur = client.get(f"{api}/admin/provider-settings", headers=admin_headers).json()
        if cur.get("openrouter_api_key_set"):
            import pytest
            pytest.skip("OpenRouter key configured")
        r = client.get(f"{api}/admin/openrouter-models", headers=admin_headers)
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text[:300]}"
        assert "key" in r.json().get("detail", "").lower()

    def test_emergent_provider_still_settable(self, api, client, admin_headers):
        r = client.put(f"{api}/admin/provider-settings",
                       json={"llm_provider": "emergent", "openrouter_api_key": ""},
                       headers=admin_headers)
        assert r.status_code == 200, r.text
        assert client.get(f"{api}/admin/provider-settings", headers=admin_headers).json()["llm_provider"] == "emergent"


# ---- 404 on non-existent resource mutations ----
class TestNotFoundMutations:
    def test_delete_missing_memory_404(self, api, client, user_headers):
        r = client.delete(f"{api}/memories/{uuid.uuid4().hex}", headers=user_headers)
        assert r.status_code == 404, f"got {r.status_code} {r.text[:200]}"

    def test_update_missing_memory_404(self, api, client, user_headers):
        r = client.put(f"{api}/memories/{uuid.uuid4().hex}", json={"content": "x"}, headers=user_headers)
        assert r.status_code in (404, 422), f"got {r.status_code} {r.text[:200]}"

    def test_delete_missing_professional_404(self, api, client, admin_headers):
        r = client.delete(f"{api}/admin/professionals/{uuid.uuid4().hex}", headers=admin_headers)
        assert r.status_code == 404, f"got {r.status_code} {r.text[:200]}"

    def test_resolve_missing_safety_event_404(self, api, client, admin_headers):
        r = client.put(f"{api}/admin/safety-events/{uuid.uuid4().hex}/resolve", headers=admin_headers)
        assert r.status_code == 404, f"got {r.status_code} {r.text[:200]}"
