# Health / basic reachability
import requests


def test_root(api):
    r = requests.get(f"{api}/", timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_countries_meta(api):
    r = requests.get(f"{api}/meta/countries", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) > 1
    codes = [c.get("code") for c in data]
    assert "US" in codes
