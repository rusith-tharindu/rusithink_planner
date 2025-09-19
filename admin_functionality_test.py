import requests
import sys
from datetime import datetime, timedelta
import json
import tempfile
import os

class AdminFunctionalityTester:
    def __init__(self, base_url="https://rusithink-manage.preview.emergentagent.com"):
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
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data, response.cookies, response
                except:
                    return True, {}, response.cookies, response
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}, None, response

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}, None, None

    def test_admin_login(self):
        """Test admin authentication"""
        login_data = {
            "username": "rusithink",
            "password": "20200104Rh"
        }
        
        success, response, cookies, _ = self.run_test(
            "Admin Login", 
            "POST", 
            "auth/admin-login", 
            200, 
            data=login_data
        )
        
        if success:
            self.admin_cookies = cookies
            if 'session_token' in response:
                self.admin_session_token = response['session_token']
            print(f"   ✅ Admin authenticated: {response['user']['name']}")
            return True
        
        return success

    def create_test_clients(self):
        """Create test clients for deletion and export testing"""
        test_clients = [
            {
                "email": "admin_test_client1@example.com",
                "password": "testpass123",
                "first_name": "AdminTest",
                "last_name": "Client1",
                "phone": "+1234567890",
                "company_name": "Admin Test Company 1",
                "address": "123 Admin Test Street, Test City, TC 12345"
            },
            {
                "email": "admin_test_client2@example.com",
                "password": "testpass123",
                "first_name": "AdminTest",
                "last_name": "Client2",
                "phone": "+1234567891",
                "company_name": "Admin Test Company 2",
                "address": "456 Admin Test Avenue, Test City, TC 12346"
            },
            {
                "email": "admin_test_client3@example.com",
                "password": "testpass123",
                "first_name": "AdminTest",
                "last_name": "Client3",
                "phone": "+1234567892",
                "company_name": "Admin Test Company 3",
                "address": "789 Admin Test Boulevard, Test City, TC 12347"
            }
        ]
        
        created_clients = []
        for client_data in test_clients:
            success, response, _, _ = self.run_test(
                f"Create Test Client ({client_data['email']})",
                "POST",
                "auth/register",
                200,
                data=client_data
            )
            
            if success and 'user' in response:
                created_clients.append({
                    'id': response['user']['id'],
                    'email': response['user']['email'],
                    'name': response['user']['name']
                })
                print(f"   ✅ Created: {response['user']['name']} (ID: {response['user']['id']})")
        
        self.test_client_ids = [client['id'] for client in created_clients]
        return len(created_clients) == len(test_clients)

    # ========== USER MANAGEMENT DELETE TESTS ==========
    
    def test_single_user_delete(self):
        """Test single user deletion endpoint"""
        if not self.admin_cookies or not self.test_client_ids:
            print("❌ Prerequisites not met for single user delete test")
            return False
        
        user_id_to_delete = self.test_client_ids[0]
        
        success, response, _, _ = self.run_test(
            "Single User Delete",
            "DELETE",
            f"admin/users/{user_id_to_delete}",
            200,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ User deleted: {response.get('message')}")
            self.test_client_ids.remove(user_id_to_delete)
            return True
        
        return False

    def test_bulk_user_delete(self):
        """Test bulk user deletion endpoint"""
        if not self.admin_cookies or len(self.test_client_ids) < 2:
            print("❌ Prerequisites not met for bulk user delete test")
            return False
        
        # Delete 2 users in bulk
        users_to_delete = self.test_client_ids[:2]
        
        success, response, _, _ = self.run_test(
            "Bulk User Delete",
            "DELETE",
            "admin/users/bulk",
            200,
            data=users_to_delete,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Bulk delete completed: {response.get('message')}")
            print(f"   ✅ Deleted count: {response.get('deleted_count')}")
            if response.get('errors'):
                print(f"   ⚠️  Errors: {response.get('errors')}")
            
            # Remove deleted users from our list
            for user_id in users_to_delete:
                if user_id in self.test_client_ids:
                    self.test_client_ids.remove(user_id)
            
            return True
        
        return False

    def test_user_delete_safety_checks(self):
        """Test safety checks for user deletion"""
        if not self.admin_cookies:
            print("❌ No admin session for safety check tests")
            return False
        
        # Test 1: Try to delete admin account (should fail)
        success, users_response, _, _ = self.run_test(
            "Get Users for Admin Safety Test",
            "GET",
            "admin/users",
            200,
            cookies=self.admin_cookies
        )
        
        if not success:
            return False
        
        admin_user = None
        for user in users_response:
            if user.get('role') == 'admin':
                admin_user = user
                break
        
        if not admin_user:
            print("❌ Could not find admin user for safety test")
            return False
        
        # Try to delete admin (should fail with 400)
        success, response, _, _ = self.run_test(
            "Delete Admin Account (Safety Check)",
            "DELETE",
            f"admin/users/{admin_user['id']}",
            400,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Admin deletion blocked: {response.get('detail')}")
            return True
        
        return False

    # ========== USER EXPORT TESTS ==========
    
    def test_csv_export_with_address(self):
        """Test CSV export with address field"""
        if not self.admin_cookies:
            print("❌ No admin session for CSV export test")
            return False
        
        url = f"{self.api_url}/admin/users/export/csv"
        print(f"\n🔍 Testing CSV Export with Address Field...")
        print(f"   URL: {url}")
        
        try:
            response = requests.get(url, cookies=self.admin_cookies)
            self.tests_run += 1
            
            if response.status_code == 200:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                
                # Check headers
                content_type = response.headers.get('content-type', '')
                content_disposition = response.headers.get('content-disposition', '')
                
                print(f"   Content-Type: {content_type}")
                print(f"   Content-Disposition: {content_disposition}")
                print(f"   Content-Length: {len(response.content)} bytes")
                
                # Verify it's CSV
                if 'text/csv' in content_type:
                    print("   ✅ Correct CSV content type")
                
                # Verify download headers
                if 'attachment' in content_disposition and 'filename' in content_disposition:
                    print("   ✅ Proper download headers present")
                
                # Check CSV content for address field
                content = response.text
                if 'Address' in content:
                    print("   ✅ Address field included in CSV headers")
                
                # Check for actual address data
                lines = content.split('\n')
                if len(lines) > 1:
                    headers = lines[0].split(',')
                    if 'Address' in headers:
                        address_index = headers.index('Address')
                        for line in lines[1:3]:  # Check first few data rows
                            if line.strip():
                                fields = line.split(',')
                                if len(fields) > address_index and fields[address_index].strip():
                                    print(f"   ✅ Address data found: {fields[address_index][:30]}...")
                                    break
                
                return True
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    def test_pdf_export_with_address(self):
        """Test PDF export with address field"""
        if not self.admin_cookies:
            print("❌ No admin session for PDF export test")
            return False
        
        url = f"{self.api_url}/admin/users/export/pdf"
        print(f"\n🔍 Testing PDF Export with Address Field...")
        print(f"   URL: {url}")
        
        try:
            response = requests.get(url, cookies=self.admin_cookies)
            self.tests_run += 1
            
            if response.status_code == 200:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                
                # Check headers
                content_type = response.headers.get('content-type', '')
                content_disposition = response.headers.get('content-disposition', '')
                
                print(f"   Content-Type: {content_type}")
                print(f"   Content-Disposition: {content_disposition}")
                print(f"   Content-Length: {len(response.content)} bytes")
                
                # Verify it's PDF
                if 'application/pdf' in content_type:
                    print("   ✅ Correct PDF content type")
                
                # Verify download headers
                if 'attachment' in content_disposition and 'filename' in content_disposition:
                    print("   ✅ Proper download headers present")
                
                # Check PDF signature
                if response.content.startswith(b'%PDF'):
                    print("   ✅ Valid PDF file signature")
                
                # Check file size (should be substantial for a real PDF)
                if len(response.content) > 1000:
                    print("   ✅ PDF file has substantial content")
                
                return True
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    # ========== CHAT MANAGEMENT TESTS ==========
    
    def create_test_chat_messages(self):
        """Create test chat messages for deletion testing"""
        if not self.admin_cookies or not self.test_client_ids:
            print("❌ Prerequisites not met for chat message creation")
            return False
        
        # Create a test client for chat
        test_client_data = {
            "email": "chat_test_client@example.com",
            "password": "testpass123",
            "first_name": "ChatTest",
            "last_name": "Client",
            "phone": "+1234567899",
            "company_name": "Chat Test Company"
        }
        
        success, response, client_cookies, _ = self.run_test(
            "Create Chat Test Client",
            "POST",
            "auth/register",
            200,
            data=test_client_data
        )
        
        if not success:
            return False
        
        client_id = response['user']['id']
        self.chat_test_client_id = client_id
        self.chat_test_client_cookies = client_cookies
        
        # Admin sends messages to client
        messages_to_send = [
            "Test message 1 for chat deletion testing",
            "Test message 2 for chat deletion testing",
            "Test message 3 for chat deletion testing"
        ]
        
        created_message_ids = []
        for i, content in enumerate(messages_to_send):
            message_data = {
                "content": content,
                "recipient_id": client_id
            }
            
            success, response, _, _ = self.run_test(
                f"Admin Sends Test Message {i+1}",
                "POST",
                "chat/messages",
                200,
                data=message_data,
                cookies=self.admin_cookies
            )
            
            if success and 'id' in response:
                created_message_ids.append(response['id'])
                print(f"   ✅ Created message: {response['id']}")
        
        self.test_message_ids = created_message_ids
        return len(created_message_ids) == len(messages_to_send)

    def test_chat_message_deletion(self):
        """Test single chat message deletion"""
        if not self.admin_cookies or not self.test_message_ids:
            print("❌ Prerequisites not met for chat message deletion test")
            return False
        
        message_id_to_delete = self.test_message_ids[0]
        
        success, response, _, _ = self.run_test(
            "Delete Single Chat Message",
            "DELETE",
            f"admin/chat/message/{message_id_to_delete}",
            200,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Message deleted: {response.get('message')}")
            self.test_message_ids.remove(message_id_to_delete)
            return True
        
        return False

    def test_chat_conversation_deletion(self):
        """Test conversation deletion"""
        if not self.admin_cookies or not hasattr(self, 'chat_test_client_id'):
            print("❌ Prerequisites not met for conversation deletion test")
            return False
        
        success, response, _, _ = self.run_test(
            "Delete Chat Conversation",
            "DELETE",
            f"admin/chat/conversation/{self.chat_test_client_id}",
            200,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Conversation deleted: {response.get('message')}")
            print(f"   ✅ Messages deleted: {response.get('deleted_messages')}")
            return True
        
        return False

    def test_bulk_chat_message_deletion(self):
        """Test bulk chat message deletion"""
        if not self.admin_cookies:
            print("❌ No admin session for bulk chat deletion test")
            return False
        
        # Create fresh messages for bulk deletion test
        if not hasattr(self, 'chat_test_client_id'):
            print("❌ No chat test client for bulk deletion")
            return False
        
        # Send a few more messages for bulk deletion
        bulk_messages = ["Bulk test message 1", "Bulk test message 2"]
        bulk_message_ids = []
        
        for content in bulk_messages:
            message_data = {
                "content": content,
                "recipient_id": self.chat_test_client_id
            }
            
            success, response, _, _ = self.run_test(
                f"Create Message for Bulk Delete",
                "POST",
                "chat/messages",
                200,
                data=message_data,
                cookies=self.admin_cookies
            )
            
            if success and 'id' in response:
                bulk_message_ids.append(response['id'])
        
        if not bulk_message_ids:
            print("❌ Could not create messages for bulk deletion test")
            return False
        
        # Bulk delete the messages
        success, response, _, _ = self.run_test(
            "Bulk Delete Chat Messages",
            "DELETE",
            "admin/chat/bulk-delete",
            200,
            data=bulk_message_ids,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Bulk delete completed: {response.get('message')}")
            print(f"   ✅ Deleted count: {response.get('deleted_count')}")
            if response.get('errors'):
                print(f"   ⚠️  Errors: {response.get('errors')}")
            return True
        
        return False

    def test_chat_export_as_pdf(self):
        """Test chat export as PDF"""
        if not self.admin_cookies or not hasattr(self, 'chat_test_client_id'):
            print("❌ Prerequisites not met for chat PDF export test")
            return False
        
        url = f"{self.api_url}/admin/chat/export/{self.chat_test_client_id}"
        print(f"\n🔍 Testing Chat Export as PDF...")
        print(f"   URL: {url}")
        
        try:
            response = requests.get(url, cookies=self.admin_cookies)
            self.tests_run += 1
            
            if response.status_code == 200:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                
                # Check headers
                content_type = response.headers.get('content-type', '')
                content_disposition = response.headers.get('content-disposition', '')
                
                print(f"   Content-Type: {content_type}")
                print(f"   Content-Disposition: {content_disposition}")
                print(f"   Content-Length: {len(response.content)} bytes")
                
                # Verify it's PDF (as requested in review)
                if 'application/pdf' in content_type:
                    print("   ✅ Correct PDF content type (as requested)")
                
                # Verify download headers
                if 'attachment' in content_disposition:
                    print("   ✅ Proper download headers present")
                
                # Check PDF signature
                if response.content.startswith(b'%PDF'):
                    print("   ✅ Valid PDF file signature")
                
                return True
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    # ========== BACKEND DEPENDENCIES TESTS ==========
    
    def test_pandas_dependency(self):
        """Test that pandas is working for CSV generation"""
        try:
            import pandas as pd
            print(f"\n🔍 Testing Pandas Dependency...")
            
            # Create a simple DataFrame
            test_data = {'Name': ['Test User'], 'Email': ['test@example.com']}
            df = pd.DataFrame(test_data)
            
            # Convert to CSV
            csv_output = df.to_csv(index=False)
            
            if 'Name,Email' in csv_output and 'Test User,test@example.com' in csv_output:
                print("   ✅ Pandas working correctly for CSV generation")
                self.tests_run += 1
                self.tests_passed += 1
                return True
            else:
                print("   ❌ Pandas CSV generation not working properly")
                return False
                
        except ImportError:
            print("   ❌ Pandas not installed or not importable")
            return False
        except Exception as e:
            print(f"   ❌ Pandas error: {str(e)}")
            return False

    def test_reportlab_dependency(self):
        """Test that reportlab is working for PDF generation"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph
            from reportlab.lib.styles import getSampleStyleSheet
            import io
            
            print(f"\n🔍 Testing ReportLab Dependency...")
            
            # Create a simple PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            
            content = [Paragraph("Test PDF Generation", styles['Title'])]
            doc.build(content)
            
            buffer.seek(0)
            pdf_content = buffer.getvalue()
            
            if pdf_content.startswith(b'%PDF'):
                print("   ✅ ReportLab working correctly for PDF generation")
                self.tests_run += 1
                self.tests_passed += 1
                return True
            else:
                print("   ❌ ReportLab PDF generation not working properly")
                return False
                
        except ImportError as e:
            print(f"   ❌ ReportLab not installed or not importable: {str(e)}")
            return False
        except Exception as e:
            print(f"   ❌ ReportLab error: {str(e)}")
            return False

    # ========== AUTHENTICATION & SECURITY TESTS ==========
    
    def test_admin_only_access(self):
        """Test that admin endpoints require admin privileges"""
        # Create a regular client session
        client_data = {
            "email": "security_test_client@example.com",
            "password": "testpass123",
            "first_name": "Security",
            "last_name": "TestClient",
            "phone": "+1234567888",
            "company_name": "Security Test Company"
        }
        
        success, response, client_cookies, _ = self.run_test(
            "Create Client for Security Test",
            "POST",
            "auth/register",
            200,
            data=client_data
        )
        
        if not success:
            print("❌ Could not create client for security test")
            return False
        
        client_id = response['user']['id']
        
        # Test admin-only endpoints with client session (should all fail with 403)
        admin_endpoints = [
            ("admin/users", "GET"),
            ("admin/users/export/csv", "GET"),
            ("admin/users/export/pdf", "GET"),
            (f"admin/users/{client_id}", "DELETE"),
            ("admin/chat/message/fake-id", "DELETE"),
            ("admin/chat/conversation/fake-id", "DELETE"),
            ("admin/chat/bulk-delete", "DELETE")
        ]
        
        all_blocked = True
        for endpoint, method in admin_endpoints:
            success, _, _, _ = self.run_test(
                f"Security Test: {endpoint} (Client Access)",
                method,
                endpoint,
                403,
                cookies=client_cookies
            )
            
            if not success:
                all_blocked = False
                print(f"   ❌ Security breach: Client can access {endpoint}")
        
        # Clean up test client
        self.run_test(
            "Cleanup Security Test Client",
            "DELETE",
            f"admin/users/{client_id}",
            200,
            cookies=self.admin_cookies
        )
        
        if all_blocked:
            print("   ✅ All admin endpoints properly secured")
        
        return all_blocked

    def test_error_handling(self):
        """Test proper error handling and responses"""
        if not self.admin_cookies:
            print("❌ No admin session for error handling test")
            return False
        
        error_tests = [
            # Non-existent user deletion
            ("admin/users/non-existent-id", "DELETE", 404),
            # Non-existent message deletion  
            ("admin/chat/message/non-existent-id", "DELETE", 404),
            # Non-existent conversation deletion
            ("admin/chat/conversation/non-existent-id", "DELETE", 404),
        ]
        
        all_passed = True
        for endpoint, method, expected_status in error_tests:
            success, response, _, _ = self.run_test(
                f"Error Handling: {endpoint}",
                method,
                endpoint,
                expected_status,
                cookies=self.admin_cookies
            )
            
            if not success:
                all_passed = False
        
        return all_passed

    def run_comprehensive_test(self):
        """Run all comprehensive admin functionality tests"""
        print("🚀 Starting Comprehensive Admin Functionality Testing")
        print("=" * 60)
        
        # Step 1: Authentication
        print("\n📋 STEP 1: AUTHENTICATION & SETUP")
        if not self.test_admin_login():
            print("❌ CRITICAL: Admin login failed - cannot continue")
            return False
        
        # Step 2: Create test data
        print("\n📋 STEP 2: TEST DATA CREATION")
        if not self.create_test_clients():
            print("❌ CRITICAL: Could not create test clients")
            return False
        
        if not self.create_test_chat_messages():
            print("❌ CRITICAL: Could not create test chat messages")
            return False
        
        # Step 3: User Management Delete & Export Tests
        print("\n📋 STEP 3: USER MANAGEMENT DELETE & EXPORT")
        user_delete_tests = [
            self.test_single_user_delete(),
            self.test_bulk_user_delete(),
            self.test_user_delete_safety_checks(),
            self.test_csv_export_with_address(),
            self.test_pdf_export_with_address()
        ]
        
        # Step 4: Chat Management Delete & Export Tests
        print("\n📋 STEP 4: CHAT MANAGEMENT DELETE & EXPORT")
        chat_tests = [
            self.test_chat_message_deletion(),
            self.test_bulk_chat_message_deletion(),
            self.test_chat_conversation_deletion(),
            self.test_chat_export_as_pdf()
        ]
        
        # Step 5: Backend Dependencies Tests
        print("\n📋 STEP 5: BACKEND DEPENDENCIES & FILE GENERATION")
        dependency_tests = [
            self.test_pandas_dependency(),
            self.test_reportlab_dependency()
        ]
        
        # Step 6: Authentication & Security Tests
        print("\n📋 STEP 6: AUTHENTICATION & SECURITY")
        security_tests = [
            self.test_admin_only_access(),
            self.test_error_handling()
        ]
        
        # Calculate results
        all_tests = user_delete_tests + chat_tests + dependency_tests + security_tests
        passed_tests = sum(all_tests)
        total_tests = len(all_tests)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST RESULTS")
        print("=" * 60)
        print(f"Total API Tests Run: {self.tests_run}")
        print(f"Total API Tests Passed: {self.tests_passed}")
        print(f"API Test Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        print()
        print(f"Functional Test Categories: {total_tests}")
        print(f"Functional Categories Passed: {passed_tests}")
        print(f"Functional Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n📋 DETAILED RESULTS BY CATEGORY:")
        print(f"   User Management: {sum(user_delete_tests)}/{len(user_delete_tests)} ({'✅' if all(user_delete_tests) else '❌'})")
        print(f"   Chat Management: {sum(chat_tests)}/{len(chat_tests)} ({'✅' if all(chat_tests) else '❌'})")
        print(f"   Dependencies: {sum(dependency_tests)}/{len(dependency_tests)} ({'✅' if all(dependency_tests) else '❌'})")
        print(f"   Security: {sum(security_tests)}/{len(security_tests)} ({'✅' if all(security_tests) else '❌'})")
        
        # Overall result
        overall_success = all(all_tests)
        print(f"\n🎯 OVERALL RESULT: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
        
        return overall_success

if __name__ == "__main__":
    tester = AdminFunctionalityTester()
    success = tester.run_comprehensive_test()
    sys.exit(0 if success else 1)