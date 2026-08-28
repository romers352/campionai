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
BASE_URL = "https://fix-it-features.preview.emergentagent.com/api"

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

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
