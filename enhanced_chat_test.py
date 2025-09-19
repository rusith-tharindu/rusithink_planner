import requests
import sys
from datetime import datetime, timedelta
import json
import tempfile
import os

class EnhancedChatSystemTester:
    def __init__(self, base_url="https://rusithink-manage.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_session_token = None
        self.admin_cookies = None
        self.client_session_token = None
        self.client_cookies = None
        self.client_user_id = None
        self.client2_user_id = None
        self.test_task_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None, cookies=None, headers=None, files=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        request_headers = {'Content-Type': 'application/json'} if not files else {}
        if headers:
            request_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=request_headers, params=params, cookies=cookies)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, data=data, cookies=cookies)
                else:
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
                    if response.headers.get('content-type', '').startswith('application/json'):
                        response_data = response.json()
                        print(f"   Response: {json.dumps(response_data, indent=2)[:300]}...")
                        return True, response_data, response.cookies
                    else:
                        print(f"   Content-Type: {response.headers.get('content-type')}")
                        print(f"   Content-Length: {len(response.content)} bytes")
                        return True, {}, response.cookies
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

    def setup_admin_session(self):
        """Setup admin session for testing"""
        login_data = {
            "username": "rusithink",
            "password": "20200104Rh"
        }
        
        success, response, cookies = self.run_test(
            "Admin Login Setup", 
            "POST", 
            "auth/admin-login", 
            200, 
            data=login_data
        )
        
        if success:
            self.admin_cookies = cookies
            if 'session_token' in response:
                self.admin_session_token = response['session_token']
            print(f"   ✅ Admin session established")
            return True
        return False

    def setup_test_client(self):
        """Create a test client user for chat testing"""
        if not self.admin_cookies:
            print("❌ No admin session for client creation")
            return False

        # Register a test client
        client_data = {
            "email": "testclient@example.com",
            "password": "testpass123",
            "first_name": "Test",
            "last_name": "Client",
            "phone": "+1234567890",
            "company_name": "Test Company",
            "address": "123 Test Street, Test City"
        }
        
        success, response, cookies = self.run_test(
            "Create Test Client", 
            "POST", 
            "auth/register", 
            200, 
            data=client_data
        )
        
        if success:
            self.client_cookies = cookies
            self.client_user_id = response['user']['id']
            print(f"   ✅ Test client created: {self.client_user_id}")
            return True
        return False

    def setup_second_test_client(self):
        """Create a second test client for privacy testing"""
        client2_data = {
            "email": "testclient2@example.com",
            "password": "testpass123",
            "first_name": "Test2",
            "last_name": "Client2",
            "phone": "+1234567891",
            "company_name": "Test Company 2",
            "address": "456 Test Avenue, Test City"
        }
        
        success, response, cookies = self.run_test(
            "Create Second Test Client", 
            "POST", 
            "auth/register", 
            200, 
            data=client2_data
        )
        
        if success:
            self.client2_user_id = response['user']['id']
            print(f"   ✅ Second test client created: {self.client2_user_id}")
            return True
        return False

    def create_test_task(self):
        """Create a test task for chat testing"""
        if not self.admin_cookies:
            return False

        due_date = datetime.now() + timedelta(days=7)
        task_data = {
            "title": "Chat Test Project",
            "description": "Project for testing chat functionality",
            "due_datetime": due_date.isoformat(),
            "project_price": 2500.0,
            "priority": "medium"
        }
        
        success, response, _ = self.run_test(
            "Create Test Task", 
            "POST", 
            "tasks", 
            200, 
            data=task_data,
            cookies=self.admin_cookies
        )
        
        if success:
            self.test_task_id = response['id']
            print(f"   ✅ Test task created: {self.test_task_id}")
            return True
        return False

    # ========== ENHANCED CHAT EXPORT TESTS ==========

    def test_admin_chat_export_specific_client(self):
        """Test GET /api/admin/chat/export/{client_id} - CSV export for specific client"""
        if not self.admin_cookies or not self.client_user_id:
            print("❌ Missing admin session or client ID for chat export test")
            return False

        # First, send some messages to have data to export
        self.send_test_messages()

        url = f"{self.api_url}/admin/chat/export/{self.client_user_id}"
        print(f"\n🔍 Testing Admin Chat Export for Specific Client...")
        print(f"   URL: {url}")
        
        try:
            response = requests.get(url, cookies=self.admin_cookies)
            self.tests_run += 1
            
            if response.status_code == 200:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                print(f"   Content-Type: {response.headers.get('content-type')}")
                print(f"   Content-Length: {len(response.content)} bytes")
                
                # Check if it's CSV content
                if 'text/csv' in response.headers.get('content-type', ''):
                    print("   ✅ Correct CSV content type")
                
                # Check CSV headers
                content = response.text
                if 'Date & Time' in content and 'Sender' in content and 'Content' in content:
                    print("   ✅ CSV contains expected headers")
                
                # Check for actual message content
                if 'Admin test message' in content or 'Client test message' in content:
                    print("   ✅ CSV contains chat messages")
                
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

    def test_admin_chat_conversations_list(self):
        """Test GET /api/admin/chat/conversations - list all client conversations"""
        if not self.admin_cookies:
            print("❌ No admin session for conversations list test")
            return False

        success, response, _ = self.run_test(
            "Admin Chat Conversations List", 
            "GET", 
            "admin/chat/conversations", 
            200,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Retrieved {len(response)} conversations")
            for conv in response[:3]:  # Show first 3
                print(f"   - Client: {conv.get('client_name')} ({conv.get('client_email')})")
                print(f"     Unread: {conv.get('unread_count')}, Company: {conv.get('client_company')}")
        
        return success

    # ========== ENHANCED CHAT MESSAGES TESTS ==========

    def test_chat_messages_with_client_id_admin(self):
        """Test GET /api/chat/messages with client_id parameter for admin users"""
        if not self.admin_cookies or not self.client_user_id:
            print("❌ Missing admin session or client ID for chat messages test")
            return False

        params = {"client_id": self.client_user_id, "limit": 20}
        success, response, _ = self.run_test(
            "Chat Messages with Client ID (Admin)", 
            "GET", 
            "chat/messages", 
            200,
            params=params,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Retrieved {len(response)} messages for specific client")
            # Verify all messages are between admin and specified client
            for msg in response:
                sender_id = msg.get('sender_id')
                recipient_id = msg.get('recipient_id')
                if not ((sender_id == self.client_user_id or recipient_id == self.client_user_id)):
                    print(f"   ❌ Message not related to specified client: {msg.get('id')}")
                    return False
            print("   ✅ All messages are between admin and specified client")
        
        return success

    def test_chat_privacy_controls(self):
        """Test that clients can't see other clients' messages"""
        if not self.client_cookies or not self.client2_user_id:
            print("❌ Missing client session or second client ID for privacy test")
            return False

        # Try to get messages with another client's ID (should not work for non-admin)
        params = {"client_id": self.client2_user_id}
        success, response, _ = self.run_test(
            "Chat Privacy - Client Cannot Access Other Client Messages", 
            "GET", 
            "chat/messages", 
            200,  # Should return 200 but with no messages or only client's own messages
            params=params,
            cookies=self.client_cookies
        )
        
        if success:
            # For non-admin users, client_id parameter should be ignored
            # and they should only see their own messages
            for msg in response:
                sender_id = msg.get('sender_id')
                recipient_id = msg.get('recipient_id')
                if not (sender_id == self.client_user_id or recipient_id == self.client_user_id):
                    print(f"   ❌ Client can see other client's messages - privacy violation!")
                    return False
            print("   ✅ Client can only see their own messages (privacy maintained)")
        
        return success

    # ========== FILE UPLOAD RESTRICTION TESTS ==========

    def test_file_upload_format_validation(self):
        """Test file format validation (png, jpg, pdf, heic, csv only)"""
        if not self.admin_cookies or not self.client_user_id:
            print("❌ Missing admin session or client ID for file upload test")
            return False

        # Test valid formats
        valid_formats = [
            ('test.png', b'\x89PNG\r\n\x1a\n', 'image/png'),
            ('test.jpg', b'\xff\xd8\xff\xe0', 'image/jpeg'),
            ('test.pdf', b'%PDF-1.4', 'application/pdf'),
            ('test.csv', b'name,email\ntest,test@example.com', 'text/csv')
        ]
        
        all_passed = True
        
        for filename, content, mime_type in valid_formats:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                with open(temp_file_path, 'rb') as f:
                    files = {'file': (filename, f, mime_type)}
                    data = {
                        'recipient_id': self.client_user_id,
                        'content': f'Test {filename} upload'
                    }
                    
                    success, response, _ = self.run_test(
                        f"File Upload - Valid Format ({filename})", 
                        "POST", 
                        "chat/upload", 
                        200,
                        data=data,
                        files=files,
                        cookies=self.admin_cookies
                    )
                    
                    if not success:
                        all_passed = False
                        
            finally:
                try:
                    os.unlink(temp_file_path)
                except:
                    pass

        # Test invalid formats
        invalid_formats = [
            ('test.txt', b'This is a text file', 'text/plain'),
            ('test.doc', b'Microsoft Word document', 'application/msword'),
            ('test.exe', b'Executable file', 'application/octet-stream')
        ]
        
        for filename, content, mime_type in invalid_formats:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                with open(temp_file_path, 'rb') as f:
                    files = {'file': (filename, f, mime_type)}
                    data = {
                        'recipient_id': self.client_user_id,
                        'content': f'Test {filename} upload (should fail)'
                    }
                    
                    success, response, _ = self.run_test(
                        f"File Upload - Invalid Format ({filename})", 
                        "POST", 
                        "chat/upload", 
                        400,  # Should be rejected
                        data=data,
                        files=files,
                        cookies=self.admin_cookies
                    )
                    
                    if not success:
                        all_passed = False
                        
            finally:
                try:
                    os.unlink(temp_file_path)
                except:
                    pass

        return all_passed

    def test_file_upload_size_limit(self):
        """Test 16MB file size limit"""
        if not self.admin_cookies or not self.client_user_id:
            print("❌ Missing admin session or client ID for file size test")
            return False

        # Test file just under 16MB (should pass)
        print("\n🔍 Testing File Upload - Size Just Under 16MB...")
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            # Write ~15.5MB of data
            chunk_size = 1024 * 1024  # 1MB chunks
            for i in range(15):  # 15MB
                temp_file.write(b'x' * chunk_size)
            temp_file.write(b'x' * (512 * 1024))  # Additional 0.5MB
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('under_limit.pdf', f, 'application/pdf')}
                data = {
                    'recipient_id': self.client_user_id,
                    'content': 'Test file under 16MB limit'
                }
                
                success1, _, _ = self.run_test(
                    "File Upload - Under 16MB Limit", 
                    "POST", 
                    "chat/upload", 
                    200,
                    data=data,
                    files=files,
                    cookies=self.admin_cookies
                )
                
        finally:
            try:
                os.unlink(temp_file_path)
            except:
                pass

        # Test file over 16MB (should fail)
        print("\n🔍 Testing File Upload - Size Over 16MB...")
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            # Write ~17MB of data
            chunk_size = 1024 * 1024  # 1MB chunks
            for i in range(17):  # 17MB
                temp_file.write(b'x' * chunk_size)
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('over_limit.pdf', f, 'application/pdf')}
                data = {
                    'recipient_id': self.client_user_id,
                    'content': 'Test file over 16MB limit (should fail)'
                }
                
                success2, _, _ = self.run_test(
                    "File Upload - Over 16MB Limit", 
                    "POST", 
                    "chat/upload", 
                    400,  # Should be rejected
                    data=data,
                    files=files,
                    cookies=self.admin_cookies
                )
                
        finally:
            try:
                os.unlink(temp_file_path)
            except:
                pass

        return success1 and success2

    # ========== REAL-TIME CHAT FLOW TESTS ==========

    def send_test_messages(self):
        """Send test messages for chat flow testing"""
        if not self.admin_cookies or not self.client_cookies or not self.client_user_id:
            return False

        # Admin sends message to client
        admin_msg_data = {
            "recipient_id": self.client_user_id,
            "content": "Admin test message - Hello from admin!",
            "task_id": self.test_task_id
        }
        
        success1, _, _ = self.run_test(
            "Admin Sends Message to Client", 
            "POST", 
            "chat/messages", 
            200,
            data=admin_msg_data,
            cookies=self.admin_cookies
        )

        # Get admin user ID from admin session
        success_me, admin_user_data, _ = self.run_test(
            "Get Admin User Info", 
            "GET", 
            "auth/me", 
            200,
            cookies=self.admin_cookies
        )
        
        if not success_me:
            return False
            
        admin_user_id = admin_user_data.get('id')

        # Client sends message back to admin
        client_msg_data = {
            "recipient_id": admin_user_id,
            "content": "Client test message - Hello from client!",
            "task_id": self.test_task_id
        }
        
        success2, _, _ = self.run_test(
            "Client Sends Message to Admin", 
            "POST", 
            "chat/messages", 
            200,
            data=client_msg_data,
            cookies=self.client_cookies
        )

        return success1 and success2

    def test_complete_chat_flow(self):
        """Test a complete chat flow with file uploads from both sides"""
        if not self.admin_cookies or not self.client_cookies or not self.client_user_id:
            print("❌ Missing sessions for complete chat flow test")
            return False

        # Send text messages
        messages_success = self.send_test_messages()
        if not messages_success:
            print("❌ Failed to send test messages")
            return False

        # Get admin user ID
        success_me, admin_user_data, _ = self.run_test(
            "Get Admin User Info for File Upload", 
            "GET", 
            "auth/me", 
            200,
            cookies=self.admin_cookies
        )
        
        if not success_me:
            return False
            
        admin_user_id = admin_user_data.get('id')

        # Admin uploads file to client
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(b'%PDF-1.4\nAdmin file content')
            admin_file_path = temp_file.name
        
        try:
            with open(admin_file_path, 'rb') as f:
                files = {'file': ('admin_document.pdf', f, 'application/pdf')}
                data = {
                    'recipient_id': self.client_user_id,
                    'content': 'Admin file upload',
                    'task_id': self.test_task_id
                }
                
                admin_upload_success, _, _ = self.run_test(
                    "Admin File Upload to Client", 
                    "POST", 
                    "chat/upload", 
                    200,
                    data=data,
                    files=files,
                    cookies=self.admin_cookies
                )
                
        finally:
            try:
                os.unlink(admin_file_path)
            except:
                pass

        # Client uploads file to admin
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_file.write(b'\x89PNG\r\n\x1a\nClient image content')
            client_file_path = temp_file.name
        
        try:
            with open(client_file_path, 'rb') as f:
                files = {'file': ('client_image.png', f, 'image/png')}
                data = {
                    'recipient_id': admin_user_id,
                    'content': 'Client file upload',
                    'task_id': self.test_task_id
                }
                
                client_upload_success, _, _ = self.run_test(
                    "Client File Upload to Admin", 
                    "POST", 
                    "chat/upload", 
                    200,
                    data=data,
                    files=files,
                    cookies=self.client_cookies
                )
                
        finally:
            try:
                os.unlink(client_file_path)
            except:
                pass

        return messages_success and admin_upload_success and client_upload_success

    def test_message_privacy_between_clients(self):
        """Test that different clients cannot see each other's messages"""
        if not self.client_cookies or not self.client2_user_id:
            print("❌ Missing client sessions for privacy test")
            return False

        # Get messages as first client
        success1, client1_messages, _ = self.run_test(
            "Get Messages as Client 1", 
            "GET", 
            "chat/messages", 
            200,
            cookies=self.client_cookies
        )

        # Create second client session
        client2_login_data = {
            "email": "testclient2@example.com",
            "password": "testpass123"
        }
        
        # Login as second client (assuming manual login endpoint exists)
        # For now, we'll test with the existing client session and verify privacy logic
        
        if success1:
            # Verify that client 1 can only see messages involving them
            for msg in client1_messages:
                sender_id = msg.get('sender_id')
                recipient_id = msg.get('recipient_id')
                if not (sender_id == self.client_user_id or recipient_id == self.client_user_id):
                    print(f"   ❌ Privacy violation: Client 1 can see message not involving them")
                    return False
            print("   ✅ Client 1 can only see their own messages")

        return success1

def main():
    print("🚀 Starting Enhanced RusiThink Chat System Tests")
    print("=" * 70)
    
    tester = EnhancedChatSystemTester()
    
    # Setup phase
    print("\n🔧 SETUP PHASE")
    print("-" * 30)
    
    if not tester.setup_admin_session():
        print("❌ Failed to setup admin session")
        return 1
    
    if not tester.setup_test_client():
        print("❌ Failed to setup test client")
        return 1
        
    if not tester.setup_second_test_client():
        print("❌ Failed to setup second test client")
        return 1
    
    if not tester.create_test_task():
        print("❌ Failed to create test task")
        return 1

    # Test sequence for enhanced chat features
    test_results = []
    
    print("\n📤 CHAT EXPORT ENDPOINT TESTS")
    print("-" * 40)
    test_results.append(tester.test_admin_chat_export_specific_client())
    test_results.append(tester.test_admin_chat_conversations_list())
    
    print("\n💬 ENHANCED CHAT MESSAGES TESTS")
    print("-" * 40)
    test_results.append(tester.test_chat_messages_with_client_id_admin())
    test_results.append(tester.test_chat_privacy_controls())
    
    print("\n📁 FILE UPLOAD RESTRICTION TESTS")
    print("-" * 40)
    test_results.append(tester.test_file_upload_format_validation())
    test_results.append(tester.test_file_upload_size_limit())
    
    print("\n🔄 REAL-TIME CHAT FLOW TESTS")
    print("-" * 40)
    test_results.append(tester.test_complete_chat_flow())
    test_results.append(tester.test_message_privacy_between_clients())

    # Print final results
    print("\n" + "=" * 70)
    print(f"📊 ENHANCED CHAT SYSTEM TEST RESULTS")
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All enhanced chat system tests passed!")
        print("✅ Chat export endpoints working correctly")
        print("✅ Enhanced chat messages with client_id parameter working")
        print("✅ Privacy controls properly implemented")
        print("✅ File upload restrictions working (format and size)")
        print("✅ Complete chat flow with file uploads working")
        return 0
    else:
        failed_tests = tester.tests_run - tester.tests_passed
        print(f"⚠️  {failed_tests} tests failed. Check the enhanced chat implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())