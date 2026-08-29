#!/usr/bin/env python3
"""
Backend API Testing for CampionAI - Supporters Wall + Donation Receipt
Tests the new supporters wall endpoint and donation flow with graceful degradation
"""

import requests
import json
import sys
import uuid

# Backend URL from frontend/.env
BASE_URL = "https://5bf17d89-e033-4713-a907-ef5b1c33b4af.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@campionai.com"
ADMIN_PASSWORD = "Admin@12345"

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def log_test(name):
    print(f"\n{BLUE}[TEST]{RESET} {name}")

def log_pass(msg):
    print(f"  {GREEN}✓{RESET} {msg}")

def log_fail(msg):
    print(f"  {RED}✗{RESET} {msg}")

def log_info(msg):
    print(f"  {YELLOW}ℹ{RESET} {msg}")

def test_donors_top_public():
    """Test GET /api/donors/top is PUBLIC and returns correct empty-state object shape"""
    log_test("GET /api/donors/top - PUBLIC endpoint with correct object shape")
    
    url = f"{BASE_URL}/donors/top"
    
    try:
        # Test WITHOUT Authorization header (public endpoint)
        resp = requests.get(url, timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Expected HTTP 200, got {resp.status_code}")
            log_info(f"Response: {resp.text}")
            return False
        
        log_pass(f"HTTP 200 OK (public endpoint works without auth)")
        
        data = resp.json()
        log_info(f"Response: {json.dumps(data, indent=2)}")
        
        # Verify it's an OBJECT (not an array)
        if not isinstance(data, dict):
            log_fail(f"Expected response to be an object/dict, got {type(data).__name__}")
            return False
        
        log_pass("Response is an object (not an array)")
        
        # Verify required fields exist
        required_fields = ["supporters", "total_raised", "gift_count", "supporter_count"]
        for field in required_fields:
            if field not in data:
                log_fail(f"Missing required field: {field}")
                return False
        
        log_pass(f"All required fields present: {', '.join(required_fields)}")
        
        # Verify supporters is a list
        if not isinstance(data["supporters"], list):
            log_fail(f"Expected 'supporters' to be a list, got {type(data['supporters']).__name__}")
            return False
        
        log_pass(f"'supporters' is a list (length: {len(data['supporters'])})")
        
        # Verify numeric fields are numbers and 0 in empty state
        numeric_fields = ["total_raised", "gift_count", "supporter_count"]
        for field in numeric_fields:
            value = data[field]
            if not isinstance(value, (int, float)):
                log_fail(f"Expected '{field}' to be numeric, got {type(value).__name__}: {value}")
                return False
            log_pass(f"'{field}' is numeric: {value}")
        
        # If supporters list is not empty, verify structure
        if data["supporters"]:
            log_info(f"Found {len(data['supporters'])} supporters")
            sample = data["supporters"][0]
            expected_supporter_fields = ["name", "avatar", "total", "count", "tier", "tier_color"]
            for field in expected_supporter_fields:
                if field not in sample:
                    log_fail(f"Supporter missing field: {field}")
                    return False
            log_pass(f"Supporter objects have correct structure: {', '.join(expected_supporter_fields)}")
        else:
            log_info("Empty supporters list (expected in initial state)")
        
        log_pass("✅ GET /api/donors/top VERIFIED - PUBLIC, correct object shape, all fields present")
        return True
        
    except requests.exceptions.RequestException as e:
        log_fail(f"Request failed: {e}")
        return False
    except json.JSONDecodeError as e:
        log_fail(f"Invalid JSON response: {e}")
        return False
    except Exception as e:
        log_fail(f"Unexpected error: {e}")
        return False


def test_donation_order_no_paypal():
    """Test POST /api/donations/order returns clean 400 when PayPal not configured"""
    log_test("POST /api/donations/order - Graceful degradation (no PayPal keys)")
    
    # First, login to get token
    login_url = f"{BASE_URL}/auth/login"
    login_payload = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    try:
        login_resp = requests.post(login_url, json=login_payload, timeout=10)
        if login_resp.status_code != 200:
            log_fail(f"Login failed with status {login_resp.status_code}")
            return False
        
        token = login_resp.json().get("token")
        if not token:
            log_fail("No token in login response")
            return False
        
        log_pass("Admin login successful")
        
        # Now test donation order
        url = f"{BASE_URL}/donations/order"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {"amount": 10}
        
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if resp.status_code == 500:
            log_fail(f"Got HTTP 500 (should be 400 for graceful degradation)")
            log_info(f"Response: {resp.text}")
            return False
        
        if resp.status_code != 400:
            log_fail(f"Expected HTTP 400, got {resp.status_code}")
            log_info(f"Response: {resp.text}")
            return False
        
        log_pass(f"HTTP 400 (NOT 500 - graceful degradation confirmed)")
        
        data = resp.json()
        detail = data.get("detail", "")
        
        if "PayPal is not configured" not in detail:
            log_fail(f"Expected detail 'PayPal is not configured', got: {detail}")
            return False
        
        log_pass(f"Correct error message: '{detail}'")
        log_pass("✅ POST /api/donations/order VERIFIED - Clean 400 with graceful error message")
        return True
        
    except requests.exceptions.RequestException as e:
        log_fail(f"Request failed: {e}")
        return False
    except Exception as e:
        log_fail(f"Unexpected error: {e}")
        return False


def test_donation_capture_not_found():
    """Test POST /api/donations/capture/{fake-id} returns clean 404"""
    log_test("POST /api/donations/capture/{fake-id} - Order not found")
    
    # First, login to get token
    login_url = f"{BASE_URL}/auth/login"
    login_payload = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    try:
        login_resp = requests.post(login_url, json=login_payload, timeout=10)
        if login_resp.status_code != 200:
            log_fail(f"Login failed with status {login_resp.status_code}")
            return False
        
        token = login_resp.json().get("token")
        if not token:
            log_fail("No token in login response")
            return False
        
        log_pass("Admin login successful")
        
        # Test with a fake order ID
        fake_order_id = f"FAKE-ORDER-{uuid.uuid4()}"
        url = f"{BASE_URL}/donations/capture/{fake_order_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        resp = requests.post(url, headers=headers, timeout=10)
        
        if resp.status_code == 500:
            log_fail(f"Got HTTP 500 (should be 404 for not found)")
            log_info(f"Response: {resp.text}")
            return False
        
        if resp.status_code != 404:
            log_fail(f"Expected HTTP 404, got {resp.status_code}")
            log_info(f"Response: {resp.text}")
            return False
        
        log_pass(f"HTTP 404 (NOT 500 - graceful error handling)")
        
        data = resp.json()
        detail = data.get("detail", "")
        
        if "Order not found" not in detail:
            log_fail(f"Expected detail 'Order not found', got: {detail}")
            return False
        
        log_pass(f"Correct error message: '{detail}'")
        log_pass("✅ POST /api/donations/capture VERIFIED - Clean 404 for non-existent order")
        return True
        
    except requests.exceptions.RequestException as e:
        log_fail(f"Request failed: {e}")
        return False
    except Exception as e:
        log_fail(f"Unexpected error: {e}")
        return False


def test_no_regressions():
    """Test that existing endpoints still work correctly"""
    log_test("No-regression checks - Existing endpoints")
    
    all_passed = True
    
    # Test 1: GET /api/pricing
    try:
        url = f"{BASE_URL}/pricing"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            log_pass("GET /api/pricing returns 200")
        else:
            log_fail(f"GET /api/pricing returned {resp.status_code}")
            all_passed = False
    except Exception as e:
        log_fail(f"GET /api/pricing failed: {e}")
        all_passed = False
    
    # Test 2: Admin login
    try:
        url = f"{BASE_URL}/auth/login"
        payload = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            token = resp.json().get("token")
            if token:
                log_pass("Admin login returns 200 with token")
                
                # Test 3: GET /api/auth/me
                try:
                    me_url = f"{BASE_URL}/auth/me"
                    headers = {"Authorization": f"Bearer {token}"}
                    me_resp = requests.get(me_url, headers=headers, timeout=10)
                    if me_resp.status_code == 200:
                        log_pass("GET /api/auth/me returns 200")
                    else:
                        log_fail(f"GET /api/auth/me returned {me_resp.status_code}")
                        all_passed = False
                except Exception as e:
                    log_fail(f"GET /api/auth/me failed: {e}")
                    all_passed = False
            else:
                log_fail("Admin login missing token")
                all_passed = False
        else:
            log_fail(f"Admin login returned {resp.status_code}")
            all_passed = False
    except Exception as e:
        log_fail(f"Admin login failed: {e}")
        all_passed = False
    
    # Test 4: Register new user
    try:
        url = f"{BASE_URL}/auth/register"
        test_email = f"test-{uuid.uuid4()}@example.com"
        payload = {"email": test_email, "password": "TestPass123!"}
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            new_token = resp.json().get("token")
            if new_token:
                log_pass("Register new user returns 200 with token")
                
                # Test 5: Login with new user
                try:
                    login_url = f"{BASE_URL}/auth/login"
                    login_payload = {"email": test_email, "password": "TestPass123!"}
                    login_resp = requests.post(login_url, json=login_payload, timeout=10)
                    if login_resp.status_code == 200:
                        log_pass("Login with new user returns 200")
                        
                        # Test 6: GET /api/auth/me with new user
                        try:
                            me_url = f"{BASE_URL}/auth/me"
                            headers = {"Authorization": f"Bearer {new_token}"}
                            me_resp = requests.get(me_url, headers=headers, timeout=10)
                            if me_resp.status_code == 200:
                                log_pass("GET /api/auth/me with new user returns 200")
                            else:
                                log_fail(f"GET /api/auth/me with new user returned {me_resp.status_code}")
                                all_passed = False
                        except Exception as e:
                            log_fail(f"GET /api/auth/me with new user failed: {e}")
                            all_passed = False
                    else:
                        log_fail(f"Login with new user returned {login_resp.status_code}")
                        all_passed = False
                except Exception as e:
                    log_fail(f"Login with new user failed: {e}")
                    all_passed = False
            else:
                log_fail("Register missing token")
                all_passed = False
        else:
            log_fail(f"Register new user returned {resp.status_code}")
            all_passed = False
    except Exception as e:
        log_fail(f"Register new user failed: {e}")
        all_passed = False
    
    if all_passed:
        log_pass("✅ NO-REGRESSION CHECKS PASSED - All existing endpoints working")
    else:
        log_fail("❌ Some regression checks failed")
    
    return all_passed


def main():
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CampionAI Backend Testing - Supporters Wall + Donation Receipt{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    print(f"Backend URL: {BASE_URL}")
    print(f"Admin: {ADMIN_EMAIL}")
    
    results = []
    
    # Run all tests
    results.append(("GET /api/donors/top (PUBLIC)", test_donors_top_public()))
    results.append(("POST /api/donations/order (no PayPal)", test_donation_order_no_paypal()))
    results.append(("POST /api/donations/capture (not found)", test_donation_capture_not_found()))
    results.append(("No-regression checks", test_no_regressions()))
    
    # Summary
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST SUMMARY{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{GREEN}✓ PASS{RESET}" if result else f"{RED}✗ FAIL{RESET}"
        print(f"{status} - {name}")
    
    print(f"\n{BLUE}Total: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}{'='*70}{RESET}")
        print(f"{GREEN}✅ ALL TESTS PASSED{RESET}")
        print(f"{GREEN}{'='*70}{RESET}")
        return 0
    else:
        print(f"\n{RED}{'='*70}{RESET}")
        print(f"{RED}❌ SOME TESTS FAILED{RESET}")
        print(f"{RED}{'='*70}{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
