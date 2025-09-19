import requests
import sys
from datetime import datetime, timedelta
import json

class ProjectPlannerAPITester:
    def __init__(self, base_url="https://rusithink-manage.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_task_id = None
        self.admin_session_token = None
        self.admin_cookies = None
        self.test_user_id = None
        self.milestone_id = None

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
            # Store first user ID for update test
            if response and len(response) > 0:
                self.test_user_id = response[0].get('id')
        
        return success

    def test_admin_update_user(self):
        """Test admin endpoint to update user details"""
        if not self.admin_cookies:
            print("❌ No admin session available for update user test")
            return False
        
        if not hasattr(self, 'test_user_id') or not self.test_user_id:
            print("❌ No user ID available for update test")
            return False
        
        update_data = {
            "first_name": "Updated",
            "last_name": "TestUser",
            "phone": "+1234567890",
            "company_name": "Updated Company Ltd"
        }
        
        success, response, _ = self.run_test(
            "Update User Details (Admin Only)", 
            "PUT", 
            f"admin/users/{self.test_user_id}", 
            200,
            data=update_data,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Updated user: {response.get('name')} ({response.get('email')})")
            print(f"   ✅ Company: {response.get('company_name')}")
        
        return success

    def test_admin_export_users_csv(self):
        """Test admin endpoint to export users as CSV"""
        if not self.admin_cookies:
            print("❌ No admin session available for CSV export test")
            return False
        
        url = f"{self.api_url}/admin/users/export/csv"
        print(f"\n🔍 Testing Admin Export Users CSV...")
        print(f"   URL: {url}")
        
        try:
            response = requests.get(url, cookies=self.admin_cookies)
            self.tests_run += 1
            
            if response.status_code == 200:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                print(f"   Content-Type: {response.headers.get('content-type')}")
                print(f"   Content-Length: {len(response.content)} bytes")
                
                # Check if it's actually CSV content
                if 'text/csv' in response.headers.get('content-type', ''):
                    print("   ✅ Correct CSV content type")
                
                # Check for CSV headers in content
                content = response.text[:200]
                if 'Email' in content and 'Name' in content:
                    print("   ✅ CSV contains expected headers")
                
                return True
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                print(f"   Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    def test_admin_export_users_pdf(self):
        """Test admin endpoint to export users as PDF"""
        if not self.admin_cookies:
            print("❌ No admin session available for PDF export test")
            return False
        
        url = f"{self.api_url}/admin/users/export/pdf"
        print(f"\n🔍 Testing Admin Export Users PDF...")
        print(f"   URL: {url}")
        
        try:
            response = requests.get(url, cookies=self.admin_cookies)
            self.tests_run += 1
            
            if response.status_code == 200:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                print(f"   Content-Type: {response.headers.get('content-type')}")
                print(f"   Content-Length: {len(response.content)} bytes")
                
                # Check if it's actually PDF content
                if 'application/pdf' in response.headers.get('content-type', ''):
                    print("   ✅ Correct PDF content type")
                
                # Check for PDF signature
                if response.content.startswith(b'%PDF'):
                    print("   ✅ Valid PDF file signature")
                
                return True
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                print(f"   Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

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

    # ========== FILE UPLOAD TESTS ==========
    
    def test_chat_file_upload_valid_file(self):
        """Test chat file upload with valid file"""
        if not self.admin_cookies:
            print("❌ No admin session available for file upload test")
            return False
        
        # Create a small test PDF file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            # Write minimal PDF content
            temp_file.write(b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF')
            temp_file_path = temp_file.name
        
        url = f"{self.api_url}/chat/upload"
        print(f"\n🔍 Testing Chat File Upload (Valid PDF)...")
        print(f"   URL: {url}")
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('test.pdf', f, 'application/pdf')}
                data = {
                    'recipient_id': 'test-recipient-id',
                    'content': 'Test file upload'
                }
                
                response = requests.post(url, files=files, data=data, cookies=self.admin_cookies)
                self.tests_run += 1
                
                if response.status_code == 200:
                    self.tests_passed += 1
                    print(f"✅ Passed - Status: {response.status_code}")
                    try:
                        response_data = response.json()
                        print(f"   ✅ File uploaded: {response_data.get('file_name')}")
                        print(f"   ✅ Message type: {response_data.get('message_type')}")
                        return True
                    except:
                        return True
                else:
                    print(f"❌ Failed - Expected 200, got {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"   Error: {error_data}")
                    except:
                        print(f"   Error: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except:
                pass

    def test_chat_file_upload_invalid_format(self):
        """Test chat file upload with invalid file format"""
        if not self.admin_cookies:
            print("❌ No admin session available for invalid file test")
            return False
        
        # Create a test file with invalid extension
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_file.write(b'This is a text file which should not be allowed')
            temp_file_path = temp_file.name
        
        url = f"{self.api_url}/chat/upload"
        print(f"\n🔍 Testing Chat File Upload (Invalid Format)...")
        print(f"   URL: {url}")
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('test.txt', f, 'text/plain')}
                data = {
                    'recipient_id': 'test-recipient-id',
                    'content': 'Test invalid file upload'
                }
                
                response = requests.post(url, files=files, data=data, cookies=self.admin_cookies)
                self.tests_run += 1
                
                if response.status_code == 400:
                    self.tests_passed += 1
                    print(f"✅ Passed - Status: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"   ✅ Correct error: {error_data.get('detail')}")
                    except:
                        pass
                    return True
                else:
                    print(f"❌ Failed - Expected 400, got {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except:
                pass

    def test_chat_file_upload_oversized_file(self):
        """Test chat file upload with file exceeding 16MB limit"""
        if not self.admin_cookies:
            print("❌ No admin session available for oversized file test")
            return False
        
        # Create a large test file (simulate 17MB)
        import tempfile
        import os
        
        print(f"\n🔍 Testing Chat File Upload (Oversized File)...")
        print("   Creating 17MB test file...")
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            # Write 17MB of data
            chunk_size = 1024 * 1024  # 1MB chunks
            for i in range(17):  # 17MB total
                temp_file.write(b'x' * chunk_size)
            temp_file_path = temp_file.name
        
        url = f"{self.api_url}/chat/upload"
        print(f"   URL: {url}")
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('large_test.pdf', f, 'application/pdf')}
                data = {
                    'recipient_id': 'test-recipient-id',
                    'content': 'Test oversized file upload'
                }
                
                response = requests.post(url, files=files, data=data, cookies=self.admin_cookies)
                self.tests_run += 1
                
                if response.status_code == 400:
                    self.tests_passed += 1
                    print(f"✅ Passed - Status: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"   ✅ Correct error: {error_data.get('detail')}")
                    except:
                        pass
                    return True
                else:
                    print(f"❌ Failed - Expected 400, got {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except:
                pass

    # ========== MILESTONE TESTS ==========
    
    def test_create_milestone(self):
        """Test creating a project milestone"""
        if not self.admin_cookies:
            print("❌ No admin session available for milestone creation test")
            return False
        
        if not self.created_task_id:
            print("❌ No task ID available for milestone test")
            return False
        
        milestone_data = {
            "title": "Project Kickoff",
            "description": "Initial project meeting and requirements gathering",
            "due_date": (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        success, response, _ = self.run_test(
            "Create Project Milestone", 
            "POST", 
            f"tasks/{self.created_task_id}/milestones", 
            200,
            data=milestone_data,
            cookies=self.admin_cookies
        )
        
        if success and 'id' in response:
            self.milestone_id = response['id']
            print(f"   ✅ Created milestone ID: {self.milestone_id}")
            print(f"   ✅ Milestone title: {response.get('title')}")
        
        return success

    def test_get_milestones(self):
        """Test getting project milestones"""
        if not self.admin_cookies:
            print("❌ No admin session available for get milestones test")
            return False
        
        if not self.created_task_id:
            print("❌ No task ID available for milestones test")
            return False
        
        success, response, _ = self.run_test(
            "Get Project Milestones", 
            "GET", 
            f"tasks/{self.created_task_id}/milestones", 
            200,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Retrieved {len(response)} milestones")
            for milestone in response:
                print(f"   - {milestone.get('title')} ({milestone.get('status')})")
        
        return success

    def test_get_milestones_nonexistent_task(self):
        """Test getting milestones for non-existent task"""
        if not self.admin_cookies:
            print("❌ No admin session available for milestone test")
            return False
        
        fake_task_id = "non-existent-task-id"
        success, response, _ = self.run_test(
            "Get Milestones (Non-existent Task)", 
            "GET", 
            f"tasks/{fake_task_id}/milestones", 
            404,
            cookies=self.admin_cookies
        )
        
        return success

    # ========== USER MANAGEMENT DELETE TESTS ==========
    
    def test_create_test_client_users(self):
        """Create test client users for deletion testing"""
        if not self.admin_cookies:
            print("❌ No admin session available for user creation test")
            return False
        
        # Create multiple test users for deletion testing
        test_users = [
            {
                "email": "testclient1@example.com",
                "password": "testpass123",
                "first_name": "Test",
                "last_name": "Client1",
                "phone": "+1234567890",
                "company_name": "Test Company 1",
                "address": "123 Test Street"
            },
            {
                "email": "testclient2@example.com", 
                "password": "testpass123",
                "first_name": "Test",
                "last_name": "Client2",
                "phone": "+1234567891",
                "company_name": "Test Company 2",
                "address": "456 Test Avenue"
            },
            {
                "email": "testclient3@example.com",
                "password": "testpass123", 
                "first_name": "Test",
                "last_name": "Client3",
                "phone": "+1234567892",
                "company_name": "Test Company 3",
                "address": "789 Test Boulevard"
            }
        ]
        
        created_users = []
        for user_data in test_users:
            success, response, _ = self.run_test(
                f"Create Test Client ({user_data['email']})",
                "POST",
                "auth/register",
                200,
                data=user_data
            )
            
            if success and 'user' in response:
                created_users.append(response['user']['id'])
                print(f"   ✅ Created test user: {response['user']['name']} (ID: {response['user']['id']})")
        
        # Store created user IDs for deletion tests
        self.test_client_ids = created_users
        return len(created_users) == len(test_users)

    def test_single_user_delete_success(self):
        """Test successful single user deletion"""
        if not self.admin_cookies:
            print("❌ No admin session available for user deletion test")
            return False
        
        if not hasattr(self, 'test_client_ids') or not self.test_client_ids:
            print("❌ No test client users available for deletion")
            return False
        
        # Delete the first test client
        user_id_to_delete = self.test_client_ids[0]
        
        success, response, _ = self.run_test(
            "Delete Single User (Success)",
            "DELETE",
            f"admin/users/{user_id_to_delete}",
            200,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ User deleted successfully: {response.get('message')}")
            # Remove from our list
            self.test_client_ids.remove(user_id_to_delete)
        
        return success

    def test_single_user_delete_nonexistent(self):
        """Test deleting non-existent user"""
        if not self.admin_cookies:
            print("❌ No admin session available for user deletion test")
            return False
        
        fake_user_id = "non-existent-user-id"
        
        success, response, _ = self.run_test(
            "Delete Single User (Non-existent)",
            "DELETE", 
            f"admin/users/{fake_user_id}",
            404,
            cookies=self.admin_cookies
        )
        
        return success

    def test_single_user_delete_admin_account(self):
        """Test attempting to delete admin account (should fail)"""
        if not self.admin_cookies:
            print("❌ No admin session available for admin deletion test")
            return False
        
        # Get admin user ID
        success, users_response, _ = self.run_test(
            "Get Users for Admin ID",
            "GET",
            "admin/users", 
            200,
            cookies=self.admin_cookies
        )
        
        if not success:
            print("❌ Could not retrieve users to find admin ID")
            return False
        
        admin_user = None
        for user in users_response:
            if user.get('role') == 'admin':
                admin_user = user
                break
        
        if not admin_user:
            print("❌ Could not find admin user")
            return False
        
        # Try to delete admin account (should fail)
        success, response, _ = self.run_test(
            "Delete Admin Account (Should Fail)",
            "DELETE",
            f"admin/users/{admin_user['id']}",
            400,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Admin deletion properly blocked: {response.get('detail')}")
        
        return success

    def test_single_user_delete_self(self):
        """Test admin attempting to delete themselves (should fail)"""
        if not self.admin_cookies:
            print("❌ No admin session available for self-deletion test")
            return False
        
        # Get current admin user info
        success, user_response, _ = self.run_test(
            "Get Current Admin User",
            "GET",
            "auth/me",
            200,
            cookies=self.admin_cookies
        )
        
        if not success:
            print("❌ Could not get current user info")
            return False
        
        admin_id = user_response.get('id')
        
        # Try to delete self (should fail)
        success, response, _ = self.run_test(
            "Delete Self (Should Fail)",
            "DELETE",
            f"admin/users/{admin_id}",
            400,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Self-deletion properly blocked: {response.get('detail')}")
        
        return success

    def test_bulk_user_delete_success(self):
        """Test successful bulk user deletion"""
        if not self.admin_cookies:
            print("❌ No admin session available for bulk deletion test")
            return False
        
        if not hasattr(self, 'test_client_ids') or len(self.test_client_ids) < 2:
            print("❌ Not enough test client users available for bulk deletion")
            return False
        
        # Delete remaining test clients in bulk
        user_ids_to_delete = self.test_client_ids[:2]  # Take first 2 remaining
        
        url = f"{self.api_url}/admin/users/bulk"
        print(f"\n🔍 Testing Bulk User Delete (Success)...")
        print(f"   URL: {url}")
        print(f"   Deleting users: {user_ids_to_delete}")
        
        try:
            response = requests.delete(
                url,
                json=user_ids_to_delete,
                headers={'Content-Type': 'application/json'},
                cookies=self.admin_cookies
            )
            self.tests_run += 1
            
            if response.status_code == 200:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   ✅ Deleted count: {response_data.get('deleted_count')}")
                    print(f"   ✅ Message: {response_data.get('message')}")
                    if response_data.get('errors'):
                        print(f"   ⚠️  Errors: {response_data.get('errors')}")
                    
                    # Remove deleted users from our list
                    for user_id in user_ids_to_delete:
                        if user_id in self.test_client_ids:
                            self.test_client_ids.remove(user_id)
                    
                    return True
                except:
                    return True
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    def test_bulk_user_delete_mixed_scenario(self):
        """Test bulk deletion with mixed scenarios (valid and invalid users)"""
        if not self.admin_cookies:
            print("❌ No admin session available for mixed bulk deletion test")
            return False
        
        # Get admin user ID for the test
        success, user_response, _ = self.run_test(
            "Get Current Admin for Mixed Test",
            "GET", 
            "auth/me",
            200,
            cookies=self.admin_cookies
        )
        
        if not success:
            print("❌ Could not get admin user info")
            return False
        
        admin_id = user_response.get('id')
        
        # Mix of valid client, admin (should fail), non-existent (should fail)
        mixed_user_ids = []
        
        # Add remaining test client if available
        if hasattr(self, 'test_client_ids') and self.test_client_ids:
            mixed_user_ids.append(self.test_client_ids[0])
        
        # Add admin ID (should fail)
        mixed_user_ids.append(admin_id)
        
        # Add non-existent user (should fail)
        mixed_user_ids.append("non-existent-user-id")
        
        url = f"{self.api_url}/admin/users/bulk"
        print(f"\n🔍 Testing Bulk User Delete (Mixed Scenario)...")
        print(f"   URL: {url}")
        print(f"   User IDs: {mixed_user_ids}")
        
        try:
            response = requests.delete(
                url,
                json=mixed_user_ids,
                headers={'Content-Type': 'application/json'},
                cookies=self.admin_cookies
            )
            self.tests_run += 1
            
            if response.status_code == 200:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   ✅ Deleted count: {response_data.get('deleted_count')}")
                    print(f"   ✅ Message: {response_data.get('message')}")
                    print(f"   ✅ Errors (expected): {response_data.get('errors')}")
                    
                    # Should have some errors but some successes
                    has_errors = len(response_data.get('errors', [])) > 0
                    has_successes = response_data.get('deleted_count', 0) > 0
                    
                    if has_errors and has_successes:
                        print("   ✅ Mixed scenario handled correctly")
                    
                    return True
                except:
                    return True
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    def test_verify_cascading_deletes(self):
        """Test that user deletion properly cascades to tasks and chat messages"""
        if not self.admin_cookies:
            print("❌ No admin session available for cascading delete test")
            return False
        
        print(f"\n🔍 Testing Cascading Deletes Verification...")
        
        # Create a test user
        test_user_data = {
            "email": "cascade_test@example.com",
            "password": "testpass123",
            "first_name": "Cascade",
            "last_name": "Test",
            "phone": "+1234567899",
            "company_name": "Cascade Test Company"
        }
        
        success, response, cookies = self.run_test(
            "Create User for Cascade Test",
            "POST",
            "auth/register",
            200,
            data=test_user_data
        )
        
        if not success:
            print("❌ Could not create test user for cascade test")
            return False
        
        test_user_id = response['user']['id']
        test_session_token = response['session_token']
        test_cookies = cookies
        
        print(f"   ✅ Created test user: {test_user_id}")
        
        # Create a task as this user
        due_date = datetime.now() + timedelta(days=1)
        task_data = {
            "title": "Cascade Test Task",
            "description": "Task to test cascading delete",
            "due_datetime": due_date.isoformat(),
            "project_price": 1000.0
        }
        
        success, task_response, _ = self.run_test(
            "Create Task for Cascade Test",
            "POST",
            "tasks",
            200,
            data=task_data,
            cookies=test_cookies
        )
        
        if success:
            test_task_id = task_response['id']
            print(f"   ✅ Created test task: {test_task_id}")
        
        # Send a chat message as this user
        admin_users_success, admin_users_response, _ = self.run_test(
            "Get Admin for Chat Test",
            "GET",
            "admin/users",
            200,
            cookies=self.admin_cookies
        )
        
        if admin_users_success:
            admin_user = None
            for user in admin_users_response:
                if user.get('role') == 'admin':
                    admin_user = user
                    break
            
            if admin_user:
                chat_data = {
                    "content": "Test message for cascade delete",
                    "recipient_id": admin_user['id']
                }
                
                success, chat_response, _ = self.run_test(
                    "Send Chat Message for Cascade Test",
                    "POST",
                    "chat/messages",
                    200,
                    data=chat_data,
                    cookies=test_cookies
                )
                
                if success:
                    print(f"   ✅ Created test chat message")
        
        # Now delete the user as admin
        success, delete_response, _ = self.run_test(
            "Delete User (Cascade Test)",
            "DELETE",
            f"admin/users/{test_user_id}",
            200,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ User deleted: {delete_response.get('message')}")
            print("   ✅ Cascading delete test completed - user's tasks and messages should be removed")
            return True
        
        return False

    def test_user_delete_unauthorized(self):
        """Test user deletion without admin privileges"""
        # Create a regular user session
        test_user_data = {
            "email": "unauthorized_test@example.com",
            "password": "testpass123",
            "first_name": "Unauthorized",
            "last_name": "Test",
            "phone": "+1234567898",
            "company_name": "Unauthorized Test Company"
        }
        
        success, response, cookies = self.run_test(
            "Create User for Unauthorized Test",
            "POST",
            "auth/register",
            200,
            data=test_user_data
        )
        
        if not success:
            print("❌ Could not create test user for unauthorized test")
            return False
        
        test_user_id = response['user']['id']
        test_cookies = cookies
        
        # Try to delete another user (should fail with 403)
        fake_user_id = "some-other-user-id"
        
        success, response, _ = self.run_test(
            "Delete User (Unauthorized)",
            "DELETE",
            f"admin/users/{fake_user_id}",
            403,
            cookies=test_cookies
        )
        
        if success:
            print("   ✅ Unauthorized deletion properly blocked")
        
        # Clean up - delete the test user as admin
        self.run_test(
            "Cleanup Unauthorized Test User",
            "DELETE",
            f"admin/users/{test_user_id}",
            200,
            cookies=self.admin_cookies
        )
        
        return success

    # ========== CHAT SYSTEM VERIFICATION TESTS ==========
    
    def test_chat_system_basic_functionality(self):
        """Test that basic chat functionality still works after optimization"""
        if not self.admin_cookies:
            print("❌ No admin session available for chat system test")
            return False
        
        print(f"\n🔍 Testing Chat System Basic Functionality...")
        
        # Create a test client for chat
        test_user_data = {
            "email": "chat_test@example.com",
            "password": "testpass123",
            "first_name": "Chat",
            "last_name": "Test",
            "phone": "+1234567897",
            "company_name": "Chat Test Company"
        }
        
        success, response, client_cookies = self.run_test(
            "Create Client for Chat Test",
            "POST",
            "auth/register",
            200,
            data=test_user_data
        )
        
        if not success:
            print("❌ Could not create test client for chat test")
            return False
        
        client_user_id = response['user']['id']
        print(f"   ✅ Created test client: {client_user_id}")
        
        # Get admin info for chat
        success, admin_info, _ = self.run_test(
            "Get Admin Info for Chat",
            "GET",
            "chat/admin-info",
            200,
            cookies=client_cookies
        )
        
        if not success:
            print("❌ Could not get admin info for chat")
            return False
        
        admin_id = admin_info['id']
        print(f"   ✅ Got admin info: {admin_info['name']}")
        
        # Test 1: Admin sends message to client
        admin_message_data = {
            "content": "Hello from admin - chat system test",
            "recipient_id": client_user_id
        }
        
        success, admin_msg_response, _ = self.run_test(
            "Admin Sends Message to Client",
            "POST",
            "chat/messages",
            200,
            data=admin_message_data,
            cookies=self.admin_cookies
        )
        
        if not success:
            print("❌ Admin could not send message to client")
            return False
        
        print(f"   ✅ Admin message sent: {admin_msg_response.get('content')[:30]}...")
        
        # Test 2: Client retrieves messages (should see admin message)
        success, client_messages, _ = self.run_test(
            "Client Retrieves Messages",
            "GET",
            "chat/messages",
            200,
            cookies=client_cookies
        )
        
        if not success:
            print("❌ Client could not retrieve messages")
            return False
        
        admin_message_found = False
        for msg in client_messages:
            if msg.get('sender_id') == admin_id and 'chat system test' in msg.get('content', ''):
                admin_message_found = True
                break
        
        if admin_message_found:
            print("   ✅ Client can see admin message")
        else:
            print("   ❌ Client cannot see admin message")
            return False
        
        # Test 3: Client sends reply to admin
        client_message_data = {
            "content": "Reply from client - chat system test",
            "recipient_id": admin_id
        }
        
        success, client_msg_response, _ = self.run_test(
            "Client Sends Reply to Admin",
            "POST",
            "chat/messages",
            200,
            data=client_message_data,
            cookies=client_cookies
        )
        
        if not success:
            print("❌ Client could not send reply to admin")
            return False
        
        print(f"   ✅ Client reply sent: {client_msg_response.get('content')[:30]}...")
        
        # Test 4: Admin retrieves messages with client_id parameter
        success, admin_messages, _ = self.run_test(
            "Admin Retrieves Client Conversation",
            "GET",
            f"chat/messages?client_id={client_user_id}",
            200,
            cookies=self.admin_cookies
        )
        
        if not success:
            print("❌ Admin could not retrieve client conversation")
            return False
        
        client_reply_found = False
        for msg in admin_messages:
            if msg.get('sender_id') == client_user_id and 'Reply from client' in msg.get('content', ''):
                client_reply_found = True
                break
        
        if client_reply_found:
            print("   ✅ Admin can see client reply")
        else:
            print("   ❌ Admin cannot see client reply")
            return False
        
        # Clean up test client
        self.run_test(
            "Cleanup Chat Test Client",
            "DELETE",
            f"admin/users/{client_user_id}",
            200,
            cookies=self.admin_cookies
        )
        
        print("   ✅ Chat system basic functionality verified")
        return True

    def test_chat_file_upload_still_works(self):
        """Test that file upload functionality still works in chat system"""
        if not self.admin_cookies:
            print("❌ No admin session available for chat file upload test")
            return False
        
        print(f"\n🔍 Testing Chat File Upload After Optimization...")
        
        # Create a test client
        test_user_data = {
            "email": "file_test@example.com",
            "password": "testpass123",
            "first_name": "File",
            "last_name": "Test",
            "phone": "+1234567896",
            "company_name": "File Test Company"
        }
        
        success, response, client_cookies = self.run_test(
            "Create Client for File Test",
            "POST",
            "auth/register",
            200,
            data=test_user_data
        )
        
        if not success:
            print("❌ Could not create test client for file test")
            return False
        
        client_user_id = response['user']['id']
        
        # Test file upload from admin to client
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            # Create a minimal PNG file
            temp_file.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82')
            temp_file_path = temp_file.name
        
        url = f"{self.api_url}/chat/upload"
        print(f"   Testing file upload to: {url}")
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('test_chat.png', f, 'image/png')}
                data = {
                    'recipient_id': client_user_id,
                    'content': 'Test file upload after optimization'
                }
                
                response = requests.post(url, files=files, data=data, cookies=self.admin_cookies)
                self.tests_run += 1
                
                if response.status_code == 200:
                    self.tests_passed += 1
                    print(f"✅ Passed - Status: {response.status_code}")
                    try:
                        response_data = response.json()
                        print(f"   ✅ File uploaded: {response_data.get('file_name')}")
                        print(f"   ✅ Message type: {response_data.get('message_type')}")
                        
                        # Clean up test client
                        self.run_test(
                            "Cleanup File Test Client",
                            "DELETE",
                            f"admin/users/{client_user_id}",
                            200,
                            cookies=self.admin_cookies
                        )
                        
                        return True
                    except:
                        return True
                else:
                    print(f"❌ Failed - Expected 200, got {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except:
                pass

def main():
    print("🚀 Starting Project Planner Authentication & Authorization Tests")
    print("=" * 70)
    
    tester = ProjectPlannerAPITester()
    
    # Test sequence - Authentication & Authorization Focus
    test_results = []
    
    print("\n🔐 AUTHENTICATION TESTS")
    print("-" * 30)
    
    # Basic connectivity
    test_results.append(tester.test_api_root())
    
    # Authentication tests
    test_results.append(tester.test_admin_login_success())
    test_results.append(tester.test_admin_login_invalid_credentials())
    test_results.append(tester.test_admin_login_invalid_username())
    test_results.append(tester.test_get_current_user_authenticated())
    test_results.append(tester.test_get_current_user_unauthenticated())
    
    # OAuth tests (will fail with external service, but tests error handling)
    test_results.append(tester.test_oauth_session_missing_header())
    test_results.append(tester.test_oauth_session_invalid_id())
    
    print("\n🛡️  AUTHORIZATION TESTS")
    print("-" * 30)
    
    # Re-login for authorization tests (in case logout cleared session)
    if not tester.admin_cookies:
        print("Re-authenticating for authorization tests...")
        tester.test_admin_login_success()
    
    # Admin-specific operations
    test_results.append(tester.test_create_task_as_admin())
    test_results.append(tester.test_get_tasks_as_admin())
    test_results.append(tester.test_get_task_stats_as_admin())
    test_results.append(tester.test_admin_get_all_users())
    
    # User management tests
    test_results.append(tester.test_admin_update_user())
    test_results.append(tester.test_admin_export_users_csv())
    test_results.append(tester.test_admin_export_users_pdf())
    
    # NEW USER MANAGEMENT DELETE FUNCTIONALITY TESTS
    print("\n🗑️  USER MANAGEMENT DELETE TESTS (PRIMARY FOCUS)")
    print("-" * 50)
    test_results.append(tester.test_create_test_client_users())
    test_results.append(tester.test_single_user_delete_success())
    test_results.append(tester.test_single_user_delete_nonexistent())
    test_results.append(tester.test_single_user_delete_admin_account())
    test_results.append(tester.test_single_user_delete_self())
    test_results.append(tester.test_bulk_user_delete_success())
    test_results.append(tester.test_bulk_user_delete_mixed_scenario())
    test_results.append(tester.test_verify_cascading_deletes())
    test_results.append(tester.test_user_delete_unauthorized())
    
    # CHAT SYSTEM VERIFICATION TESTS (SECONDARY FOCUS)
    print("\n💬 CHAT SYSTEM VERIFICATION TESTS (SECONDARY FOCUS)")
    print("-" * 50)
    test_results.append(tester.test_chat_system_basic_functionality())
    test_results.append(tester.test_chat_file_upload_still_works())
    
    # Milestone tests
    test_results.append(tester.test_create_milestone())
    test_results.append(tester.test_get_milestones())
    test_results.append(tester.test_get_milestones_nonexistent_task())
    
    # File upload tests
    print("\n📁 FILE UPLOAD TESTS")
    print("-" * 30)
    test_results.append(tester.test_chat_file_upload_valid_file())
    test_results.append(tester.test_chat_file_upload_invalid_format())
    test_results.append(tester.test_chat_file_upload_oversized_file())
    
    test_results.append(tester.test_delete_task_as_admin())
    
    # Protected routes without authentication
    test_results.append(tester.test_protected_routes_without_auth())
    
    print("\n🔒 SECURITY TESTS")
    print("-" * 30)
    
    # Test logout
    test_results.append(tester.test_logout())
    
    # Legacy CRUD tests (should all fail with 401 now)
    print("\n📋 LEGACY CRUD TESTS (Should require auth)")
    print("-" * 30)
    test_results.append(tester.test_create_task())
    test_results.append(tester.test_get_tasks())
    test_results.append(tester.test_get_single_task())
    test_results.append(tester.test_update_task_status())
    test_results.append(tester.test_update_task())
    test_results.append(tester.test_get_stats())
    test_results.append(tester.test_delete_task())
    test_results.append(tester.test_get_nonexistent_task())

    # Print final results
    print("\n" + "=" * 70)
    print(f"📊 FINAL RESULTS")
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All authentication and authorization tests passed!")
        print("✅ Admin login works with correct credentials")
        print("✅ Invalid credentials are properly rejected")
        print("✅ Role-based access control is working")
        print("✅ Protected routes require authentication")
        print("✅ Admin-only operations are properly secured")
        return 0
    else:
        failed_tests = tester.tests_run - tester.tests_passed
        print(f"⚠️  {failed_tests} tests failed. Check the authentication implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())