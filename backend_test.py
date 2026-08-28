#!/usr/bin/env python3
"""
Backend API test suite for CampionAI - NEW ENDPOINTS
Tests wellness plan, food, chat feedback, and doctors search endpoints.
"""
import requests
import json
import sys
from datetime import datetime

# Backend URL from frontend/.env
BASE_URL = "https://3fffec5e-d0d4-43ec-8fae-4f0ad47c6840.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@campionai.com"
ADMIN_PASSWORD = "Admin@12345"

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def log_test(name, status, details=""):
    """Log test result with color coding"""
    color = GREEN if status == "PASS" else RED if status == "FAIL" else YELLOW
    print(f"{color}[{status}]{RESET} {name}")
    if details:
        print(f"      {details}")

def test_login():
    """Test admin login and return token"""
    print(f"\n{BLUE}=== Testing Login (No-Regression) ==={RESET}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "token" in data:
                log_test("POST /api/auth/login", "PASS", f"Status: {response.status_code}, Token received")
                return data["token"]
            else:
                log_test("POST /api/auth/login", "FAIL", f"Status: {response.status_code}, No token in response")
                return None
        else:
            log_test("POST /api/auth/login", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
            return None
    except Exception as e:
        log_test("POST /api/auth/login", "FAIL", f"Exception: {str(e)}")
        return None

def test_start_trial(token):
    """Start Plus trial to enable wellness endpoints"""
    print(f"\n{BLUE}=== Starting Plus Trial ==={RESET}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/plus/start-trial",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("active"):
                log_test("POST /api/plus/start-trial", "PASS", f"Status: {response.status_code}, Plus active: {data.get('active')}")
                return True
            else:
                log_test("POST /api/plus/start-trial", "FAIL", f"Status: {response.status_code}, Plus not active")
                return False
        elif response.status_code == 400 and "Trial already used" in response.text:
            log_test("POST /api/plus/start-trial", "PASS", f"Status: {response.status_code}, Trial already active (expected)")
            return True
        else:
            log_test("POST /api/plus/start-trial", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
            return False
    except Exception as e:
        log_test("POST /api/plus/start-trial", "FAIL", f"Exception: {str(e)}")
        return False

def test_wellness_plan(token):
    """Test wellness plan endpoints"""
    print(f"\n{BLUE}=== Testing Wellness Plan Endpoints ==={RESET}")
    
    # 1. GET /api/wellness/plan
    try:
        response = requests.get(
            f"{BASE_URL}/wellness/plan",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "items" in data and isinstance(data["items"], list):
                log_test("GET /api/wellness/plan", "PASS", f"Status: {response.status_code}, Items count: {len(data['items'])}")
                initial_items_count = len(data["items"])
            else:
                log_test("GET /api/wellness/plan", "FAIL", f"Status: {response.status_code}, No items array in response")
                return False
        else:
            log_test("GET /api/wellness/plan", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
            return False
    except Exception as e:
        log_test("GET /api/wellness/plan", "FAIL", f"Exception: {str(e)}")
        return False
    
    # 2. POST /api/wellness/plan/item - Add custom item
    try:
        new_item = {
            "title": "Drink water",
            "detail": "Stay hydrated throughout the day",
            "type": "task",
            "duration_min": 5,
            "time_of_day": "morning"
        }
        response = requests.post(
            f"{BASE_URL}/wellness/plan/item",
            headers={"Authorization": f"Bearer {token}"},
            json=new_item,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") and "items" in data:
                new_count = len(data["items"])
                if new_count == initial_items_count + 1:
                    # Check if the new item has custom flag
                    last_item = data["items"][-1]
                    if last_item.get("custom") and last_item.get("title") == "Drink water":
                        log_test("POST /api/wellness/plan/item", "PASS", f"Status: {response.status_code}, Item added with custom:true")
                    else:
                        log_test("POST /api/wellness/plan/item", "FAIL", f"Status: {response.status_code}, Item added but missing custom flag or wrong title")
                else:
                    log_test("POST /api/wellness/plan/item", "FAIL", f"Status: {response.status_code}, Items count mismatch")
            else:
                log_test("POST /api/wellness/plan/item", "FAIL", f"Status: {response.status_code}, Missing ok or items in response")
        else:
            log_test("POST /api/wellness/plan/item", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
            return False
    except Exception as e:
        log_test("POST /api/wellness/plan/item", "FAIL", f"Exception: {str(e)}")
        return False
    
    # 3. DELETE /api/wellness/plan/item/{index} - Delete last item
    try:
        # Get current plan to know the count
        response = requests.get(
            f"{BASE_URL}/wellness/plan",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        current_count = len(response.json()["items"])
        last_index = current_count - 1
        
        response = requests.delete(
            f"{BASE_URL}/wellness/plan/item/{last_index}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") and len(data["items"]) == current_count - 1:
                log_test("DELETE /api/wellness/plan/item/{index}", "PASS", f"Status: {response.status_code}, Item removed")
            else:
                log_test("DELETE /api/wellness/plan/item/{index}", "FAIL", f"Status: {response.status_code}, Item not removed properly")
        else:
            log_test("DELETE /api/wellness/plan/item/{index}", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
    except Exception as e:
        log_test("DELETE /api/wellness/plan/item/{index}", "FAIL", f"Exception: {str(e)}")
    
    # 4. DELETE with out-of-range index - should return 404
    try:
        response = requests.delete(
            f"{BASE_URL}/wellness/plan/item/999",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 404:
            log_test("DELETE /api/wellness/plan/item/{out-of-range}", "PASS", f"Status: {response.status_code}, Correctly returns 404")
        else:
            log_test("DELETE /api/wellness/plan/item/{out-of-range}", "FAIL", f"Status: {response.status_code}, Expected 404")
    except Exception as e:
        log_test("DELETE /api/wellness/plan/item/{out-of-range}", "FAIL", f"Exception: {str(e)}")
    
    # 5. PUT /api/wellness/plan/reorder - Valid reorder
    try:
        # Get current plan
        response = requests.get(
            f"{BASE_URL}/wellness/plan",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        items_count = len(response.json()["items"])
        
        # Create a valid permutation (reverse order)
        valid_order = list(range(items_count))[::-1]
        
        response = requests.put(
            f"{BASE_URL}/wellness/plan/reorder",
            headers={"Authorization": f"Bearer {token}"},
            json={"order": valid_order},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") and "items" in data:
                log_test("PUT /api/wellness/plan/reorder (valid)", "PASS", f"Status: {response.status_code}, Items reordered")
            else:
                log_test("PUT /api/wellness/plan/reorder (valid)", "FAIL", f"Status: {response.status_code}, Missing ok or items")
        else:
            log_test("PUT /api/wellness/plan/reorder (valid)", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
    except Exception as e:
        log_test("PUT /api/wellness/plan/reorder (valid)", "FAIL", f"Exception: {str(e)}")
    
    # 6. PUT /api/wellness/plan/reorder - Invalid order (duplicate indices)
    try:
        response = requests.get(
            f"{BASE_URL}/wellness/plan",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        items_count = len(response.json()["items"])
        
        # Invalid order with duplicates
        invalid_order = [0, 0, 1] if items_count >= 3 else [0, 0]
        
        response = requests.put(
            f"{BASE_URL}/wellness/plan/reorder",
            headers={"Authorization": f"Bearer {token}"},
            json={"order": invalid_order},
            timeout=10
        )
        
        if response.status_code == 400:
            log_test("PUT /api/wellness/plan/reorder (invalid)", "PASS", f"Status: {response.status_code}, Correctly returns 400 for invalid order")
        else:
            log_test("PUT /api/wellness/plan/reorder (invalid)", "FAIL", f"Status: {response.status_code}, Expected 400 for invalid order")
    except Exception as e:
        log_test("PUT /api/wellness/plan/reorder (invalid)", "FAIL", f"Exception: {str(e)}")
    
    return True

def test_wellness_streak(token):
    """Test wellness streak endpoint"""
    print(f"\n{BLUE}=== Testing Wellness Streak ==={RESET}")
    
    # 1. GET /api/wellness/streak - Initial state
    try:
        response = requests.get(
            f"{BASE_URL}/wellness/streak",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "current" in data and "best" in data and "today_complete" in data:
                log_test("GET /api/wellness/streak", "PASS", 
                        f"Status: {response.status_code}, Current: {data['current']}, Best: {data['best']}, Today complete: {data['today_complete']}")
                initial_today_complete = data["today_complete"]
            else:
                log_test("GET /api/wellness/streak", "FAIL", f"Status: {response.status_code}, Missing required fields")
                return False
        else:
            log_test("GET /api/wellness/streak", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
            return False
    except Exception as e:
        log_test("GET /api/wellness/streak", "FAIL", f"Exception: {str(e)}")
        return False
    
    # 2. Toggle all items to done and check streak
    try:
        # Get current plan
        response = requests.get(
            f"{BASE_URL}/wellness/plan",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        plan = response.json()
        items = plan.get("items", [])
        
        # Toggle all items to done
        for i, item in enumerate(items):
            if not item.get("done"):
                response = requests.put(
                    f"{BASE_URL}/wellness/plan/toggle",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"item_index": i},
                    timeout=10
                )
                if response.status_code != 200:
                    log_test("Toggle items to done", "FAIL", f"Failed to toggle item {i}")
                    return False
        
        # Check streak again
        response = requests.get(
            f"{BASE_URL}/wellness/streak",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("today_complete") == True and data.get("current") >= 1:
                log_test("Streak after completing all items", "PASS", 
                        f"Status: {response.status_code}, Today complete: True, Current streak: {data['current']}")
            else:
                log_test("Streak after completing all items", "FAIL", 
                        f"Status: {response.status_code}, Today complete: {data.get('today_complete')}, Current: {data.get('current')}")
        else:
            log_test("Streak after completing all items", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("Streak after completing all items", "FAIL", f"Exception: {str(e)}")
    
    return True

def test_wellness_food(token):
    """Test wellness food endpoints"""
    print(f"\n{BLUE}=== Testing Wellness Food Endpoints ==={RESET}")
    
    food_id = None
    
    # 1. POST /api/wellness/food - Log food with meal
    try:
        food_data = {
            "text": "2 eggs and toast",
            "meal": "breakfast"
        }
        response = requests.post(
            f"{BASE_URL}/wellness/food",
            headers={"Authorization": f"Bearer {token}"},
            json=food_data,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if (data.get("meal") == "breakfast" and 
                "calories" in data and isinstance(data["calories"], int) and
                "protein_g" in data and isinstance(data["protein_g"], int) and
                "carbs_g" in data and isinstance(data["carbs_g"], int) and
                "fat_g" in data and isinstance(data["fat_g"], int)):
                log_test("POST /api/wellness/food", "PASS", 
                        f"Status: {response.status_code}, Meal: {data['meal']}, Calories: {data['calories']}, Protein: {data['protein_g']}g")
                food_id = data.get("id")
            else:
                log_test("POST /api/wellness/food", "FAIL", f"Status: {response.status_code}, Missing or invalid nutrition data")
                return False
        else:
            log_test("POST /api/wellness/food", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
            return False
    except Exception as e:
        log_test("POST /api/wellness/food", "FAIL", f"Exception: {str(e)}")
        return False
    
    # 2. GET /api/wellness/food - Get food logs
    try:
        response = requests.get(
            f"{BASE_URL}/wellness/food",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "totals" in data and "logs" in data:
                # Check if our new log is present
                logs = data.get("logs", [])
                found = any(log.get("id") == food_id for log in logs)
                if found:
                    log_test("GET /api/wellness/food", "PASS", 
                            f"Status: {response.status_code}, Logs count: {len(logs)}, New log present with meal field")
                else:
                    log_test("GET /api/wellness/food", "FAIL", f"Status: {response.status_code}, New log not found")
            else:
                log_test("GET /api/wellness/food", "FAIL", f"Status: {response.status_code}, Missing totals or logs")
        else:
            log_test("GET /api/wellness/food", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
    except Exception as e:
        log_test("GET /api/wellness/food", "FAIL", f"Exception: {str(e)}")
    
    # 3. PUT /api/wellness/food/{fid} - Edit food log
    if food_id:
        try:
            edit_data = {
                "summary": "Eggs and whole wheat toast",
                "calories": 250
            }
            response = requests.put(
                f"{BASE_URL}/wellness/food/{food_id}",
                headers={"Authorization": f"Bearer {token}"},
                json=edit_data,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("summary") == "Eggs and whole wheat toast" and data.get("calories") == 250:
                    log_test("PUT /api/wellness/food/{fid}", "PASS", 
                            f"Status: {response.status_code}, Updated summary and calories")
                else:
                    log_test("PUT /api/wellness/food/{fid}", "FAIL", f"Status: {response.status_code}, Changes not reflected")
            else:
                log_test("PUT /api/wellness/food/{fid}", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
        except Exception as e:
            log_test("PUT /api/wellness/food/{fid}", "FAIL", f"Exception: {str(e)}")
    
    # 4. PUT with unknown fid - should return 404
    try:
        response = requests.put(
            f"{BASE_URL}/wellness/food/unknown-food-id-12345",
            headers={"Authorization": f"Bearer {token}"},
            json={"summary": "Test", "calories": 100},
            timeout=10
        )
        
        if response.status_code == 404:
            log_test("PUT /api/wellness/food/{unknown-fid}", "PASS", f"Status: {response.status_code}, Correctly returns 404")
        else:
            log_test("PUT /api/wellness/food/{unknown-fid}", "FAIL", f"Status: {response.status_code}, Expected 404")
    except Exception as e:
        log_test("PUT /api/wellness/food/{unknown-fid}", "FAIL", f"Exception: {str(e)}")
    
    # 5. PUT with empty body - should return 400
    if food_id:
        try:
            response = requests.put(
                f"{BASE_URL}/wellness/food/{food_id}",
                headers={"Authorization": f"Bearer {token}"},
                json={},
                timeout=10
            )
            
            if response.status_code == 400:
                log_test("PUT /api/wellness/food/{fid} (empty body)", "PASS", f"Status: {response.status_code}, Correctly returns 400")
            else:
                log_test("PUT /api/wellness/food/{fid} (empty body)", "FAIL", f"Status: {response.status_code}, Expected 400")
        except Exception as e:
            log_test("PUT /api/wellness/food/{fid} (empty body)", "FAIL", f"Exception: {str(e)}")
    
    return True

def test_chat_feedback(token):
    """Test chat feedback endpoint"""
    print(f"\n{BLUE}=== Testing Chat Feedback Endpoint ==={RESET}")
    
    # 1. POST /api/chat/feedback - Valid rating "up"
    try:
        feedback_data = {
            "session_id": None,
            "content": "This was helpful",
            "rating": "up"
        }
        response = requests.post(
            f"{BASE_URL}/chat/feedback",
            headers={"Authorization": f"Bearer {token}"},
            json=feedback_data,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                log_test("POST /api/chat/feedback (rating: up)", "PASS", f"Status: {response.status_code}, ok: true")
            else:
                log_test("POST /api/chat/feedback (rating: up)", "FAIL", f"Status: {response.status_code}, ok not true")
        else:
            log_test("POST /api/chat/feedback (rating: up)", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
    except Exception as e:
        log_test("POST /api/chat/feedback (rating: up)", "FAIL", f"Exception: {str(e)}")
    
    # 2. POST /api/chat/feedback - Valid rating "down"
    try:
        feedback_data = {
            "session_id": None,
            "content": "Not helpful",
            "rating": "down"
        }
        response = requests.post(
            f"{BASE_URL}/chat/feedback",
            headers={"Authorization": f"Bearer {token}"},
            json=feedback_data,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                log_test("POST /api/chat/feedback (rating: down)", "PASS", f"Status: {response.status_code}, ok: true")
            else:
                log_test("POST /api/chat/feedback (rating: down)", "FAIL", f"Status: {response.status_code}, ok not true")
        else:
            log_test("POST /api/chat/feedback (rating: down)", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
    except Exception as e:
        log_test("POST /api/chat/feedback (rating: down)", "FAIL", f"Exception: {str(e)}")
    
    # 3. POST /api/chat/feedback - Invalid rating
    try:
        feedback_data = {
            "session_id": None,
            "content": "Test",
            "rating": "sideways"
        }
        response = requests.post(
            f"{BASE_URL}/chat/feedback",
            headers={"Authorization": f"Bearer {token}"},
            json=feedback_data,
            timeout=10
        )
        
        if response.status_code == 422:
            log_test("POST /api/chat/feedback (invalid rating)", "PASS", f"Status: {response.status_code}, Correctly returns 422")
        else:
            log_test("POST /api/chat/feedback (invalid rating)", "FAIL", f"Status: {response.status_code}, Expected 422")
    except Exception as e:
        log_test("POST /api/chat/feedback (invalid rating)", "FAIL", f"Exception: {str(e)}")
    
    # 4. POST /api/chat/feedback - Missing auth header
    try:
        feedback_data = {
            "session_id": None,
            "content": "Test",
            "rating": "up"
        }
        response = requests.post(
            f"{BASE_URL}/chat/feedback",
            json=feedback_data,
            timeout=10
        )
        
        if response.status_code in [401, 403]:
            log_test("POST /api/chat/feedback (no auth)", "PASS", f"Status: {response.status_code}, Correctly requires auth")
        else:
            log_test("POST /api/chat/feedback (no auth)", "FAIL", f"Status: {response.status_code}, Expected 401/403")
    except Exception as e:
        log_test("POST /api/chat/feedback (no auth)", "FAIL", f"Exception: {str(e)}")
    
    return True

def test_doctors_search(token):
    """Test doctors search endpoint"""
    print(f"\n{BLUE}=== Testing Doctors Search Endpoint ==={RESET}")
    
    # 1. GET /api/doctors - List all doctors
    try:
        response = requests.get(
            f"{BASE_URL}/doctors",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                log_test("GET /api/doctors", "PASS", f"Status: {response.status_code}, Doctors count: {len(data)}")
                
                # Verify demo doctors are seeded (at least 5)
                if len(data) >= 5:
                    log_test("Demo doctors seeded", "PASS", f"Found {len(data)} doctors (expected >= 5)")
                else:
                    log_test("Demo doctors seeded", "FAIL", f"Found {len(data)} doctors (expected >= 5)")
            else:
                log_test("GET /api/doctors", "FAIL", f"Status: {response.status_code}, Response is not a list")
                return False
        else:
            log_test("GET /api/doctors", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
            return False
    except Exception as e:
        log_test("GET /api/doctors", "FAIL", f"Exception: {str(e)}")
        return False
    
    # 2. GET /api/doctors?q=aisha - Search by name
    try:
        response = requests.get(
            f"{BASE_URL}/doctors?q=aisha",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                # Check if results contain "aisha" in name
                matching = [d for d in data if "aisha" in (d.get("name") or "").lower()]
                if len(matching) > 0:
                    log_test("GET /api/doctors?q=aisha", "PASS", f"Status: {response.status_code}, Found {len(matching)} matching doctor(s)")
                else:
                    log_test("GET /api/doctors?q=aisha", "FAIL", f"Status: {response.status_code}, No matching doctors found")
            else:
                log_test("GET /api/doctors?q=aisha", "FAIL", f"Status: {response.status_code}, Response is not a list")
        else:
            log_test("GET /api/doctors?q=aisha", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
    except Exception as e:
        log_test("GET /api/doctors?q=aisha", "FAIL", f"Exception: {str(e)}")
    
    # 3. GET /api/doctors?q=sleep - Search by specialty
    try:
        response = requests.get(
            f"{BASE_URL}/doctors?q=sleep",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                # Check if results contain "sleep" in specialty
                matching = [d for d in data if "sleep" in (d.get("specialty") or "").lower()]
                if len(matching) > 0:
                    log_test("GET /api/doctors?q=sleep", "PASS", f"Status: {response.status_code}, Found {len(matching)} matching doctor(s) by specialty")
                else:
                    log_test("GET /api/doctors?q=sleep", "FAIL", f"Status: {response.status_code}, No matching doctors found by specialty")
            else:
                log_test("GET /api/doctors?q=sleep", "FAIL", f"Status: {response.status_code}, Response is not a list")
        else:
            log_test("GET /api/doctors?q=sleep", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
    except Exception as e:
        log_test("GET /api/doctors?q=sleep", "FAIL", f"Exception: {str(e)}")
    
    # 4. GET /api/doctors?q=zzzznomatch - Search with no matches
    try:
        response = requests.get(
            f"{BASE_URL}/doctors?q=zzzznomatch",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) == 0:
                log_test("GET /api/doctors?q=zzzznomatch", "PASS", f"Status: {response.status_code}, Empty list returned (expected)")
            else:
                log_test("GET /api/doctors?q=zzzznomatch", "FAIL", f"Status: {response.status_code}, Expected empty list")
        else:
            log_test("GET /api/doctors?q=zzzznomatch", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
    except Exception as e:
        log_test("GET /api/doctors?q=zzzznomatch", "FAIL", f"Exception: {str(e)}")
    
    return True

def main():
    """Run all tests"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}CampionAI Backend API Tests - NEW ENDPOINTS{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    # 1. Test login (no-regression)
    token = test_login()
    if not token:
        print(f"\n{RED}CRITICAL: Login failed. Cannot proceed with other tests.{RESET}")
        sys.exit(1)
    
    # 2. Start Plus trial
    trial_started = test_start_trial(token)
    if not trial_started:
        print(f"\n{RED}CRITICAL: Could not start Plus trial. Wellness endpoints will fail.{RESET}")
        sys.exit(1)
    
    # 3. Test wellness plan endpoints
    test_wellness_plan(token)
    
    # 4. Test wellness streak
    test_wellness_streak(token)
    
    # 5. Test wellness food endpoints
    test_wellness_food(token)
    
    # 6. Test chat feedback
    test_chat_feedback(token)
    
    # 7. Test doctors search
    test_doctors_search(token)
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}All tests completed!{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

if __name__ == "__main__":
    main()
