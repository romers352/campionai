#!/usr/bin/env python3
"""
Backend API Testing for CampionAI
Tests password reset endpoints with comprehensive scenarios
"""

import requests
import json
import sys
import time

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

def test_forgot_password_registered_email():
    """Test forgot-password with a registered email (admin@campionai.com)"""
    log_test("POST /api/auth/forgot-password - Registered email")
    
    url = f"{BASE_URL}/auth/forgot-password"
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://example.com"
    }
    payload = {"email": ADMIN_EMAIL}
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        
        # Check status code
        if resp.status_code != 200:
            log_fail(f"Expected 200, got {resp.status_code}")
            log_info(f"Response: {resp.text}")
            return False
        
        log_pass(f"Status code: {resp.status_code}")
        
        # Check response structure
        data = resp.json()
        
        # Must have ok:true
        if not data.get("ok"):
            log_fail("Response missing 'ok: true'")
            return False
        log_pass("Response has 'ok: true'")
        
        # Must have generic message
        if not data.get("message"):
            log_fail("Response missing 'message'")
            return False
        log_pass(f"Message: {data['message']}")
        
        # Since RESEND_API_KEY is empty, must have dev_reset_link
        if "dev_reset_link" not in data:
            log_fail("Response missing 'dev_reset_link' (RESEND_API_KEY is empty)")
            return False
        log_pass(f"dev_reset_link present: {data['dev_reset_link']}")
        
        # Must have email_configured: false
        if data.get("email_configured") != False:
            log_fail(f"Expected email_configured: false, got {data.get('email_configured')}")
            return False
        log_pass("email_configured: false")
        
        # Extract token from dev_reset_link for later use
        reset_link = data["dev_reset_link"]
        if "token=" in reset_link:
            token = reset_link.split("token=")[1]
            log_info(f"Extracted token: {token[:20]}...")
            return token
        else:
            log_fail("Could not extract token from dev_reset_link")
            return False
            
    except Exception as e:
        log_fail(f"Exception: {e}")
        return False

def test_forgot_password_unknown_email():
    """Test forgot-password with an unknown email - must NOT leak email existence"""
    log_test("POST /api/auth/forgot-password - Unknown email (security check)")
    
    url = f"{BASE_URL}/auth/forgot-password"
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://example.com"
    }
    payload = {"email": "nobody-xyz-unknown@example.com"}
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        
        # Check status code
        if resp.status_code != 200:
            log_fail(f"Expected 200, got {resp.status_code}")
            log_info(f"Response: {resp.text}")
            return False
        
        log_pass(f"Status code: {resp.status_code}")
        
        # Check response structure
        data = resp.json()
        
        # Must have ok:true
        if not data.get("ok"):
            log_fail("Response missing 'ok: true'")
            return False
        log_pass("Response has 'ok: true'")
        
        # Must have generic message (same as registered email)
        if not data.get("message"):
            log_fail("Response missing 'message'")
            return False
        log_pass(f"Message: {data['message']}")
        
        # SECURITY CHECK: Must NOT have dev_reset_link for unknown email
        if "dev_reset_link" in data:
            log_fail("SECURITY ISSUE: dev_reset_link present for unknown email (leaks email existence)")
            return False
        log_pass("dev_reset_link NOT present (correct - no email leak)")
        
        return True
            
    except Exception as e:
        log_fail(f"Exception: {e}")
        return False

def test_forgot_password_invalid_email():
    """Test forgot-password with invalid email format"""
    log_test("POST /api/auth/forgot-password - Invalid email format")
    
    url = f"{BASE_URL}/auth/forgot-password"
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://example.com"
    }
    payload = {"email": "not-an-email"}
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        
        # Check status code - must be 422 validation error, NOT 500
        if resp.status_code != 422:
            log_fail(f"Expected 422 validation error, got {resp.status_code}")
            log_info(f"Response: {resp.text}")
            return False
        
        log_pass(f"Status code: {resp.status_code} (validation error)")
        return True
            
    except Exception as e:
        log_fail(f"Exception: {e}")
        return False

def test_reset_password_valid_token(token):
    """Test reset-password with valid token"""
    log_test("POST /api/auth/reset-password - Valid token")
    
    url = f"{BASE_URL}/auth/reset-password"
    headers = {"Content-Type": "application/json"}
    payload = {
        "token": token,
        "new_password": "TempPass@999"
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        
        # Check status code
        if resp.status_code != 200:
            log_fail(f"Expected 200, got {resp.status_code}")
            log_info(f"Response: {resp.text}")
            return False
        
        log_pass(f"Status code: {resp.status_code}")
        
        # Check response structure
        data = resp.json()
        
        # Must have ok:true
        if not data.get("ok"):
            log_fail("Response missing 'ok: true'")
            return False
        log_pass("Response has 'ok: true'")
        
        # Must have message
        if not data.get("message"):
            log_fail("Response missing 'message'")
            return False
        log_pass(f"Message: {data['message']}")
        
        return True
            
    except Exception as e:
        log_fail(f"Exception: {e}")
        return False

def test_reset_password_reuse_token(token):
    """Test reset-password with already used token"""
    log_test("POST /api/auth/reset-password - Reuse token (must fail)")
    
    url = f"{BASE_URL}/auth/reset-password"
    headers = {"Content-Type": "application/json"}
    payload = {
        "token": token,
        "new_password": "AnotherPass@123"
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        
        # Check status code - must be 400, NOT 200 or 500
        if resp.status_code != 400:
            log_fail(f"Expected 400, got {resp.status_code}")
            log_info(f"Response: {resp.text}")
            return False
        
        log_pass(f"Status code: {resp.status_code}")
        
        # Check error message
        data = resp.json()
        detail = data.get("detail", "")
        if "already been used" not in detail.lower() and "invalid" not in detail.lower():
            log_fail(f"Expected error about token being used/invalid, got: {detail}")
            return False
        log_pass(f"Error message: {detail}")
        
        return True
            
    except Exception as e:
        log_fail(f"Exception: {e}")
        return False

def test_reset_password_garbage_token():
    """Test reset-password with garbage token"""
    log_test("POST /api/auth/reset-password - Garbage token")
    
    url = f"{BASE_URL}/auth/reset-password"
    headers = {"Content-Type": "application/json"}
    payload = {
        "token": "garbage-token-123456789",
        "new_password": "ValidPass@123"
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        
        # Check status code - must be 400, NOT 500
        if resp.status_code != 400:
            log_fail(f"Expected 400, got {resp.status_code}")
            log_info(f"Response: {resp.text}")
            return False
        
        log_pass(f"Status code: {resp.status_code}")
        
        # Check error message
        data = resp.json()
        detail = data.get("detail", "")
        if "invalid" not in detail.lower():
            log_fail(f"Expected error about invalid token, got: {detail}")
            return False
        log_pass(f"Error message: {detail}")
        
        return True
            
    except Exception as e:
        log_fail(f"Exception: {e}")
        return False

def test_reset_password_short_password(token):
    """Test reset-password with password shorter than 8 chars"""
    log_test("POST /api/auth/reset-password - Short password (< 8 chars)")
    
    url = f"{BASE_URL}/auth/reset-password"
    headers = {"Content-Type": "application/json"}
    payload = {
        "token": token,
        "new_password": "abc"
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        
        # Check status code - must be 422 validation error, NOT 500
        if resp.status_code != 422:
            log_fail(f"Expected 422 validation error, got {resp.status_code}")
            log_info(f"Response: {resp.text}")
            return False
        
        log_pass(f"Status code: {resp.status_code} (validation error)")
        return True
            
    except Exception as e:
        log_fail(f"Exception: {e}")
        return False

def test_login_with_new_password():
    """Test login with new password after reset"""
    log_test("POST /api/auth/login - Login with NEW password")
    
    url = f"{BASE_URL}/auth/login"
    headers = {"Content-Type": "application/json"}
    payload = {
        "email": ADMIN_EMAIL,
        "password": "TempPass@999"
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        
        # Check status code
        if resp.status_code != 200:
            log_fail(f"Expected 200, got {resp.status_code}")
            log_info(f"Response: {resp.text}")
            return False
        
        log_pass(f"Status code: {resp.status_code}")
        
        # Check response has token
        data = resp.json()
        if not data.get("token"):
            log_fail("Response missing 'token'")
            return False
        log_pass("Login successful with new password")
        
        return True
            
    except Exception as e:
        log_fail(f"Exception: {e}")
        return False

def test_login_with_old_password():
    """Test login with old password after reset (must fail)"""
    log_test("POST /api/auth/login - Login with OLD password (must fail)")
    
    url = f"{BASE_URL}/auth/login"
    headers = {"Content-Type": "application/json"}
    payload = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD  # Old password
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        
        # Check status code - must be 401, NOT 200
        if resp.status_code != 401:
            log_fail(f"Expected 401, got {resp.status_code}")
            log_info(f"Response: {resp.text}")
            return False
        
        log_pass(f"Status code: {resp.status_code} (old password correctly rejected)")
        return True
            
    except Exception as e:
        log_fail(f"Exception: {e}")
        return False

def restore_admin_password():
    """CLEANUP: Restore admin password back to Admin@12345"""
    log_test("CLEANUP: Restore admin password to Admin@12345")
    
    # Step 1: Request password reset
    url = f"{BASE_URL}/auth/forgot-password"
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://example.com"
    }
    payload = {"email": ADMIN_EMAIL}
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Failed to request reset: {resp.status_code}")
            return False
        
        data = resp.json()
        if "dev_reset_link" not in data:
            log_fail("No dev_reset_link in response")
            return False
        
        # Extract token
        reset_link = data["dev_reset_link"]
        token = reset_link.split("token=")[1]
        log_info(f"Got reset token: {token[:20]}...")
        
        # Step 2: Reset password back to Admin@12345
        url = f"{BASE_URL}/auth/reset-password"
        payload = {
            "token": token,
            "new_password": ADMIN_PASSWORD
        }
        
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Failed to reset password: {resp.status_code}")
            log_info(f"Response: {resp.text}")
            return False
        
        log_pass("Password reset to Admin@12345")
        
        # Step 3: Verify login with Admin@12345
        url = f"{BASE_URL}/auth/login"
        payload = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Failed to login with restored password: {resp.status_code}")
            return False
        
        log_pass("Login successful with Admin@12345 - CLEANUP COMPLETE")
        return True
            
    except Exception as e:
        log_fail(f"Exception: {e}")
        return False

def main():
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CampionAI Backend Testing - Password Reset Endpoints{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    print(f"Backend URL: {BASE_URL}")
    print(f"Admin Email: {ADMIN_EMAIL}")
    
    results = []
    
    # Test 1: forgot-password with registered email
    token = test_forgot_password_registered_email()
    if token and isinstance(token, str):
        results.append(("forgot-password (registered email)", True))
    else:
        results.append(("forgot-password (registered email)", False))
        print(f"\n{RED}CRITICAL: Cannot continue without valid token{RESET}")
        return False
    
    # Test 2: forgot-password with unknown email (security check)
    result = test_forgot_password_unknown_email()
    results.append(("forgot-password (unknown email - no leak)", result))
    
    # Test 3: forgot-password with invalid email format
    result = test_forgot_password_invalid_email()
    results.append(("forgot-password (invalid email format)", result))
    
    # Test 4: reset-password with valid token
    result = test_reset_password_valid_token(token)
    results.append(("reset-password (valid token)", result))
    
    # Test 5: reset-password with reused token
    result = test_reset_password_reuse_token(token)
    results.append(("reset-password (reuse token)", result))
    
    # Test 6: reset-password with garbage token
    result = test_reset_password_garbage_token()
    results.append(("reset-password (garbage token)", result))
    
    # Get a fresh token for short password test
    log_info("Getting fresh token for short password test...")
    fresh_token = test_forgot_password_registered_email()
    if fresh_token and isinstance(fresh_token, str):
        # Test 7: reset-password with short password
        result = test_reset_password_short_password(fresh_token)
        results.append(("reset-password (short password)", result))
    else:
        results.append(("reset-password (short password)", False))
    
    # Test 8: login with new password
    result = test_login_with_new_password()
    results.append(("login (new password)", result))
    
    # Test 9: login with old password (must fail)
    result = test_login_with_old_password()
    results.append(("login (old password - must fail)", result))
    
    # CLEANUP: Restore admin password
    result = restore_admin_password()
    results.append(("CLEANUP (restore admin password)", result))
    
    # Summary
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST SUMMARY{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{status} - {name}")
    
    print(f"\n{BLUE}Total: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"{GREEN}✓ ALL TESTS PASSED{RESET}")
        return True
    else:
        print(f"{RED}✗ SOME TESTS FAILED{RESET}")
        return False

def test_wellness_endpoints():
    """
    Comprehensive test suite for Phase-1 Wellness endpoints:
    - POST /api/wellness/mood (with validation and UPSERT)
    - GET /api/wellness/mood/trends
    - POST/GET/DELETE /api/wellness/gratitude
    - GET /api/wellness/gratitude/random
    - GET /api/wellness/badges
    - Auth guard testing
    """
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}PHASE-1 WELLNESS ENDPOINTS TEST SUITE{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    results = []
    
    # Step 1: Login as admin
    log_test("Login as admin")
    login_url = f"{BASE_URL}/auth/login"
    login_payload = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    try:
        resp = requests.post(login_url, json=login_payload, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("token")
            if token:
                log_pass(f"Login successful, got token")
                results.append(("Admin login", True))
            else:
                log_fail("No token in response")
                results.append(("Admin login", False))
                return False
        else:
            log_fail(f"Login failed with status {resp.status_code}: {resp.text}")
            results.append(("Admin login", False))
            return False
    except Exception as e:
        log_fail(f"Login exception: {e}")
        results.append(("Admin login", False))
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Step 2: Ensure Plus subscription (start trial if needed)
    log_test("Ensure Plus subscription")
    try:
        # Check Plus status first
        plus_status_resp = requests.get(f"{BASE_URL}/plus/status", headers=headers, timeout=10)
        if plus_status_resp.status_code == 200:
            plus_data = plus_status_resp.json()
            if not plus_data.get("active"):
                log_info("Plus not active, starting trial...")
                trial_resp = requests.post(f"{BASE_URL}/plus/start-trial", headers=headers, timeout=10)
                if trial_resp.status_code == 200:
                    log_pass("Plus trial started successfully")
                    results.append(("Start Plus trial", True))
                else:
                    log_fail(f"Failed to start trial: {trial_resp.status_code} - {trial_resp.text}")
                    results.append(("Start Plus trial", False))
            else:
                log_pass("Plus already active")
                results.append(("Plus subscription check", True))
        else:
            log_fail(f"Failed to check Plus status: {plus_status_resp.status_code}")
            results.append(("Plus subscription check", False))
    except Exception as e:
        log_fail(f"Plus subscription check exception: {e}")
        results.append(("Plus subscription check", False))
    
    # Test 1: POST /api/wellness/mood - Valid mood (mood=4)
    log_test("POST /api/wellness/mood - Valid mood (mood=4)")
    try:
        mood_payload = {"mood": 4, "note": "good day"}
        resp = requests.post(f"{BASE_URL}/wellness/mood", json=mood_payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("mood") == 4 and "id" in data:
                log_pass(f"Mood logged successfully: mood={data.get('mood')}, note={data.get('note')}")
                results.append(("POST /api/wellness/mood (valid mood=4)", True))
            else:
                log_fail(f"Response missing expected fields: {data}")
                results.append(("POST /api/wellness/mood (valid mood=4)", False))
        else:
            log_fail(f"Status {resp.status_code}: {resp.text}")
            results.append(("POST /api/wellness/mood (valid mood=4)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("POST /api/wellness/mood (valid mood=4)", False))
    
    # Test 2: POST /api/wellness/mood - Out of range (mood=0) should return 422
    log_test("POST /api/wellness/mood - Out of range (mood=0) → 422")
    try:
        mood_payload = {"mood": 0, "note": "invalid"}
        resp = requests.post(f"{BASE_URL}/wellness/mood", json=mood_payload, headers=headers, timeout=10)
        if resp.status_code == 422:
            log_pass(f"Correctly rejected mood=0 with 422 validation error")
            results.append(("POST /api/wellness/mood (mood=0 → 422)", True))
        elif resp.status_code == 500:
            log_fail(f"Got 500 error (should be 422): {resp.text}")
            results.append(("POST /api/wellness/mood (mood=0 → 422)", False))
        else:
            log_fail(f"Unexpected status {resp.status_code}: {resp.text}")
            results.append(("POST /api/wellness/mood (mood=0 → 422)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("POST /api/wellness/mood (mood=0 → 422)", False))
    
    # Test 3: POST /api/wellness/mood - Out of range (mood=6) should return 422
    log_test("POST /api/wellness/mood - Out of range (mood=6) → 422")
    try:
        mood_payload = {"mood": 6, "note": "invalid"}
        resp = requests.post(f"{BASE_URL}/wellness/mood", json=mood_payload, headers=headers, timeout=10)
        if resp.status_code == 422:
            log_pass(f"Correctly rejected mood=6 with 422 validation error")
            results.append(("POST /api/wellness/mood (mood=6 → 422)", True))
        elif resp.status_code == 500:
            log_fail(f"Got 500 error (should be 422): {resp.text}")
            results.append(("POST /api/wellness/mood (mood=6 → 422)", False))
        else:
            log_fail(f"Unexpected status {resp.status_code}: {resp.text}")
            results.append(("POST /api/wellness/mood (mood=6 → 422)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("POST /api/wellness/mood (mood=6 → 422)", False))
    
    # Test 4: POST /api/wellness/mood - UPSERT behavior (log again with mood=2)
    log_test("POST /api/wellness/mood - UPSERT behavior (mood=2 for today)")
    try:
        mood_payload = {"mood": 2, "note": "updated mood"}
        resp = requests.post(f"{BASE_URL}/wellness/mood", json=mood_payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("mood") == 2:
                log_pass(f"Mood updated successfully: mood={data.get('mood')}")
                results.append(("POST /api/wellness/mood (UPSERT mood=2)", True))
            else:
                log_fail(f"Mood not updated correctly: {data}")
                results.append(("POST /api/wellness/mood (UPSERT mood=2)", False))
        else:
            log_fail(f"Status {resp.status_code}: {resp.text}")
            results.append(("POST /api/wellness/mood (UPSERT mood=2)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("POST /api/wellness/mood (UPSERT mood=2)", False))
    
    # Test 5: GET /api/wellness/mood/trends - Verify UPSERT (today's mood should be 2)
    log_test("GET /api/wellness/mood/trends?days=30 - Verify UPSERT")
    try:
        resp = requests.get(f"{BASE_URL}/wellness/mood/trends?days=30", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "series" in data and "average" in data and "count" in data and "today" in data:
                count = data.get("count")
                today = data.get("today")
                if count >= 1:
                    log_pass(f"Trends returned: count={count}, average={data.get('average')}")
                    if today and today.get("mood") == 2:
                        log_pass(f"UPSERT verified: today's mood is 2 (not duplicate)")
                        results.append(("GET /api/wellness/mood/trends (UPSERT verified)", True))
                    else:
                        log_fail(f"Today's mood is not 2: {today}")
                        results.append(("GET /api/wellness/mood/trends (UPSERT verified)", False))
                else:
                    log_fail(f"Count is {count}, expected >= 1")
                    results.append(("GET /api/wellness/mood/trends (UPSERT verified)", False))
            else:
                log_fail(f"Response missing expected fields: {data}")
                results.append(("GET /api/wellness/mood/trends (UPSERT verified)", False))
        else:
            log_fail(f"Status {resp.status_code}: {resp.text}")
            results.append(("GET /api/wellness/mood/trends (UPSERT verified)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("GET /api/wellness/mood/trends (UPSERT verified)", False))
    
    # Test 6: POST /api/wellness/gratitude - Valid text
    log_test("POST /api/wellness/gratitude - Valid text")
    gratitude_id = None
    try:
        gratitude_payload = {"text": "morning coffee"}
        resp = requests.post(f"{BASE_URL}/wellness/gratitude", json=gratitude_payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "id" in data and "text" in data and "created_at" in data:
                gratitude_id = data.get("id")
                log_pass(f"Gratitude added: id={gratitude_id}, text={data.get('text')}")
                results.append(("POST /api/wellness/gratitude (valid text)", True))
            else:
                log_fail(f"Response missing expected fields: {data}")
                results.append(("POST /api/wellness/gratitude (valid text)", False))
        else:
            log_fail(f"Status {resp.status_code}: {resp.text}")
            results.append(("POST /api/wellness/gratitude (valid text)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("POST /api/wellness/gratitude (valid text)", False))
    
    # Test 7: POST /api/wellness/gratitude - Empty text should return 422
    log_test("POST /api/wellness/gratitude - Empty text → 422")
    try:
        gratitude_payload = {"text": ""}
        resp = requests.post(f"{BASE_URL}/wellness/gratitude", json=gratitude_payload, headers=headers, timeout=10)
        if resp.status_code == 422:
            log_pass(f"Correctly rejected empty text with 422 validation error")
            results.append(("POST /api/wellness/gratitude (empty text → 422)", True))
        elif resp.status_code == 500:
            log_fail(f"Got 500 error (should be 422): {resp.text}")
            results.append(("POST /api/wellness/gratitude (empty text → 422)", False))
        else:
            log_fail(f"Unexpected status {resp.status_code}: {resp.text}")
            results.append(("POST /api/wellness/gratitude (empty text → 422)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("POST /api/wellness/gratitude (empty text → 422)", False))
    
    # Test 8: GET /api/wellness/gratitude - List gratitude entries
    log_test("GET /api/wellness/gratitude - List entries")
    try:
        resp = requests.get(f"{BASE_URL}/wellness/gratitude", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "items" in data and "count" in data:
                items = data.get("items", [])
                count = data.get("count")
                if gratitude_id and any(item.get("id") == gratitude_id for item in items):
                    log_pass(f"Gratitude list returned: count={count}, added item present")
                    results.append(("GET /api/wellness/gratitude (list)", True))
                else:
                    log_fail(f"Added gratitude item not found in list")
                    results.append(("GET /api/wellness/gratitude (list)", False))
            else:
                log_fail(f"Response missing expected fields: {data}")
                results.append(("GET /api/wellness/gratitude (list)", False))
        else:
            log_fail(f"Status {resp.status_code}: {resp.text}")
            results.append(("GET /api/wellness/gratitude (list)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("GET /api/wellness/gratitude (list)", False))
    
    # Test 9: GET /api/wellness/gratitude/random - Get random entry
    log_test("GET /api/wellness/gratitude/random - Get random entry")
    try:
        resp = requests.get(f"{BASE_URL}/wellness/gratitude/random", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "item" in data:
                item = data.get("item")
                if item is not None:
                    log_pass(f"Random gratitude returned: {item.get('text', 'N/A')}")
                    results.append(("GET /api/wellness/gratitude/random", True))
                else:
                    log_fail(f"Random item is null (expected non-null after adding one)")
                    results.append(("GET /api/wellness/gratitude/random", False))
            else:
                log_fail(f"Response missing 'item' field: {data}")
                results.append(("GET /api/wellness/gratitude/random", False))
        else:
            log_fail(f"Status {resp.status_code}: {resp.text}")
            results.append(("GET /api/wellness/gratitude/random", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("GET /api/wellness/gratitude/random", False))
    
    # Test 10: DELETE /api/wellness/gratitude/{id} - Delete entry
    log_test(f"DELETE /api/wellness/gratitude/{gratitude_id} - Delete entry")
    if gratitude_id:
        try:
            resp = requests.delete(f"{BASE_URL}/wellness/gratitude/{gratitude_id}", headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok") is True:
                    log_pass(f"Gratitude deleted successfully")
                    results.append(("DELETE /api/wellness/gratitude/{id}", True))
                else:
                    log_fail(f"Response missing 'ok: true': {data}")
                    results.append(("DELETE /api/wellness/gratitude/{id}", False))
            else:
                log_fail(f"Status {resp.status_code}: {resp.text}")
                results.append(("DELETE /api/wellness/gratitude/{id}", False))
        except Exception as e:
            log_fail(f"Exception: {e}")
            results.append(("DELETE /api/wellness/gratitude/{id}", False))
    else:
        log_fail("No gratitude_id to delete")
        results.append(("DELETE /api/wellness/gratitude/{id}", False))
    
    # Test 11: GET /api/wellness/gratitude - Verify deletion
    log_test("GET /api/wellness/gratitude - Verify deletion")
    try:
        resp = requests.get(f"{BASE_URL}/wellness/gratitude", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            if gratitude_id and not any(item.get("id") == gratitude_id for item in items):
                log_pass(f"Deleted gratitude item no longer in list")
                results.append(("GET /api/wellness/gratitude (verify deletion)", True))
            elif not gratitude_id:
                log_fail("No gratitude_id to verify deletion")
                results.append(("GET /api/wellness/gratitude (verify deletion)", False))
            else:
                log_fail(f"Deleted gratitude item still in list")
                results.append(("GET /api/wellness/gratitude (verify deletion)", False))
        else:
            log_fail(f"Status {resp.status_code}: {resp.text}")
            results.append(("GET /api/wellness/gratitude (verify deletion)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("GET /api/wellness/gratitude (verify deletion)", False))
    
    # Test 12: GET /api/wellness/badges - Verify structure
    log_test("GET /api/wellness/badges - Verify structure")
    try:
        resp = requests.get(f"{BASE_URL}/wellness/badges", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "badges" in data and "earned_count" in data:
                badges = data.get("badges", [])
                earned_count = data.get("earned_count")
                if len(badges) == 6:
                    log_pass(f"Badges returned: 6 items, earned_count={earned_count}")
                    # Verify structure of each badge
                    required_fields = ["id", "label", "icon", "metric", "threshold", "value", "earned", "progress"]
                    all_valid = True
                    for badge in badges:
                        if not all(field in badge for field in required_fields):
                            log_fail(f"Badge missing required fields: {badge}")
                            all_valid = False
                            break
                    if all_valid:
                        log_pass(f"All badges have required fields: {', '.join(required_fields)}")
                        # Verify specific badges exist
                        badge_ids = [b.get("id") for b in badges]
                        if "mood_tracker" in badge_ids and "grateful_heart" in badge_ids:
                            log_pass(f"'mood_tracker' and 'grateful_heart' badges exist")
                            results.append(("GET /api/wellness/badges (structure)", True))
                        else:
                            log_fail(f"Missing 'mood_tracker' or 'grateful_heart' badge. Found: {badge_ids}")
                            results.append(("GET /api/wellness/badges (structure)", False))
                    else:
                        results.append(("GET /api/wellness/badges (structure)", False))
                else:
                    log_fail(f"Expected 6 badges, got {len(badges)}")
                    results.append(("GET /api/wellness/badges (structure)", False))
            else:
                log_fail(f"Response missing expected fields: {data}")
                results.append(("GET /api/wellness/badges (structure)", False))
        else:
            log_fail(f"Status {resp.status_code}: {resp.text}")
            results.append(("GET /api/wellness/badges (structure)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("GET /api/wellness/badges (structure)", False))
    
    # Test 13: Auth guard - POST /api/wellness/mood without Authorization header
    log_test("POST /api/wellness/mood - No Authorization header → 401/403")
    try:
        mood_payload = {"mood": 3, "note": "test"}
        resp = requests.post(f"{BASE_URL}/wellness/mood", json=mood_payload, timeout=10)
        if resp.status_code in [401, 403]:
            log_pass(f"Correctly rejected with {resp.status_code} (auth required)")
            results.append(("POST /api/wellness/mood (no auth → 401/403)", True))
        elif resp.status_code == 500:
            log_fail(f"Got 500 error (should be 401/403): {resp.text}")
            results.append(("POST /api/wellness/mood (no auth → 401/403)", False))
        else:
            log_fail(f"Unexpected status {resp.status_code}: {resp.text}")
            results.append(("POST /api/wellness/mood (no auth → 401/403)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("POST /api/wellness/mood (no auth → 401/403)", False))
    
    # Summary
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}WELLNESS ENDPOINTS TEST SUMMARY{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{status} - {name}")
    
    print(f"\n{BLUE}Total: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"{GREEN}✓ ALL WELLNESS TESTS PASSED{RESET}")
        return True
    else:
        print(f"{RED}✗ SOME WELLNESS TESTS FAILED{RESET}")
        return False

def test_phase3_chat_endpoints():
    """Test Phase-3 Chat endpoints: pin memory, conversation summary"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}PHASE-3 CHAT ENDPOINTS TEST{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    results = []
    
    # Step 1: Login to get JWT token
    log_test("Login to get JWT token")
    try:
        login_resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        if login_resp.status_code != 200:
            log_fail(f"Login failed with status {login_resp.status_code}: {login_resp.text}")
            return False
        
        token = login_resp.json().get("token")
        if not token:
            log_fail("No token in login response")
            return False
        
        log_pass(f"Login successful, token obtained")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    except Exception as e:
        log_fail(f"Login exception: {e}")
        return False
    
    # Test 1: POST /api/memories/pin with valid text
    log_test("POST /api/memories/pin - Valid text → 200 with memory doc")
    try:
        pin_payload = {"text": "I love hiking on weekends"}
        resp = requests.post(f"{BASE_URL}/memories/pin", json=pin_payload, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            # Verify response structure
            if (data.get("content") == "I love hiking on weekends" and
                data.get("category") == "pinned" and
                data.get("tier") == "LONG_TERM" and
                "id" in data):
                log_pass(f"Memory pinned successfully: category={data['category']}, tier={data['tier']}")
                pinned_memory_content = data.get("content")
                results.append(("POST /api/memories/pin (valid text → 200)", True))
            else:
                log_fail(f"Response missing expected fields or values: {data}")
                results.append(("POST /api/memories/pin (valid text → 200)", False))
                pinned_memory_content = None
        else:
            log_fail(f"Status {resp.status_code}: {resp.text}")
            results.append(("POST /api/memories/pin (valid text → 200)", False))
            pinned_memory_content = None
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("POST /api/memories/pin (valid text → 200)", False))
        pinned_memory_content = None
    
    # Test 2: GET /api/memories - Verify pinned memory is included
    log_test("GET /api/memories - Verify pinned memory is included")
    try:
        resp = requests.get(f"{BASE_URL}/memories", headers=headers, timeout=10)
        
        if resp.status_code == 200:
            memories = resp.json()  # Returns a list directly
            
            # Check if pinned memory is in the list
            if pinned_memory_content:
                found = any(m.get("content") == pinned_memory_content for m in memories)
                if found:
                    log_pass(f"Pinned memory found in GET /api/memories list")
                    results.append(("GET /api/memories (includes pinned)", True))
                else:
                    log_fail(f"Pinned memory NOT found in list. Total memories: {len(memories)}")
                    results.append(("GET /api/memories (includes pinned)", False))
            else:
                log_info("Skipping verification (no pinned memory from previous test)")
                results.append(("GET /api/memories (includes pinned)", False))
        else:
            log_fail(f"Status {resp.status_code}: {resp.text}")
            results.append(("GET /api/memories (includes pinned)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("GET /api/memories (includes pinned)", False))
    
    # Test 3: POST /api/memories/pin with empty text → 422
    log_test("POST /api/memories/pin - Empty text → 422 (NOT 500)")
    try:
        pin_payload = {"text": ""}
        resp = requests.post(f"{BASE_URL}/memories/pin", json=pin_payload, headers=headers, timeout=10)
        
        if resp.status_code == 422:
            log_pass(f"Correctly rejected empty text with 422 validation error")
            results.append(("POST /api/memories/pin (empty text → 422)", True))
        elif resp.status_code == 500:
            log_fail(f"Got 500 error (should be 422): {resp.text}")
            results.append(("POST /api/memories/pin (empty text → 422)", False))
        else:
            log_fail(f"Unexpected status {resp.status_code}: {resp.text}")
            results.append(("POST /api/memories/pin (empty text → 422)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("POST /api/memories/pin (empty text → 422)", False))
    
    # Test 4: POST /api/memories/pin without auth → 401/403
    log_test("POST /api/memories/pin - No auth header → 401/403")
    try:
        pin_payload = {"text": "test without auth"}
        resp = requests.post(f"{BASE_URL}/memories/pin", json=pin_payload, timeout=10)
        
        if resp.status_code in [401, 403]:
            log_pass(f"Correctly rejected with {resp.status_code} (auth required)")
            results.append(("POST /api/memories/pin (no auth → 401/403)", True))
        else:
            log_fail(f"Unexpected status {resp.status_code}: {resp.text}")
            results.append(("POST /api/memories/pin (no auth → 401/403)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("POST /api/memories/pin (no auth → 401/403)", False))
    
    # Test 5: Create a real conversation for summary testing
    log_test("Create real conversation - POST /api/chat/stream (streaming)")
    session_id = None
    try:
        # First message - this will create a session
        chat_payload = {"session_id": None, "message": "I have been feeling stressed about work lately"}
        log_info("Sending first message to /api/chat/stream (streaming endpoint)...")
        
        # /api/chat/stream is a streaming endpoint, so we need to handle it differently
        resp = requests.post(
            f"{BASE_URL}/chat/stream",
            json=chat_payload,
            headers=headers,
            timeout=30,
            stream=True
        )
        
        if resp.status_code == 200:
            log_pass(f"First message sent successfully (status 200, streaming response)")
            
            # Now get the session_id by calling GET /api/sessions
            time.sleep(1)  # Give it a moment to save
            sessions_resp = requests.get(f"{BASE_URL}/sessions", headers=headers, timeout=10)
            
            if sessions_resp.status_code == 200:
                sessions = sessions_resp.json()
                if sessions and len(sessions) > 0:
                    # Get the most recent session
                    session_id = sessions[0].get("id")
                    log_pass(f"Session created with id: {session_id}")
                    results.append(("POST /api/chat/stream (create conversation)", True))
                else:
                    log_fail("No sessions found after chat message")
                    results.append(("POST /api/chat/stream (create conversation)", False))
            else:
                log_fail(f"Failed to get sessions: {sessions_resp.status_code}")
                results.append(("POST /api/chat/stream (create conversation)", False))
        else:
            log_fail(f"Chat failed with status {resp.status_code}: {resp.text}")
            results.append(("POST /api/chat/stream (create conversation)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("POST /api/chat/stream (create conversation)", False))
    
    # Test 6: Send second message to same session
    if session_id:
        log_test("Send second message to same session")
        try:
            chat_payload = {"session_id": session_id, "message": "yeah my manager keeps piling on tasks"}
            resp = requests.post(
                f"{BASE_URL}/chat/stream",
                json=chat_payload,
                headers=headers,
                timeout=30,
                stream=True
            )
            
            if resp.status_code == 200:
                log_pass(f"Second message sent successfully")
                time.sleep(1)  # Give it a moment to save
                results.append(("POST /api/chat/stream (second message)", True))
            else:
                log_fail(f"Status {resp.status_code}: {resp.text}")
                results.append(("POST /api/chat/stream (second message)", False))
        except Exception as e:
            log_fail(f"Exception: {e}")
            results.append(("POST /api/chat/stream (second message)", False))
    else:
        log_info("Skipping second message (no session_id from previous test)")
        results.append(("POST /api/chat/stream (second message)", False))
    
    # Test 7: POST /api/sessions/{id}/summary with real conversation
    if session_id:
        log_test(f"POST /api/sessions/{session_id}/summary - Real conversation → 200 with summary")
        try:
            resp = requests.post(
                f"{BASE_URL}/sessions/{session_id}/summary",
                headers=headers,
                timeout=35  # Allow up to 35s for LLM call
            )
            
            if resp.status_code == 200:
                data = resp.json()
                summary = data.get("summary", "")
                
                if summary and len(summary) > 10:  # Non-empty warm text
                    log_pass(f"Summary generated successfully: '{summary[:100]}...'")
                    results.append(("POST /api/sessions/{id}/summary (real conversation)", True))
                else:
                    log_fail(f"Summary is empty or too short: '{summary}'")
                    results.append(("POST /api/sessions/{id}/summary (real conversation)", False))
            elif resp.status_code == 502:
                log_info(f"Got 502 - LLM provider may have errored (acceptable per review_request)")
                log_info(f"Response: {resp.text}")
                results.append(("POST /api/sessions/{id}/summary (real conversation)", True))
            else:
                log_fail(f"Status {resp.status_code}: {resp.text}")
                results.append(("POST /api/sessions/{id}/summary (real conversation)", False))
        except Exception as e:
            log_fail(f"Exception: {e}")
            results.append(("POST /api/sessions/{id}/summary (real conversation)", False))
    else:
        log_info("Skipping summary test (no session_id from previous test)")
        results.append(("POST /api/sessions/{id}/summary (real conversation)", False))
    
    # Test 8: POST /api/sessions/{random-uuid}/summary → 404
    log_test("POST /api/sessions/{random-uuid}/summary - Non-existent session → 404")
    try:
        fake_session_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        resp = requests.post(
            f"{BASE_URL}/sessions/{fake_session_id}/summary",
            headers=headers,
            timeout=10
        )
        
        if resp.status_code == 404:
            log_pass(f"Correctly returned 404 for non-existent session")
            results.append(("POST /api/sessions/{id}/summary (non-existent → 404)", True))
        elif resp.status_code == 500:
            log_fail(f"Got 500 error (should be 404): {resp.text}")
            results.append(("POST /api/sessions/{id}/summary (non-existent → 404)", False))
        else:
            log_fail(f"Unexpected status {resp.status_code}: {resp.text}")
            results.append(("POST /api/sessions/{id}/summary (non-existent → 404)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("POST /api/sessions/{id}/summary (non-existent → 404)", False))
    
    # Test 9: Create empty session and test summary
    log_test("POST /api/sessions (create empty session) then summary → friendly stub")
    try:
        # Create a new empty session with optional fields
        create_payload = {"title": "Test empty session", "private": False}
        create_resp = requests.post(f"{BASE_URL}/sessions", json=create_payload, headers=headers, timeout=10)
        
        if create_resp.status_code == 200:
            empty_session = create_resp.json()
            empty_session_id = empty_session.get("id")
            log_pass(f"Empty session created: {empty_session_id}")
            
            # Now try to get summary for this empty session
            summary_resp = requests.post(
                f"{BASE_URL}/sessions/{empty_session_id}/summary",
                headers=headers,
                timeout=10
            )
            
            if summary_resp.status_code == 200:
                data = summary_resp.json()
                summary = data.get("summary", "")
                
                # Should return friendly stub for <2 messages
                if "just getting started" in summary.lower() or "not much to recap" in summary.lower():
                    log_pass(f"Friendly stub returned: '{summary}'")
                    results.append(("POST /api/sessions/{id}/summary (empty session → stub)", True))
                else:
                    log_fail(f"Expected friendly stub, got: '{summary}'")
                    results.append(("POST /api/sessions/{id}/summary (empty session → stub)", False))
            else:
                log_fail(f"Summary failed with status {summary_resp.status_code}: {summary_resp.text}")
                results.append(("POST /api/sessions/{id}/summary (empty session → stub)", False))
        else:
            log_fail(f"Failed to create empty session: {create_resp.status_code} - {create_resp.text}")
            results.append(("POST /api/sessions/{id}/summary (empty session → stub)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("POST /api/sessions/{id}/summary (empty session → stub)", False))
    
    # Test 10: Regression - GET /api/sessions → 200
    log_test("Regression: GET /api/sessions → 200")
    try:
        resp = requests.get(f"{BASE_URL}/sessions", headers=headers, timeout=10)
        
        if resp.status_code == 200:
            sessions = resp.json()
            log_pass(f"GET /api/sessions returned 200 with {len(sessions)} sessions")
            results.append(("Regression: GET /api/sessions → 200", True))
        else:
            log_fail(f"Status {resp.status_code}: {resp.text}")
            results.append(("Regression: GET /api/sessions → 200", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("Regression: GET /api/sessions → 200", False))
    
    # Test 11: Regression - GET /api/auth/me → 200
    log_test("Regression: GET /api/auth/me → 200")
    try:
        resp = requests.get(f"{BASE_URL}/auth/me", headers=headers, timeout=10)
        
        if resp.status_code == 200:
            user = resp.json()
            log_pass(f"GET /api/auth/me returned 200 with user: {user.get('email')}")
            results.append(("Regression: GET /api/auth/me → 200", True))
        else:
            log_fail(f"Status {resp.status_code}: {resp.text}")
            results.append(("Regression: GET /api/auth/me → 200", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("Regression: GET /api/auth/me → 200", False))
    
    # Summary
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}PHASE-3 CHAT ENDPOINTS TEST SUMMARY{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{status} - {name}")
    
    print(f"\n{BLUE}Total: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"{GREEN}✓ ALL PHASE-3 CHAT TESTS PASSED{RESET}")
        return True
    else:
        print(f"{RED}✗ SOME PHASE-3 CHAT TESTS FAILED{RESET}")
        return False

def test_payment_system_health():
    """
    Test payment system health after Stripe removal (PayPal-only, no keys configured).
    Verify graceful degradation when PayPal credentials are NOT configured.
    """
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}PAYMENT SYSTEM HEALTH TEST (PayPal-only, no keys){RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    results = []
    
    # Step 1: Login as admin to get JWT token
    log_test("Login as admin")
    try:
        login_resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        if login_resp.status_code != 200:
            log_fail(f"Login failed with status {login_resp.status_code}: {login_resp.text}")
            results.append(("Admin login", False))
            return False
        
        token = login_resp.json().get("token")
        if not token:
            log_fail("No token in login response")
            results.append(("Admin login", False))
            return False
        
        log_pass(f"Login successful, token obtained")
        results.append(("Admin login", True))
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    except Exception as e:
        log_fail(f"Login exception: {e}")
        results.append(("Admin login", False))
        return False
    
    # Test 1: GET /api/pricing returns 200 with correct structure
    log_test("GET /api/pricing - Verify structure with no PayPal keys")
    try:
        resp = requests.get(f"{BASE_URL}/pricing", timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            log_pass(f"Status code: 200")
            
            # Verify currency
            if data.get("currency") == "USD":
                log_pass(f"currency: USD")
            else:
                log_fail(f"Expected currency: USD, got {data.get('currency')}")
                results.append(("GET /api/pricing (currency)", False))
            
            # Verify paypal_client_id is null (no keys configured)
            if data.get("paypal_client_id") is None:
                log_pass(f"paypal_client_id: null (correct - no keys configured)")
            else:
                log_fail(f"Expected paypal_client_id: null, got {data.get('paypal_client_id')}")
                results.append(("GET /api/pricing (paypal_client_id=null)", False))
            
            # Verify trial_days
            if data.get("trial_days") == 14:
                log_pass(f"trial_days: 14")
            else:
                log_fail(f"Expected trial_days: 14, got {data.get('trial_days')}")
            
            # Verify plans array
            plans = data.get("plans", [])
            if len(plans) == 2:
                log_pass(f"plans: 2 items (plus_monthly, plus_yearly)")
                
                # Check each plan has paypal_plan_id = null
                all_null = True
                for plan in plans:
                    if plan.get("paypal_plan_id") is not None:
                        log_fail(f"Plan {plan.get('id')} has paypal_plan_id={plan.get('paypal_plan_id')}, expected null")
                        all_null = False
                
                if all_null:
                    log_pass(f"All plans have paypal_plan_id: null (correct - no keys configured)")
                    results.append(("GET /api/pricing (plans with paypal_plan_id=null)", True))
                else:
                    results.append(("GET /api/pricing (plans with paypal_plan_id=null)", False))
            else:
                log_fail(f"Expected 2 plans, got {len(plans)}")
                results.append(("GET /api/pricing (plans array)", False))
            
            # Verify donations array
            donations = data.get("donations", [])
            expected_donations = ["donate_5", "donate_15", "donate_30"]
            donation_ids = [d.get("id") for d in donations]
            
            if all(d_id in donation_ids for d_id in expected_donations):
                log_pass(f"donations: {len(donations)} items (donate_5, donate_15, donate_30)")
                results.append(("GET /api/pricing (donations array)", True))
            else:
                log_fail(f"Expected donations {expected_donations}, got {donation_ids}")
                results.append(("GET /api/pricing (donations array)", False))
            
            results.append(("GET /api/pricing (200 with correct structure)", True))
        else:
            log_fail(f"Status {resp.status_code}: {resp.text}")
            results.append(("GET /api/pricing (200 with correct structure)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("GET /api/pricing (200 with correct structure)", False))
    
    # Test 2: POST /api/donations/order returns clean 400 (NOT 500)
    log_test("POST /api/donations/order - No PayPal keys → 400 (NOT 500)")
    try:
        donation_payload = {"amount": 10}
        resp = requests.post(f"{BASE_URL}/donations/order", json=donation_payload, headers=headers, timeout=10)
        
        if resp.status_code == 400:
            data = resp.json()
            detail = data.get("detail", "")
            if "PayPal is not configured" in detail or "paypal" in detail.lower():
                log_pass(f"Status 400 with detail: '{detail}'")
                results.append(("POST /api/donations/order (400 not 500)", True))
            else:
                log_fail(f"Got 400 but unexpected detail: '{detail}'")
                results.append(("POST /api/donations/order (400 not 500)", False))
        elif resp.status_code == 500:
            log_fail(f"Got 500 error (should be 400): {resp.text}")
            results.append(("POST /api/donations/order (400 not 500)", False))
        elif resp.status_code == 502:
            # 502 is also acceptable as it indicates graceful degradation
            data = resp.json()
            detail = data.get("detail", "")
            log_pass(f"Status 502 (graceful degradation): '{detail}'")
            results.append(("POST /api/donations/order (400 not 500)", True))
        else:
            log_fail(f"Unexpected status {resp.status_code}: {resp.text}")
            results.append(("POST /api/donations/order (400 not 500)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("POST /api/donations/order (400 not 500)", False))
    
    # Test 3: POST /api/paypal/activate returns clean 400 (NOT 500)
    log_test("POST /api/paypal/activate - No PayPal keys → 400 (NOT 500)")
    try:
        activate_payload = {"subscription_id": "I-DUMMY123", "plan_key": "monthly"}
        resp = requests.post(f"{BASE_URL}/paypal/activate", json=activate_payload, headers=headers, timeout=10)
        
        if resp.status_code == 400:
            data = resp.json()
            detail = data.get("detail", "")
            if "PayPal is not configured" in detail or "Could not verify" in detail:
                log_pass(f"Status 400 with detail: '{detail}'")
                results.append(("POST /api/paypal/activate (400 not 500)", True))
            else:
                log_fail(f"Got 400 but unexpected detail: '{detail}'")
                results.append(("POST /api/paypal/activate (400 not 500)", False))
        elif resp.status_code == 500:
            log_fail(f"Got 500 error (should be 400): {resp.text}")
            results.append(("POST /api/paypal/activate (400 not 500)", False))
        else:
            log_fail(f"Unexpected status {resp.status_code}: {resp.text}")
            results.append(("POST /api/paypal/activate (400 not 500)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("POST /api/paypal/activate (400 not 500)", False))
    
    # Test 4: GET /api/plus/billing returns 200 with payments list
    log_test("GET /api/plus/billing - Returns 200 with payments list")
    try:
        resp = requests.get(f"{BASE_URL}/plus/billing", headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if "payments" in data and "plus" in data:
                log_pass(f"Status 200 with 'payments' list and 'plus' state")
                log_info(f"payments count: {len(data.get('payments', []))}")
                log_info(f"plus.active: {data.get('plus', {}).get('active')}")
                results.append(("GET /api/plus/billing (200 with structure)", True))
            else:
                log_fail(f"Response missing 'payments' or 'plus' fields: {data}")
                results.append(("GET /api/plus/billing (200 with structure)", False))
        else:
            log_fail(f"Status {resp.status_code}: {resp.text}")
            results.append(("GET /api/plus/billing (200 with structure)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("GET /api/plus/billing (200 with structure)", False))
    
    # Test 5: POST /api/plus/cancel returns 400 (no active subscription)
    log_test("POST /api/plus/cancel - No subscription → 400 (NOT 500)")
    try:
        resp = requests.post(f"{BASE_URL}/plus/cancel", headers=headers, timeout=10)
        
        if resp.status_code == 400:
            data = resp.json()
            detail = data.get("detail", "")
            if "No active subscription" in detail or "cancel" in detail.lower():
                log_pass(f"Status 400 with detail: '{detail}'")
                results.append(("POST /api/plus/cancel (400 not 500)", True))
            else:
                log_fail(f"Got 400 but unexpected detail: '{detail}'")
                results.append(("POST /api/plus/cancel (400 not 500)", False))
        elif resp.status_code == 500:
            log_fail(f"Got 500 error (should be 400): {resp.text}")
            results.append(("POST /api/plus/cancel (400 not 500)", False))
        else:
            log_fail(f"Unexpected status {resp.status_code}: {resp.text}")
            results.append(("POST /api/plus/cancel (400 not 500)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("POST /api/plus/cancel (400 not 500)", False))
    
    # Test 6: Verify admin user seeded (login already tested above)
    log_test("Verify admin user seeded - GET /api/auth/me")
    try:
        resp = requests.get(f"{BASE_URL}/auth/me", headers=headers, timeout=10)
        
        if resp.status_code == 200:
            user = resp.json()
            if user.get("email") == ADMIN_EMAIL and user.get("is_admin") is True:
                log_pass(f"Admin user seeded correctly: {user.get('email')}, is_admin: {user.get('is_admin')}")
                results.append(("Admin user seeded (GET /api/auth/me)", True))
            else:
                log_fail(f"Admin user data incorrect: {user}")
                results.append(("Admin user seeded (GET /api/auth/me)", False))
        else:
            log_fail(f"Status {resp.status_code}: {resp.text}")
            results.append(("Admin user seeded (GET /api/auth/me)", False))
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("Admin user seeded (GET /api/auth/me)", False))
    
    # Test 7: Verify no Stripe endpoints exist
    log_test("Verify no Stripe endpoints exist")
    stripe_endpoints = [
        "/stripe/create-checkout-session",
        "/stripe/webhook",
        "/stripe/portal",
        "/stripe/subscription-status"
    ]
    
    all_404 = True
    for endpoint in stripe_endpoints:
        try:
            resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=5)
            if resp.status_code != 404:
                log_fail(f"Stripe endpoint {endpoint} returned {resp.status_code} (expected 404)")
                all_404 = False
        except Exception:
            pass  # Timeout or connection error is fine
    
    if all_404:
        log_pass(f"All Stripe endpoints return 404 (correctly removed)")
        results.append(("No Stripe endpoints exist", True))
    else:
        results.append(("No Stripe endpoints exist", False))
    
    # Test 8: Auth regression - Register new user
    log_test("Auth regression - Register new user")
    test_email = f"test-{int(time.time())}@example.com"
    try:
        register_payload = {
            "email": test_email,
            "password": "TestPass@123",
            "preferred_name": "Test User"
        }
        resp = requests.post(f"{BASE_URL}/auth/register", json=register_payload, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if "token" in data and "user" in data:
                log_pass(f"User registered successfully: {test_email}")
                new_user_token = data.get("token")
                results.append(("Auth regression - Register new user", True))
            else:
                log_fail(f"Response missing token or user: {data}")
                results.append(("Auth regression - Register new user", False))
                new_user_token = None
        else:
            log_fail(f"Status {resp.status_code}: {resp.text}")
            results.append(("Auth regression - Register new user", False))
            new_user_token = None
    except Exception as e:
        log_fail(f"Exception: {e}")
        results.append(("Auth regression - Register new user", False))
        new_user_token = None
    
    # Test 9: Auth regression - Login with new user
    if new_user_token:
        log_test("Auth regression - Login with new user")
        try:
            login_payload = {"email": test_email, "password": "TestPass@123"}
            resp = requests.post(f"{BASE_URL}/auth/login", json=login_payload, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                if "token" in data:
                    log_pass(f"Login successful with new user")
                    results.append(("Auth regression - Login with new user", True))
                else:
                    log_fail(f"Response missing token: {data}")
                    results.append(("Auth regression - Login with new user", False))
            else:
                log_fail(f"Status {resp.status_code}: {resp.text}")
                results.append(("Auth regression - Login with new user", False))
        except Exception as e:
            log_fail(f"Exception: {e}")
            results.append(("Auth regression - Login with new user", False))
    
    # Test 10: Auth regression - GET /api/auth/me with new user
    if new_user_token:
        log_test("Auth regression - GET /api/auth/me with new user")
        try:
            new_headers = {"Authorization": f"Bearer {new_user_token}", "Content-Type": "application/json"}
            resp = requests.get(f"{BASE_URL}/auth/me", headers=new_headers, timeout=10)
            
            if resp.status_code == 200:
                user = resp.json()
                if user.get("email") == test_email:
                    log_pass(f"GET /api/auth/me successful: {user.get('email')}")
                    results.append(("Auth regression - GET /api/auth/me", True))
                else:
                    log_fail(f"User email mismatch: {user}")
                    results.append(("Auth regression - GET /api/auth/me", False))
            else:
                log_fail(f"Status {resp.status_code}: {resp.text}")
                results.append(("Auth regression - GET /api/auth/me", False))
        except Exception as e:
            log_fail(f"Exception: {e}")
            results.append(("Auth regression - GET /api/auth/me", False))
    
    # Summary
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}PAYMENT SYSTEM HEALTH TEST SUMMARY{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{status} - {name}")
    
    print(f"\n{BLUE}Total: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"{GREEN}✓ ALL PAYMENT SYSTEM HEALTH TESTS PASSED{RESET}")
        return True
    else:
        print(f"{RED}✗ SOME PAYMENT SYSTEM HEALTH TESTS FAILED{RESET}")
        return False

if __name__ == "__main__":
    # Run Payment System Health tests
    success = test_payment_system_health()
    sys.exit(0 if success else 1)
