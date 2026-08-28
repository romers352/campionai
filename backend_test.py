#!/usr/bin/env python3
"""
Backend test suite for CampionAI.
Tests PayPal LIVE subscription integration and Emergent Google OAuth.
Tests error paths, auth-gating, and endpoint wiring WITHOUT creating real subscriptions.
"""
import requests
import json
import uuid

# Backend URL from frontend/.env
BASE_URL = "https://fix-it-features.preview.emergentagent.com/api"

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


# ============ Google Sign-in (Emergent OAuth) Tests ============

def test_google_session_bogus():
    """Test POST /api/auth/google/session with bogus session_id - must return 401"""
    print("\n=== Testing POST /api/auth/google/session (bogus session_id) ===")
    response = requests.post(
        f"{BASE_URL}/auth/google/session",
        json={"session_id": "bogus-xyz-12345"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Must return 401, NOT 500
    assert response.status_code == 401, \
        f"Expected 401 for bogus session_id, got {response.status_code}"
    
    # Must contain the expected error message
    response_json = response.json()
    detail = response_json.get("detail", "").lower()
    assert "could not verify google sign-in" in detail, \
        f"Expected 'Could not verify Google sign-in', got: {response_json.get('detail')}"
    
    print("✅ Bogus session_id correctly returns 401 with 'Could not verify Google sign-in'")


def test_google_session_missing_body():
    """Test POST /api/auth/google/session with missing body - should return 422, NOT 500"""
    print("\n=== Testing POST /api/auth/google/session (missing body) ===")
    response = requests.post(
        f"{BASE_URL}/auth/google/session",
        json={}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Should return 422 (validation error) or 401, NOT 500
    assert response.status_code in [422, 401, 400], \
        f"Expected 422/401/400 for missing session_id, got {response.status_code}"
    
    print(f"✅ Missing session_id returns {response.status_code} (validation error, no crash)")


def test_google_session_empty_session_id():
    """Test POST /api/auth/google/session with empty session_id - should return 401, NOT 500"""
    print("\n=== Testing POST /api/auth/google/session (empty session_id) ===")
    response = requests.post(
        f"{BASE_URL}/auth/google/session",
        json={"session_id": ""}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Should return 401 or 422, NOT 500
    assert response.status_code in [401, 422, 400], \
        f"Expected 401/422/400 for empty session_id, got {response.status_code}"
    
    print(f"✅ Empty session_id returns {response.status_code} (no crash)")


def test_google_session_null_body():
    """Test POST /api/auth/google/session with null/malformed body - should not crash"""
    print("\n=== Testing POST /api/auth/google/session (malformed body) ===")
    response = requests.post(
        f"{BASE_URL}/auth/google/session",
        data="not json",
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Should return 422 or 400, NOT 500
    assert response.status_code in [422, 400], \
        f"Expected 422/400 for malformed body, got {response.status_code}"
    
    print(f"✅ Malformed body returns {response.status_code} (no crash)")


# ============ No-regression: Email/Password Auth Tests ============

def test_register_new_user():
    """Test POST /api/auth/register with fresh random email - should return 200 with token"""
    print("\n=== Testing POST /api/auth/register (new user) ===")
    random_email = f"testuser_{uuid.uuid4().hex[:8]}@campionai-test.com"
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": random_email,
            "password": "TestPass123!",
            "preferred_name": "Test User"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 200, \
        f"Expected 200 for new registration, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert "token" in data, "No token in registration response"
    assert "user" in data, "No user in registration response"
    assert data["user"]["email"] == random_email.lower(), "Email mismatch"
    
    print(f"✅ New user registration successful: {random_email}")
    return random_email


def test_register_duplicate_email(email):
    """Test POST /api/auth/register with duplicate email - should return 400"""
    print("\n=== Testing POST /api/auth/register (duplicate email) ===")
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": email,
            "password": "AnotherPass456!",
            "preferred_name": "Duplicate User"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    assert response.status_code == 400, \
        f"Expected 400 for duplicate email, got {response.status_code}"
    
    response_json = response.json()
    detail = response_json.get("detail", "").lower()
    assert "already registered" in detail or "already exists" in detail, \
        f"Expected 'already registered' message, got: {response_json.get('detail')}"
    
    print("✅ Duplicate email correctly returns 400 with 'Email already registered'")


# ============ Contact Form Tests (PUBLIC endpoint) ============

def test_contact_valid_payload():
    """Test POST /api/contact with valid payload - should return 200 with ok:true"""
    print("\n=== Testing POST /api/contact (valid payload) ===")
    response = requests.post(
        f"{BASE_URL}/contact",
        json={
            "name": "Jane Test",
            "email": "jane@example.com",
            "subject": "Hi",
            "message": "Hello there"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 200, \
        f"Expected 200 for valid contact form, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data.get("ok") is True, "Expected ok:true in response"
    assert "message" in data, "Expected message field in response"
    
    print("✅ Valid contact form submission successful")


def test_contact_no_auth():
    """Test POST /api/contact WITHOUT Authorization header - should work (public endpoint)"""
    print("\n=== Testing POST /api/contact (no auth header - public) ===")
    response = requests.post(
        f"{BASE_URL}/contact",
        json={
            "name": "Public User",
            "email": "public@example.com",
            "subject": "Testing public access",
            "message": "This should work without authentication"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 200, \
        f"Expected 200 for public contact form (no auth), got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data.get("ok") is True, "Expected ok:true in response"
    
    print("✅ Contact form works without authentication (public endpoint)")


def test_contact_invalid_email():
    """Test POST /api/contact with invalid email - should return 422"""
    print("\n=== Testing POST /api/contact (invalid email) ===")
    response = requests.post(
        f"{BASE_URL}/contact",
        json={
            "name": "Jane",
            "email": "not-an-email",
            "message": "hey"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    assert response.status_code == 422, \
        f"Expected 422 for invalid email, got {response.status_code}"
    
    print("✅ Invalid email correctly returns 422 (validation error)")


def test_contact_missing_name():
    """Test POST /api/contact with missing name - should return 422"""
    print("\n=== Testing POST /api/contact (missing name) ===")
    response = requests.post(
        f"{BASE_URL}/contact",
        json={
            "email": "a@b.com",
            "message": "hi"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    assert response.status_code == 422, \
        f"Expected 422 for missing name, got {response.status_code}"
    
    print("✅ Missing name correctly returns 422 (validation error)")


def test_contact_missing_message():
    """Test POST /api/contact with missing message - should return 422"""
    print("\n=== Testing POST /api/contact (missing message) ===")
    response = requests.post(
        f"{BASE_URL}/contact",
        json={
            "name": "x",
            "email": "a@b.com"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    assert response.status_code == 422, \
        f"Expected 422 for missing message, got {response.status_code}"
    
    print("✅ Missing message correctly returns 422 (validation error)")


def test_contact_repeated_submissions():
    """Test POST /api/contact with repeated submissions - should not crash"""
    print("\n=== Testing POST /api/contact (repeated submissions) ===")
    
    for i in range(3):
        response = requests.post(
            f"{BASE_URL}/contact",
            json={
                "name": f"Repeat User {i}",
                "email": f"repeat{i}@example.com",
                "subject": f"Submission {i}",
                "message": f"This is submission number {i}"
            }
        )
        print(f"Submission {i+1}: Status {response.status_code}")
        
        assert response.status_code == 200, \
            f"Expected 200 for submission {i+1}, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("ok") is True, f"Expected ok:true in submission {i+1}"
    
    print("✅ Repeated submissions work correctly (no crash)")


def main():
    print("=" * 70)
    print("CampionAI Backend Tests")
    print("Testing: Contact Form + PayPal LIVE + Emergent Google OAuth")
    print("Testing error paths, auth-gating, and endpoint wiring")
    print("NO REAL SUBSCRIPTIONS WILL BE CREATED")
    print("=" * 70)
    
    try:
        # ============ PART 1: Contact Form Tests (NEW) ============
        print("\n" + "=" * 70)
        print("PART 1: CONTACT FORM (PUBLIC ENDPOINT) TESTS")
        print("=" * 70)
        
        test_contact_valid_payload()
        test_contact_no_auth()
        test_contact_invalid_email()
        test_contact_missing_name()
        test_contact_missing_message()
        test_contact_repeated_submissions()
        
        # ============ PART 2: No-regression Email/Password Auth ============
        print("\n" + "=" * 70)
        print("PART 2: NO-REGRESSION EMAIL/PASSWORD AUTH TESTS")
        print("=" * 70)
        
        token = test_login()
        test_me_endpoint(token)
        
        # Test registration with new user
        new_email = test_register_new_user()
        test_register_duplicate_email(new_email)
        
        # ============ PART 3: Google Sign-in Tests ============
        print("\n" + "=" * 70)
        print("PART 3: GOOGLE SIGN-IN (EMERGENT OAUTH) TESTS")
        print("=" * 70)
        
        test_google_session_bogus()
        test_google_session_missing_body()
        test_google_session_empty_session_id()
        test_google_session_null_body()
        
        # ============ PART 4: PayPal Integration Tests ============
        print("\n" + "=" * 70)
        print("PART 4: PAYPAL LIVE INTEGRATION TESTS")
        print("=" * 70)
        
        test_plus_status(token)
        test_webhook_invalid_signature()
        test_webhook_malformed_body()
        test_paypal_activate_no_auth()
        test_paypal_activate_bogus_subscription(token)
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        print("\nSUMMARY:")
        print("  ✅ Contact form (public) accepts valid submissions and returns 200 with ok:true")
        print("  ✅ Contact form works without authentication (public endpoint)")
        print("  ✅ Contact form validates email (422 for invalid email)")
        print("  ✅ Contact form validates required fields (422 for missing name/message)")
        print("  ✅ Contact form handles repeated submissions without crashing")
        print("  ✅ Email/password auth (login, register, /me) working correctly")
        print("  ✅ Duplicate email registration correctly returns 400")
        print("  ✅ Google sign-in endpoint correctly rejects bogus/invalid session_ids (401)")
        print("  ✅ Google sign-in endpoint handles missing/empty body without crashing")
        print("  ✅ PayPal webhook signature verification working")
        print("  ✅ PayPal activate endpoint auth-gated and server-side verification working")
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
