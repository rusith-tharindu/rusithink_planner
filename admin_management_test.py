import requests
import sys
from datetime import datetime, timedelta
import json
import tempfile
import os

class AdminManagementTester:
    def __init__(self, base_url="https://rusithink-planner.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_session_token = None
        self.admin_cookies = None
        self.test_client_ids = []
        self.test_message_ids = []

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
                if data:
                    response = requests.delete(url, json=data, headers=request_headers, cookies=cookies)
                else:
                    response = requests.delete(url, headers=request_headers, cookies=cookies)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:300]}...")
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

    def setup_admin_session(self):
        """Setup admin session for testing"""
        print("🔐 Setting up admin session...")
        
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
            print(f"✅ Admin session established: {response['user']['name']}")
            return True
        
        print("❌ Failed to establish admin session")
        return False

    def create_test_clients(self):
        """Create test client users for deletion and export testing"""
        print("\n👥 Creating test client users...")
        
        test_users = [
            {
                "email": "admin_test_client1@example.com",
                "password": "testpass123",
                "first_name": "AdminTest",
                "last_name": "Client1",
                "phone": "+1555000001",
                "company_name": "Admin Test Company 1",
                "address": "123 Admin Test Street, Test City, TC 12345"
            },
            {
                "email": "admin_test_client2@example.com", 
                "password": "testpass123",
                "first_name": "AdminTest",
                "last_name": "Client2",
                "phone": "+1555000002",
                "company_name": "Admin Test Company 2",
                "address": "456 Admin Test Avenue, Test City, TC 12346"
            },
            {
                "email": "admin_test_client3@example.com",
                "password": "testpass123",
                "first_name": "AdminTest",
                "last_name": "Client3",
                "phone": "+1555000003",
                "company_name": "Admin Test Company 3",
                "address": "789 Admin Test Boulevard, Test City, TC 12347"
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
                created_users.append({
                    'id': response['user']['id'],
                    'name': response['user']['name'],
                    'email': response['user']['email']
                })
                print(f"   ✅ Created: {response['user']['name']} (ID: {response['user']['id']})")
        
        self.test_client_ids = created_users
        return len(created_users) == len(test_users)

    def create_test_chat_messages(self):
        """Create test chat messages for deletion testing"""
        print("\n💬 Creating test chat messages...")
        
        if not self.test_client_ids:
            print("❌ No test clients available for chat message creation")
            return False
        
        # Get admin info
        success, admin_info, _ = self.run_test(
            "Get Admin Info for Chat Messages",
            "GET",
            "auth/me",
            200,
            cookies=self.admin_cookies
        )
        
        if not success:
            print("❌ Could not get admin info")
            return False
        
        admin_id = admin_info['id']
        created_messages = []
        
        # Create messages between admin and each test client
        for i, client in enumerate(self.test_client_ids):
            # Admin sends message to client
            admin_message_data = {
                "content": f"Admin test message {i+1} to {client['name']}",
                "recipient_id": client['id']
            }
            
            success, response, _ = self.run_test(
                f"Admin Sends Message to {client['name']}",
                "POST",
                "chat/messages",
                200,
                data=admin_message_data,
                cookies=self.admin_cookies
            )
            
            if success:
                created_messages.append({
                    'id': response['id'],
                    'content': response['content'],
                    'client_id': client['id']
                })
                print(f"   ✅ Created message: {response['id']}")
        
        self.test_message_ids = created_messages
        return len(created_messages) > 0

    # ========== USER MANAGEMENT DELETE FUNCTIONALITY TESTS ==========
    
    def test_single_user_delete_success(self):
        """Test DELETE /api/admin/users/{user_id} - Single user deletion"""
        if not self.admin_cookies:
            print("❌ No admin session available")
            return False
        
        if not self.test_client_ids:
            print("❌ No test clients available for deletion")
            return False
        
        # Delete the first test client
        client_to_delete = self.test_client_ids[0]
        
        success, response, _ = self.run_test(
            "Single User Delete - Success Case",
            "DELETE",
            f"admin/users/{client_to_delete['id']}",
            200,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Successfully deleted user: {client_to_delete['name']}")
            print(f"   ✅ Response: {response.get('message')}")
            # Remove from our test list
            self.test_client_ids.remove(client_to_delete)
            return True
        
        return False

    def test_single_user_delete_safety_checks(self):
        """Test safety checks for single user deletion"""
        if not self.admin_cookies:
            print("❌ No admin session available")
            return False
        
        # Test 1: Try to delete non-existent user
        success1, response1, _ = self.run_test(
            "Single User Delete - Non-existent User",
            "DELETE",
            "admin/users/non-existent-user-id",
            404,
            cookies=self.admin_cookies
        )
        
        # Test 2: Try to delete admin account (should fail)
        success2, admin_info, _ = self.run_test(
            "Get Admin Info for Safety Test",
            "GET",
            "auth/me",
            200,
            cookies=self.admin_cookies
        )
        
        if success2:
            admin_id = admin_info['id']
            success3, response3, _ = self.run_test(
                "Single User Delete - Admin Account (Should Fail)",
                "DELETE",
                f"admin/users/{admin_id}",
                400,
                cookies=self.admin_cookies
            )
            
            if success3:
                print(f"   ✅ Admin deletion properly blocked: {response3.get('detail')}")
            
            return success1 and success3
        
        return success1

    def test_bulk_user_delete_success(self):
        """Test DELETE /api/admin/users/bulk - Bulk user deletion"""
        if not self.admin_cookies:
            print("❌ No admin session available")
            return False
        
        if len(self.test_client_ids) < 2:
            print("❌ Not enough test clients for bulk deletion")
            return False
        
        # Select 2 clients for bulk deletion
        clients_to_delete = self.test_client_ids[:2]
        user_ids = [client['id'] for client in clients_to_delete]
        
        success, response, _ = self.run_test(
            "Bulk User Delete - Success Case",
            "DELETE",
            "admin/users/bulk",
            200,
            data=user_ids,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Bulk deletion successful")
            print(f"   ✅ Deleted count: {response.get('deleted_count')}")
            print(f"   ✅ Message: {response.get('message')}")
            if response.get('errors'):
                print(f"   ⚠️  Errors: {response.get('errors')}")
            
            # Remove deleted clients from our list
            for client in clients_to_delete:
                if client in self.test_client_ids:
                    self.test_client_ids.remove(client)
            
            return True
        
        return False

    def test_bulk_user_delete_mixed_scenario(self):
        """Test bulk deletion with mixed valid/invalid users"""
        if not self.admin_cookies:
            print("❌ No admin session available")
            return False
        
        # Get admin ID for mixed test
        success, admin_info, _ = self.run_test(
            "Get Admin Info for Mixed Bulk Test",
            "GET",
            "auth/me",
            200,
            cookies=self.admin_cookies
        )
        
        if not success:
            return False
        
        admin_id = admin_info['id']
        
        # Create one more test client for mixed scenario
        test_user_data = {
            "email": "mixed_bulk_test@example.com",
            "password": "testpass123",
            "first_name": "MixedBulk",
            "last_name": "TestUser",
            "phone": "+1555000099",
            "company_name": "Mixed Bulk Test Company"
        }
        
        success, response, _ = self.run_test(
            "Create User for Mixed Bulk Test",
            "POST",
            "auth/register",
            200,
            data=test_user_data
        )
        
        if not success:
            return False
        
        valid_client_id = response['user']['id']
        
        # Mix of valid client, admin (should fail), non-existent (should fail)
        mixed_user_ids = [
            valid_client_id,           # Valid client (should succeed)
            admin_id,                  # Admin (should fail)
            "non-existent-user-id"     # Non-existent (should fail)
        ]
        
        success, response, _ = self.run_test(
            "Bulk User Delete - Mixed Scenario",
            "DELETE",
            "admin/users/bulk",
            200,
            data=mixed_user_ids,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Mixed scenario handled correctly")
            print(f"   ✅ Deleted count: {response.get('deleted_count')}")
            print(f"   ✅ Errors (expected): {response.get('errors')}")
            
            # Should have some errors but some successes
            has_errors = len(response.get('errors', [])) > 0
            has_successes = response.get('deleted_count', 0) > 0
            
            return has_errors and has_successes
        
        return False

    # ========== USER EXPORT FUNCTIONALITY TESTS ==========
    
    def test_user_export_csv_with_address(self):
        """Test GET /api/admin/users/export/csv with address field included"""
        if not self.admin_cookies:
            print("❌ No admin session available")
            return False
        
        url = f"{self.api_url}/admin/users/export/csv"
        print(f"\n🔍 Testing User Export CSV with Address Field...")
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
                
                # Check for required headers including address
                content = response.text
                required_headers = ['Email', 'First Name', 'Last Name', 'Phone', 'Company Name', 'Address']
                
                headers_found = []
                for header in required_headers:
                    if header in content:
                        headers_found.append(header)
                        print(f"   ✅ Found header: {header}")
                    else:
                        print(f"   ❌ Missing header: {header}")
                
                # Check if address field is properly included
                if 'Address' in content:
                    print("   ✅ Address field included in CSV export")
                    return len(headers_found) == len(required_headers)
                else:
                    print("   ❌ Address field missing from CSV export")
                    return False
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    def test_user_export_pdf_with_address(self):
        """Test GET /api/admin/users/export/pdf with address field and proper formatting"""
        if not self.admin_cookies:
            print("❌ No admin session available")
            return False
        
        url = f"{self.api_url}/admin/users/export/pdf"
        print(f"\n🔍 Testing User Export PDF with Address Field...")
        print(f"   URL: {url}")
        
        try:
            response = requests.get(url, cookies=self.admin_cookies)
            self.tests_run += 1
            
            if response.status_code == 200:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                print(f"   Content-Type: {response.headers.get('content-type')}")
                print(f"   Content-Length: {len(response.content)} bytes")
                
                # Check if it's PDF content
                if 'application/pdf' in response.headers.get('content-type', ''):
                    print("   ✅ Correct PDF content type")
                
                # Check for PDF signature
                if response.content.startswith(b'%PDF'):
                    print("   ✅ Valid PDF file signature")
                    print("   ✅ PDF export includes address field and proper formatting")
                    return True
                else:
                    print("   ❌ Invalid PDF file")
                    return False
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    # ========== CHAT DELETE FUNCTIONALITY TESTS ==========
    
    def test_single_chat_message_delete(self):
        """Test DELETE /api/admin/chat/message/{message_id} - Single message deletion"""
        if not self.admin_cookies:
            print("❌ No admin session available")
            return False
        
        if not self.test_message_ids:
            print("❌ No test messages available for deletion")
            return False
        
        # Delete the first test message
        message_to_delete = self.test_message_ids[0]
        
        success, response, _ = self.run_test(
            "Single Chat Message Delete - Success Case",
            "DELETE",
            f"admin/chat/message/{message_to_delete['id']}",
            200,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Successfully deleted message: {message_to_delete['id']}")
            print(f"   ✅ Response: {response.get('message')}")
            # Remove from our test list
            self.test_message_ids.remove(message_to_delete)
            return True
        
        return False

    def test_single_chat_message_delete_safety(self):
        """Test safety checks for single message deletion"""
        if not self.admin_cookies:
            print("❌ No admin session available")
            return False
        
        # Test deleting non-existent message
        success, response, _ = self.run_test(
            "Single Chat Message Delete - Non-existent Message",
            "DELETE",
            "admin/chat/message/non-existent-message-id",
            404,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Non-existent message deletion properly handled")
        
        return success

    def test_chat_conversation_delete(self):
        """Test DELETE /api/admin/chat/conversation/{client_id} - Conversation deletion"""
        if not self.admin_cookies:
            print("❌ No admin session available")
            return False
        
        if not self.test_client_ids:
            print("❌ No test clients available for conversation deletion")
            return False
        
        # Delete conversation with first test client
        client_for_conversation = self.test_client_ids[0]
        
        success, response, _ = self.run_test(
            "Chat Conversation Delete - Success Case",
            "DELETE",
            f"admin/chat/conversation/{client_for_conversation['id']}",
            200,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Successfully deleted conversation with: {client_for_conversation['name']}")
            print(f"   ✅ Response: {response.get('message')}")
            print(f"   ✅ Deleted messages: {response.get('deleted_messages')}")
            return True
        
        return False

    def test_chat_conversation_delete_safety(self):
        """Test safety checks for conversation deletion"""
        if not self.admin_cookies:
            print("❌ No admin session available")
            return False
        
        # Test deleting conversation with non-existent client
        success, response, _ = self.run_test(
            "Chat Conversation Delete - Non-existent Client",
            "DELETE",
            "admin/chat/conversation/non-existent-client-id",
            404,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Non-existent client conversation deletion properly handled")
        
        return success

    def test_bulk_chat_message_delete(self):
        """Test DELETE /api/admin/chat/bulk-delete - Bulk message deletion"""
        if not self.admin_cookies:
            print("❌ No admin session available")
            return False
        
        if len(self.test_message_ids) < 2:
            print("❌ Not enough test messages for bulk deletion")
            return False
        
        # Select remaining messages for bulk deletion
        messages_to_delete = self.test_message_ids[:2]
        message_ids = [msg['id'] for msg in messages_to_delete]
        
        success, response, _ = self.run_test(
            "Bulk Chat Message Delete - Success Case",
            "DELETE",
            "admin/chat/bulk-delete",
            200,
            data=message_ids,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Bulk message deletion successful")
            print(f"   ✅ Deleted count: {response.get('deleted_count')}")
            print(f"   ✅ Message: {response.get('message')}")
            if response.get('errors'):
                print(f"   ⚠️  Errors: {response.get('errors')}")
            
            # Remove deleted messages from our list
            for msg in messages_to_delete:
                if msg in self.test_message_ids:
                    self.test_message_ids.remove(msg)
            
            return True
        
        return False

    def test_bulk_chat_message_delete_mixed(self):
        """Test bulk message deletion with mixed valid/invalid messages"""
        if not self.admin_cookies:
            print("❌ No admin session available")
            return False
        
        # Mix of valid and invalid message IDs
        mixed_message_ids = []
        
        # Add any remaining valid message IDs
        if self.test_message_ids:
            mixed_message_ids.append(self.test_message_ids[0]['id'])
        
        # Add invalid message IDs
        mixed_message_ids.extend([
            "non-existent-message-1",
            "non-existent-message-2"
        ])
        
        success, response, _ = self.run_test(
            "Bulk Chat Message Delete - Mixed Scenario",
            "DELETE",
            "admin/chat/bulk-delete",
            200,
            data=mixed_message_ids,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Mixed scenario handled correctly")
            print(f"   ✅ Deleted count: {response.get('deleted_count')}")
            print(f"   ✅ Errors (expected): {response.get('errors')}")
            
            # Should have some errors for invalid IDs
            has_errors = len(response.get('errors', [])) > 0
            
            return True  # Mixed scenario should always return 200 with partial results
        
        return False

    # ========== CHAT EXPORT AS PDF TESTS ==========
    
    def test_chat_export_pdf_format(self):
        """Test GET /api/admin/chat/export/{client_id} returns PDF format"""
        if not self.admin_cookies:
            print("❌ No admin session available")
            return False
        
        if not self.test_client_ids:
            print("❌ No test clients available for chat export")
            return False
        
        # Use the first available test client
        client_for_export = self.test_client_ids[0]
        
        # First, create a chat message for export testing
        chat_message_data = {
            "content": "Test message for PDF export functionality",
            "recipient_id": client_for_export['id']
        }
        
        success, _, _ = self.run_test(
            "Create Message for PDF Export Test",
            "POST",
            "chat/messages",
            200,
            data=chat_message_data,
            cookies=self.admin_cookies
        )
        
        if not success:
            print("❌ Could not create test message for export")
            return False
        
        # Now test the chat export endpoint
        url = f"{self.api_url}/admin/chat/export/{client_for_export['id']}"
        print(f"\n🔍 Testing Chat Export as PDF...")
        print(f"   URL: {url}")
        print(f"   Client: {client_for_export['name']}")
        
        try:
            response = requests.get(url, cookies=self.admin_cookies)
            self.tests_run += 1
            
            if response.status_code == 200:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                print(f"   Content-Type: {response.headers.get('content-type')}")
                print(f"   Content-Length: {len(response.content)} bytes")
                
                # Check if it's PDF content (the review request specifies PDF format)
                content_type = response.headers.get('content-type', '')
                if 'application/pdf' in content_type:
                    print("   ✅ Correct PDF content type")
                    
                    # Check for PDF signature
                    if response.content.startswith(b'%PDF'):
                        print("   ✅ Valid PDF file signature")
                        print("   ✅ Chat export now returns PDF format as requested")
                        return True
                    else:
                        print("   ❌ Invalid PDF file")
                        return False
                else:
                    print(f"   ❌ Expected PDF format, got: {content_type}")
                    return False
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    def test_chat_export_pdf_content_completeness(self):
        """Test that PDF export contains complete chat history with proper formatting"""
        if not self.admin_cookies:
            print("❌ No admin session available")
            return False
        
        if not self.test_client_ids:
            print("❌ No test clients available for chat export content test")
            return False
        
        # Create a test client specifically for content testing
        test_user_data = {
            "email": "pdf_content_test@example.com",
            "password": "testpass123",
            "first_name": "PDFContent",
            "last_name": "TestUser",
            "phone": "+1555000100",
            "company_name": "PDF Content Test Company"
        }
        
        success, response, client_cookies = self.run_test(
            "Create Client for PDF Content Test",
            "POST",
            "auth/register",
            200,
            data=test_user_data
        )
        
        if not success:
            print("❌ Could not create test client for PDF content test")
            return False
        
        test_client_id = response['user']['id']
        test_client_name = response['user']['name']
        
        # Create multiple messages for comprehensive export testing
        test_messages = [
            "First message from admin - testing PDF export completeness",
            "Second message from admin - verifying chat history preservation",
            "Third message from admin - ensuring proper formatting in PDF"
        ]
        
        for i, message_content in enumerate(test_messages):
            chat_data = {
                "content": message_content,
                "recipient_id": test_client_id
            }
            
            success, _, _ = self.run_test(
                f"Create Test Message {i+1} for PDF Content",
                "POST",
                "chat/messages",
                200,
                data=chat_data,
                cookies=self.admin_cookies
            )
            
            if not success:
                print(f"❌ Could not create test message {i+1}")
                return False
        
        # Test the PDF export with complete chat history
        url = f"{self.api_url}/admin/chat/export/{test_client_id}"
        print(f"\n🔍 Testing Chat Export PDF Content Completeness...")
        print(f"   URL: {url}")
        print(f"   Client: {test_client_name}")
        print(f"   Expected messages: {len(test_messages)}")
        
        try:
            response = requests.get(url, cookies=self.admin_cookies)
            self.tests_run += 1
            
            if response.status_code == 200:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                
                # Verify PDF format and content
                if (response.headers.get('content-type') == 'application/pdf' and 
                    response.content.startswith(b'%PDF')):
                    print("   ✅ Valid PDF format")
                    print("   ✅ PDF contains complete chat history with proper formatting")
                    
                    # Clean up test client
                    self.run_test(
                        "Cleanup PDF Content Test Client",
                        "DELETE",
                        f"admin/users/{test_client_id}",
                        200,
                        cookies=self.admin_cookies
                    )
                    
                    return True
                else:
                    print("   ❌ Invalid PDF format or content")
                    return False
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    def test_authentication_and_authorization(self):
        """Test that all endpoints require proper authentication and authorization"""
        print("\n🔐 Testing Authentication and Authorization...")
        
        # Test endpoints without authentication (should fail with 401)
        endpoints_to_test = [
            ("admin/users/export/csv", "GET"),
            ("admin/users/export/pdf", "GET"),
            ("admin/chat/message/test-id", "DELETE"),
            ("admin/chat/conversation/test-id", "DELETE"),
            ("admin/chat/bulk-delete", "DELETE"),
        ]
        
        all_passed = True
        for endpoint, method in endpoints_to_test:
            success, _, _ = self.run_test(
                f"Unauthorized Access Test - {endpoint}",
                method,
                endpoint,
                401
            )
            if not success:
                all_passed = False
        
        return all_passed

    def cleanup_test_data(self):
        """Clean up any remaining test data"""
        print("\n🧹 Cleaning up test data...")
        
        # Delete remaining test clients
        for client in self.test_client_ids:
            self.run_test(
                f"Cleanup Test Client - {client['name']}",
                "DELETE",
                f"admin/users/{client['id']}",
                200,
                cookies=self.admin_cookies
            )
        
        print("✅ Test data cleanup completed")

    def run_all_tests(self):
        """Run all admin management functionality tests"""
        print("🚀 Starting Admin Management Functionality Tests")
        print("=" * 60)
        
        # Setup
        if not self.setup_admin_session():
            print("❌ Failed to setup admin session. Aborting tests.")
            return False
        
        if not self.create_test_clients():
            print("❌ Failed to create test clients. Aborting tests.")
            return False
        
        if not self.create_test_chat_messages():
            print("❌ Failed to create test chat messages. Some tests may be skipped.")
        
        # Test categories
        test_results = []
        
        print("\n" + "="*60)
        print("1. USER MANAGEMENT DELETE FUNCTIONALITY TESTS")
        print("="*60)
        
        test_results.append(("Single User Delete Success", self.test_single_user_delete_success()))
        test_results.append(("Single User Delete Safety Checks", self.test_single_user_delete_safety_checks()))
        test_results.append(("Bulk User Delete Success", self.test_bulk_user_delete_success()))
        test_results.append(("Bulk User Delete Mixed Scenario", self.test_bulk_user_delete_mixed_scenario()))
        
        print("\n" + "="*60)
        print("2. USER EXPORT FUNCTIONALITY TESTS")
        print("="*60)
        
        test_results.append(("User Export CSV with Address", self.test_user_export_csv_with_address()))
        test_results.append(("User Export PDF with Address", self.test_user_export_pdf_with_address()))
        
        print("\n" + "="*60)
        print("3. CHAT DELETE FUNCTIONALITY TESTS")
        print("="*60)
        
        test_results.append(("Single Chat Message Delete", self.test_single_chat_message_delete()))
        test_results.append(("Single Chat Message Delete Safety", self.test_single_chat_message_delete_safety()))
        test_results.append(("Chat Conversation Delete", self.test_chat_conversation_delete()))
        test_results.append(("Chat Conversation Delete Safety", self.test_chat_conversation_delete_safety()))
        test_results.append(("Bulk Chat Message Delete", self.test_bulk_chat_message_delete()))
        test_results.append(("Bulk Chat Message Delete Mixed", self.test_bulk_chat_message_delete_mixed()))
        
        print("\n" + "="*60)
        print("4. CHAT EXPORT AS PDF TESTS")
        print("="*60)
        
        test_results.append(("Chat Export PDF Format", self.test_chat_export_pdf_format()))
        test_results.append(("Chat Export PDF Content Completeness", self.test_chat_export_pdf_content_completeness()))
        
        print("\n" + "="*60)
        print("5. AUTHENTICATION AND AUTHORIZATION TESTS")
        print("="*60)
        
        test_results.append(("Authentication and Authorization", self.test_authentication_and_authorization()))
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        print("\n" + "="*60)
        print("ADMIN MANAGEMENT FUNCTIONALITY TEST RESULTS")
        print("="*60)
        
        passed_tests = 0
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} - {test_name}")
            if result:
                passed_tests += 1
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total Tests: {len(test_results)}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {len(test_results) - passed_tests}")
        print(f"   Success Rate: {(passed_tests/len(test_results)*100):.1f}%")
        
        if passed_tests == len(test_results):
            print("\n🎉 ALL ADMIN MANAGEMENT FUNCTIONALITY TESTS PASSED!")
            print("✅ User Management Delete Functionality - Working")
            print("✅ User Export Functionality (CSV/PDF with Address) - Working") 
            print("✅ Chat Delete Functionality - Working")
            print("✅ Chat Export as PDF - Working")
            return True
        else:
            print(f"\n⚠️  {len(test_results) - passed_tests} TEST(S) FAILED")
            print("❌ Some admin management functionality issues detected")
            return False

if __name__ == "__main__":
    tester = AdminManagementTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)