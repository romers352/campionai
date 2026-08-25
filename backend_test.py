#!/usr/bin/env python3
"""
Backend test suite for CampionAI PayPal LIVE subscription integration.
Tests error paths, auth-gating, and endpoint wiring WITHOUT creating real subscriptions.
"""
import requests
import json

# Backend URL from frontend/.env
BASE_URL = "https://fervent-carver-8.preview.emergentagent.com/api"

# Test credentials from review request
ADMIN_EMAIL = "admin@campionai.com"
ADMIN_PASSWORD = "Admin@12345"


def test_login():
    """Test basic auth login endpoint"""
    print("\n=== Testing POST /api/auth/login ===")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in response"
    assert "user" in data, "No user in response"
    print("✅ Login successful")
    return data["token"]


def test_me_endpoint(token):
    """Test /api/auth/me endpoint"""
    print("\n=== Testing GET /api/auth/me ===")
    response = requests.get(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200, f"/me failed: {response.text}"
    data = response.json()
    assert "email" in data, "No email in response"
    print("✅ /api/auth/me working")
    return data


def test_plus_status(token):
    """Test /api/plus/status endpoint"""
    print("\n=== Testing GET /api/plus/status ===")
    response = requests.get(
        f"{BASE_URL}/plus/status",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200, f"/plus/status failed: {response.text}"
    data = response.json()
    assert "active" in data, "No active field in response"
    assert "status" in data, "No status field in response"
    print("✅ /api/plus/status working")


def test_webhook_invalid_signature():
    """Test POST /api/webhook/paypal with fake payload and no valid signature"""
    print("\n=== Testing POST /api/webhook/paypal (invalid signature) ===")
    fake_payload = {
        "event_type": "BILLING.SUBSCRIPTION.ACTIVATED",
        "resource": {"id": "I-TEST123"}
    }
    # Send without PayPal signature headers - should be rejected
    response = requests.post(
        f"{BASE_URL}/webhook/paypal",
        json=fake_payload,
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert "signature" in response.text.lower() or "invalid" in response.text.lower(), \
        "Response should mention signature verification failure"
    print("✅ Webhook correctly rejects invalid signature (400)")


def test_webhook_malformed_body():
    """Test POST /api/webhook/paypal with malformed body - should not crash"""
    print("\n=== Testing POST /api/webhook/paypal (malformed body) ===")
    # Send malformed JSON
    response = requests.post(
        f"{BASE_URL}/webhook/paypal",
        data="this is not json",
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    # Should return 400, not 500 (server crash)
    assert response.status_code in [400, 422], \
        f"Expected 400/422 for malformed body, got {response.status_code}"
    print("✅ Webhook handles malformed body gracefully (no 500 crash)")


def test_paypal_activate_no_auth():
    """Test POST /api/paypal/activate without JWT - should return 401/403"""
    print("\n=== Testing POST /api/paypal/activate (no auth) ===")
    response = requests.post(
        f"{BASE_URL}/paypal/activate",
        json={"subscription_id": "I-BOGUS123", "plan_key": "monthly"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    assert response.status_code in [401, 403], \
        f"Expected 401/403 without auth, got {response.status_code}"
    print("✅ /api/paypal/activate correctly requires auth (401/403)")


def test_paypal_activate_bogus_subscription(token):
    """Test POST /api/paypal/activate with valid JWT but bogus subscription_id"""
    print("\n=== Testing POST /api/paypal/activate (bogus subscription_id) ===")
    response = requests.post(
        f"{BASE_URL}/paypal/activate",
        json={"subscription_id": "I-BOGUS123", "plan_key": "monthly"},
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Should return 400 (verification failed), NOT "PayPal is not configured"
    assert response.status_code == 400, \
        f"Expected 400 for bogus subscription, got {response.status_code}"
    
    response_text = response.text.lower()
    assert "paypal is not configured" not in response_text, \
        "Should NOT return 'PayPal is not configured' - creds are set!"
    
    # Should mention verification failure or subscription not found
    assert "verify" in response_text or "subscription" in response_text or "not" in response_text, \
        "Response should indicate verification/subscription issue"
    
    print("✅ /api/paypal/activate correctly attempts verification and fails gracefully (400)")
    print(f"   Detail message: {response.json().get('detail', 'N/A')}")


def main():
    print("=" * 70)
    print("CampionAI PayPal LIVE Integration - Backend Tests")
    print("Testing error paths, auth-gating, and endpoint wiring")
    print("NO REAL SUBSCRIPTIONS WILL BE CREATED")
    print("=" * 70)
    
    try:
        # 1. Test existing endpoints (spot-check)
        token = test_login()
        test_me_endpoint(token)
        test_plus_status(token)
        
        # 2. Test webhook endpoint
        test_webhook_invalid_signature()
        test_webhook_malformed_body()
        
        # 3. Test PayPal activate endpoint
        test_paypal_activate_no_auth()
        test_paypal_activate_bogus_subscription(token)
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        
    except AssertionError as e:
        print("\n" + "=" * 70)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 70)
        raise
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"❌ UNEXPECTED ERROR: {e}")
        print("=" * 70)
        raise


if __name__ == "__main__":
    main()
