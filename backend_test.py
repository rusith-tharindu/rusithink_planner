import requests
import sys
from datetime import datetime, timedelta
import json

class ProjectPlannerAPITester:
    def __init__(self, base_url="https://taskmaster-pro-11.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_task_id = None
        self.admin_session_token = None
        self.admin_cookies = None

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None, cookies=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        request_headers = {'Content-Type': 'application/json'}
        if headers:
            request_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=request_headers, params=params, cookies=cookies)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=request_headers, cookies=cookies)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=request_headers, params=params, cookies=cookies)
            elif method == 'DELETE':
                response = requests.delete(url, headers=request_headers, cookies=cookies)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data, response.cookies
                except:
                    return True, {}, response.cookies
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}, None

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}, None

    # ========== AUTHENTICATION TESTS ==========
    
    def test_admin_login_success(self):
        """Test admin login with correct credentials"""
        login_data = {
            "username": "rusithink",
            "password": "20200104Rh"
        }
        
        success, response, cookies = self.run_test(
            "Admin Login (Valid Credentials)", 
            "POST", 
            "auth/admin-login", 
            200, 
            data=login_data
        )
        
        if success:
            # Store session for future tests
            self.admin_cookies = cookies
            if 'session_token' in response:
                self.admin_session_token = response['session_token']
            
            # Verify response structure
            if 'user' in response and response['user'].get('role') == 'admin':
                print(f"   ✅ Admin user authenticated: {response['user']['name']}")
                print(f"   ✅ User role: {response['user']['role']}")
                return True
            else:
                print(f"   ❌ Invalid response structure or role")
                return False
        
        return success

    def test_admin_login_invalid_credentials(self):
        """Test admin login with invalid credentials"""
        login_data = {
            "username": "rusithink",
            "password": "wrongpassword"
        }
        
        success, response, _ = self.run_test(
            "Admin Login (Invalid Credentials)", 
            "POST", 
            "auth/admin-login", 
            401, 
            data=login_data
        )
        return success

    def test_admin_login_invalid_username(self):
        """Test admin login with invalid username"""
        login_data = {
            "username": "wronguser",
            "password": "20200104Rh"
        }
        
        success, response, _ = self.run_test(
            "Admin Login (Invalid Username)", 
            "POST", 
            "auth/admin-login", 
            401, 
            data=login_data
        )
        return success

    def test_get_current_user_authenticated(self):
        """Test getting current user info when authenticated"""
        if not self.admin_cookies:
            print("❌ No admin session available for authenticated user test")
            return False
        
        success, response, _ = self.run_test(
            "Get Current User (Authenticated)", 
            "GET", 
            "auth/me", 
            200,
            cookies=self.admin_cookies
        )
        
        if success and response.get('role') == 'admin':
            print(f"   ✅ Current user: {response.get('name')} ({response.get('role')})")
            return True
        
        return success

    def test_get_current_user_unauthenticated(self):
        """Test getting current user info when not authenticated"""
        success, response, _ = self.run_test(
            "Get Current User (Unauthenticated)", 
            "GET", 
            "auth/me", 
            401
        )
        return success

    def test_oauth_session_missing_header(self):
        """Test OAuth session processing without X-Session-ID header"""
        success, response, _ = self.run_test(
            "OAuth Session (Missing Header)", 
            "POST", 
            "auth/oauth/session-data", 
            400
        )
        return success

    def test_oauth_session_invalid_id(self):
        """Test OAuth session processing with invalid session ID"""
        headers = {"X-Session-ID": "invalid-session-id"}
        success, response, _ = self.run_test(
            "OAuth Session (Invalid ID)", 
            "POST", 
            "auth/oauth/session-data", 
            401,
            headers=headers
        )
        return success

    def test_logout(self):
        """Test logout functionality"""
        if not self.admin_cookies:
            print("❌ No admin session available for logout test")
            return False
        
        success, response, _ = self.run_test(
            "Admin Logout", 
            "POST", 
            "auth/logout", 
            200,
            cookies=self.admin_cookies
        )
        
        if success:
            # Clear stored session
            self.admin_cookies = None
            self.admin_session_token = None
            print("   ✅ Session cleared")
        
        return success

    # ========== AUTHORIZATION TESTS ==========

    def test_create_task_as_admin(self):
        """Test task creation as admin"""
        if not self.admin_cookies:
            print("❌ No admin session available for task creation test")
            return False
        
        # Create a task due tomorrow at 2 PM
        due_date = datetime.now() + timedelta(days=1)
        due_date = due_date.replace(hour=14, minute=0, second=0, microsecond=0)
        
        task_data = {
            "title": "Admin Test Task - Website Redesign",
            "description": "Complete redesign of company website with modern UI/UX",
            "due_datetime": due_date.isoformat(),
            "project_price": 5000.0,
            "priority": "high"
        }
        
        success, response, _ = self.run_test(
            "Create Task (Admin)", 
            "POST", 
            "tasks", 
            200, 
            data=task_data,
            cookies=self.admin_cookies
        )
        
        if success and 'id' in response:
            self.created_task_id = response['id']
            print(f"   ✅ Created task ID: {self.created_task_id}")
            print(f"   ✅ Task created by: {response.get('client_name')}")
        
        return success

    def test_get_tasks_as_admin(self):
        """Test getting all tasks as admin"""
        if not self.admin_cookies:
            print("❌ No admin session available for get tasks test")
            return False
        
        success, response, _ = self.run_test(
            "Get All Tasks (Admin)", 
            "GET", 
            "tasks", 
            200,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Retrieved {len(response)} tasks")
        
        return success

    def test_get_task_stats_as_admin(self):
        """Test getting task statistics as admin"""
        if not self.admin_cookies:
            print("❌ No admin session available for stats test")
            return False
        
        success, response, _ = self.run_test(
            "Get Task Stats (Admin)", 
            "GET", 
            "tasks/stats/overview", 
            200,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Stats - Total: {response.get('total_tasks')}, Pending: {response.get('pending_tasks')}")
            print(f"   ✅ User role in stats: {response.get('user_role')}")
        
        return success

    def test_delete_task_as_admin(self):
        """Test deleting a task as admin (admin-only operation)"""
        if not self.admin_cookies:
            print("❌ No admin session available for delete test")
            return False
        
        if not self.created_task_id:
            print("❌ No task ID available for delete test")
            return False
        
        success, response, _ = self.run_test(
            "Delete Task (Admin Only)", 
            "DELETE", 
            f"tasks/{self.created_task_id}", 
            200,
            cookies=self.admin_cookies
        )
        
        if success:
            print("   ✅ Task deleted successfully (admin privilege)")
        
        return success

    def test_admin_get_all_users(self):
        """Test admin endpoint to get all users"""
        if not self.admin_cookies:
            print("❌ No admin session available for get users test")
            return False
        
        success, response, _ = self.run_test(
            "Get All Users (Admin Only)", 
            "GET", 
            "admin/users", 
            200,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Retrieved {len(response)} users")
            for user in response[:3]:  # Show first 3 users
                print(f"   - {user.get('name')} ({user.get('email')}) - {user.get('role')}")
        
        return success

    def test_protected_routes_without_auth(self):
        """Test that protected routes require authentication"""
        endpoints_to_test = [
            ("tasks", "GET"),
            ("tasks/stats/overview", "GET"),
            ("admin/users", "GET")
        ]
        
        all_passed = True
        for endpoint, method in endpoints_to_test:
            success, _, _ = self.run_test(
                f"Protected Route {endpoint} (No Auth)", 
                method, 
                endpoint, 
                401
            )
            if not success:
                all_passed = False
        
        return all_passed

    def test_api_root(self):
        """Test API root endpoint"""
        success, _, _ = self.run_test("API Root", "GET", "", 200)
        return success

    # ========== LEGACY CRUD TESTS (Updated) ==========
        """Test task creation"""
        # Create a task due tomorrow at 2 PM
        due_date = datetime.now() + timedelta(days=1)
        due_date = due_date.replace(hour=14, minute=0, second=0, microsecond=0)
        
        task_data = {
            "title": "Website Redesign Project",
            "description": "Complete redesign of company website with modern UI/UX",
            "due_datetime": due_date.isoformat(),
            "project_price": 5000.0,
            "priority": "high"
        }
        
    def test_create_task(self):
        """Test task creation (legacy test - requires auth now)"""
        # Create a task due tomorrow at 2 PM
        due_date = datetime.now() + timedelta(days=1)
        due_date = due_date.replace(hour=14, minute=0, second=0, microsecond=0)
        
        task_data = {
            "title": "Website Redesign Project",
            "description": "Complete redesign of company website with modern UI/UX",
            "due_datetime": due_date.isoformat(),
            "project_price": 5000.0,
            "priority": "high"
        }
        
        success, response, _ = self.run_test("Create Task (No Auth)", "POST", "tasks", 401, data=task_data)
        return success

    def test_get_tasks(self):
        """Test getting all tasks (legacy test - requires auth now)"""
        success, _, _ = self.run_test("Get All Tasks (No Auth)", "GET", "tasks", 401)
        return success

    def test_get_single_task(self):
        """Test getting a single task (legacy test - requires auth now)"""
        fake_id = "test-task-id"
        success, _, _ = self.run_test("Get Single Task (No Auth)", "GET", f"tasks/{fake_id}", 401)
        return success

    def test_update_task_status(self):
        """Test updating task status (legacy test - requires auth now)"""
        fake_id = "test-task-id"
        success, _, _ = self.run_test(
            "Update Task Status (No Auth)", 
            "PUT", 
            f"tasks/{fake_id}/status", 
            401,
            params={"status": "completed"}
        )
        return success

    def test_update_task(self):
        """Test updating task details (legacy test - requires auth now)"""
        fake_id = "test-task-id"
        update_data = {
            "title": "Updated Website Redesign Project",
            "project_price": 6000.0
        }
        
        success, _, _ = self.run_test(
            "Update Task (No Auth)", 
            "PUT", 
            f"tasks/{fake_id}", 
            401,
            data=update_data
        )
        return success

    def test_get_stats(self):
        """Test getting task statistics (legacy test - requires auth now)"""
        success, _, _ = self.run_test("Get Task Stats (No Auth)", "GET", "tasks/stats/overview", 401)
        return success

    def test_delete_task(self):
        """Test deleting a task (legacy test - requires auth now)"""
        fake_id = "test-task-id"
        success, _, _ = self.run_test("Delete Task (No Auth)", "DELETE", f"tasks/{fake_id}", 401)
        return success

    def test_get_nonexistent_task(self):
        """Test getting a non-existent task (should return 401 due to auth requirement)"""
        fake_id = "non-existent-task-id"
        success, _, _ = self.run_test("Get Non-existent Task (No Auth)", "GET", f"tasks/{fake_id}", 401)
        return success

def main():
    print("🚀 Starting Project Planner API Tests")
    print("=" * 50)
    
    tester = ProjectPlannerAPITester()
    
    # Test sequence
    test_results = []
    
    # Basic connectivity
    test_results.append(tester.test_api_root())
    
    # CRUD operations
    test_results.append(tester.test_create_task())
    test_results.append(tester.test_get_tasks())
    test_results.append(tester.test_get_single_task())
    test_results.append(tester.test_update_task_status())
    test_results.append(tester.test_update_task())
    
    # Stats
    test_results.append(tester.test_get_stats())
    
    # Error handling
    test_results.append(tester.test_get_nonexistent_task())
    
    # Cleanup
    test_results.append(tester.test_delete_task())

    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 FINAL RESULTS")
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed! Backend API is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the backend implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())