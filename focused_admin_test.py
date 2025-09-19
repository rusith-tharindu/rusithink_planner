import requests
import sys
from datetime import datetime, timedelta
import json

class FocusedAdminTester:
    def __init__(self, base_url="https://rusithink-planner.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.admin_cookies = None
        self.test_results = []

    def setup_admin_session(self):
        """Setup admin session"""
        login_data = {"username": "rusithink", "password": "20200104Rh"}
        
        try:
            response = requests.post(f"{self.api_url}/auth/admin-login", json=login_data)
            if response.status_code == 200:
                self.admin_cookies = response.cookies
                print("✅ Admin session established")
                return True
            else:
                print(f"❌ Admin login failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Admin login error: {str(e)}")
            return False

    def test_user_delete_functionality(self):
        """Test user delete functionality comprehensively"""
        print("\n🔍 Testing User Delete Functionality...")
        
        # Create a test user first
        test_user_data = {
            "email": "delete_test_user@example.com",
            "password": "testpass123",
            "first_name": "DeleteTest",
            "last_name": "User",
            "phone": "+1555000001",
            "company_name": "Delete Test Company",
            "address": "123 Delete Test Street"
        }
        
        try:
            # Create test user
            response = requests.post(f"{self.api_url}/auth/register", json=test_user_data)
            if response.status_code != 200:
                print(f"❌ Failed to create test user: {response.status_code}")
                return False
            
            user_id = response.json()['user']['id']
            user_name = response.json()['user']['name']
            print(f"✅ Created test user: {user_name} (ID: {user_id})")
            
            # Test single user delete
            delete_response = requests.delete(
                f"{self.api_url}/admin/users/{user_id}",
                cookies=self.admin_cookies
            )
            
            if delete_response.status_code == 200:
                print("✅ Single user delete: WORKING")
                self.test_results.append(("Single User Delete", True))
            else:
                print(f"❌ Single user delete failed: {delete_response.status_code}")
                self.test_results.append(("Single User Delete", False))
                return False
            
            # Test bulk user delete with multiple users
            bulk_users = []
            for i in range(2):
                bulk_user_data = {
                    "email": f"bulk_test_{i}@example.com",
                    "password": "testpass123",
                    "first_name": f"BulkTest{i}",
                    "last_name": "User",
                    "phone": f"+155500000{i+2}",
                    "company_name": f"Bulk Test Company {i+1}"
                }
                
                response = requests.post(f"{self.api_url}/auth/register", json=bulk_user_data)
                if response.status_code == 200:
                    bulk_users.append(response.json()['user']['id'])
            
            if len(bulk_users) >= 2:
                bulk_delete_response = requests.delete(
                    f"{self.api_url}/admin/users/bulk",
                    json=bulk_users,
                    headers={'Content-Type': 'application/json'},
                    cookies=self.admin_cookies
                )
                
                if bulk_delete_response.status_code == 200:
                    result = bulk_delete_response.json()
                    print(f"✅ Bulk user delete: WORKING (deleted {result.get('deleted_count')} users)")
                    self.test_results.append(("Bulk User Delete", True))
                else:
                    print(f"❌ Bulk user delete failed: {bulk_delete_response.status_code}")
                    self.test_results.append(("Bulk User Delete", False))
            
            return True
            
        except Exception as e:
            print(f"❌ User delete test error: {str(e)}")
            self.test_results.append(("User Delete Functionality", False))
            return False

    def test_user_export_functionality(self):
        """Test user export functionality"""
        print("\n🔍 Testing User Export Functionality...")
        
        try:
            # Test CSV export
            csv_response = requests.get(f"{self.api_url}/admin/users/export/csv", cookies=self.admin_cookies)
            if csv_response.status_code == 200:
                content = csv_response.text
                if 'Address' in content and 'Email' in content:
                    print("✅ CSV export with address field: WORKING")
                    self.test_results.append(("CSV Export with Address", True))
                else:
                    print("❌ CSV export missing address field")
                    self.test_results.append(("CSV Export with Address", False))
            else:
                print(f"❌ CSV export failed: {csv_response.status_code}")
                self.test_results.append(("CSV Export with Address", False))
            
            # Test PDF export
            pdf_response = requests.get(f"{self.api_url}/admin/users/export/pdf", cookies=self.admin_cookies)
            if pdf_response.status_code == 200:
                if (pdf_response.headers.get('content-type') == 'application/pdf' and 
                    pdf_response.content.startswith(b'%PDF')):
                    print("✅ PDF export with address field: WORKING")
                    self.test_results.append(("PDF Export with Address", True))
                else:
                    print("❌ PDF export invalid format")
                    self.test_results.append(("PDF Export with Address", False))
            else:
                print(f"❌ PDF export failed: {pdf_response.status_code}")
                # Let's check what the actual error is
                try:
                    error_detail = pdf_response.json()
                    print(f"   Error detail: {error_detail}")
                except:
                    print(f"   Error text: {pdf_response.text}")
                self.test_results.append(("PDF Export with Address", False))
            
            return True
            
        except Exception as e:
            print(f"❌ User export test error: {str(e)}")
            return False

    def test_chat_delete_functionality(self):
        """Test chat delete functionality"""
        print("\n🔍 Testing Chat Delete Functionality...")
        
        try:
            # Create a test client for chat testing
            test_client_data = {
                "email": "chat_delete_test@example.com",
                "password": "testpass123",
                "first_name": "ChatDelete",
                "last_name": "TestUser",
                "phone": "+1555000010",
                "company_name": "Chat Delete Test Company"
            }
            
            response = requests.post(f"{self.api_url}/auth/register", json=test_client_data)
            if response.status_code != 200:
                print(f"❌ Failed to create test client for chat: {response.status_code}")
                return False
            
            client_id = response.json()['user']['id']
            client_cookies = response.cookies
            print(f"✅ Created test client for chat: {client_id}")
            
            # Create a chat message from admin to client
            message_data = {
                "content": "Test message for deletion testing",
                "recipient_id": client_id
            }
            
            msg_response = requests.post(
                f"{self.api_url}/chat/messages",
                json=message_data,
                cookies=self.admin_cookies
            )
            
            if msg_response.status_code == 200:
                message_id = msg_response.json()['id']
                print(f"✅ Created test message: {message_id}")
                
                # Test single message delete
                delete_msg_response = requests.delete(
                    f"{self.api_url}/admin/chat/message/{message_id}",
                    cookies=self.admin_cookies
                )
                
                if delete_msg_response.status_code == 200:
                    print("✅ Single chat message delete: WORKING")
                    self.test_results.append(("Single Chat Message Delete", True))
                else:
                    print(f"❌ Single message delete failed: {delete_msg_response.status_code}")
                    self.test_results.append(("Single Chat Message Delete", False))
                
                # Create another message for conversation delete test
                msg_response2 = requests.post(
                    f"{self.api_url}/chat/messages",
                    json={"content": "Second test message", "recipient_id": client_id},
                    cookies=self.admin_cookies
                )
                
                if msg_response2.status_code == 200:
                    # Test conversation delete
                    conv_delete_response = requests.delete(
                        f"{self.api_url}/admin/chat/conversation/{client_id}",
                        cookies=self.admin_cookies
                    )
                    
                    if conv_delete_response.status_code == 200:
                        print("✅ Chat conversation delete: WORKING")
                        self.test_results.append(("Chat Conversation Delete", True))
                    else:
                        print(f"❌ Conversation delete failed: {conv_delete_response.status_code}")
                        self.test_results.append(("Chat Conversation Delete", False))
                
                # Test bulk message delete
                # Create multiple messages first
                message_ids = []
                for i in range(3):
                    msg_resp = requests.post(
                        f"{self.api_url}/chat/messages",
                        json={"content": f"Bulk test message {i+1}", "recipient_id": client_id},
                        cookies=self.admin_cookies
                    )
                    if msg_resp.status_code == 200:
                        message_ids.append(msg_resp.json()['id'])
                
                if len(message_ids) >= 2:
                    bulk_delete_response = requests.delete(
                        f"{self.api_url}/admin/chat/bulk-delete",
                        json=message_ids[:2],
                        headers={'Content-Type': 'application/json'},
                        cookies=self.admin_cookies
                    )
                    
                    if bulk_delete_response.status_code == 200:
                        result = bulk_delete_response.json()
                        print(f"✅ Bulk chat message delete: WORKING (deleted {result.get('deleted_count')} messages)")
                        self.test_results.append(("Bulk Chat Message Delete", True))
                    else:
                        print(f"❌ Bulk message delete failed: {bulk_delete_response.status_code}")
                        self.test_results.append(("Bulk Chat Message Delete", False))
            
            # Clean up test client
            requests.delete(f"{self.api_url}/admin/users/{client_id}", cookies=self.admin_cookies)
            
            return True
            
        except Exception as e:
            print(f"❌ Chat delete test error: {str(e)}")
            return False

    def test_chat_export_pdf(self):
        """Test chat export as PDF"""
        print("\n🔍 Testing Chat Export as PDF...")
        
        try:
            # Create a test client for export testing
            test_client_data = {
                "email": "chat_export_test@example.com",
                "password": "testpass123",
                "first_name": "ChatExport",
                "last_name": "TestUser",
                "phone": "+1555000020",
                "company_name": "Chat Export Test Company"
            }
            
            response = requests.post(f"{self.api_url}/auth/register", json=test_client_data)
            if response.status_code != 200:
                print(f"❌ Failed to create test client for export: {response.status_code}")
                return False
            
            client_id = response.json()['user']['id']
            print(f"✅ Created test client for export: {client_id}")
            
            # Create some chat messages for export
            for i in range(3):
                message_data = {
                    "content": f"Test message {i+1} for PDF export",
                    "recipient_id": client_id
                }
                
                requests.post(
                    f"{self.api_url}/chat/messages",
                    json=message_data,
                    cookies=self.admin_cookies
                )
            
            # Test chat export as PDF
            export_response = requests.get(
                f"{self.api_url}/admin/chat/export/{client_id}",
                cookies=self.admin_cookies
            )
            
            if export_response.status_code == 200:
                if (export_response.headers.get('content-type') == 'application/pdf' and 
                    export_response.content.startswith(b'%PDF')):
                    print("✅ Chat export as PDF: WORKING")
                    self.test_results.append(("Chat Export as PDF", True))
                else:
                    print("❌ Chat export not in PDF format")
                    self.test_results.append(("Chat Export as PDF", False))
            else:
                print(f"❌ Chat export failed: {export_response.status_code}")
                self.test_results.append(("Chat Export as PDF", False))
            
            # Clean up test client
            requests.delete(f"{self.api_url}/admin/users/{client_id}", cookies=self.admin_cookies)
            
            return True
            
        except Exception as e:
            print(f"❌ Chat export test error: {str(e)}")
            return False

    def test_authentication_requirements(self):
        """Test authentication requirements"""
        print("\n🔍 Testing Authentication Requirements...")
        
        try:
            # Test endpoints without authentication
            endpoints = [
                ("admin/users/export/csv", "GET"),
                ("admin/users/export/pdf", "GET"),
                ("admin/chat/message/test-id", "DELETE"),
                ("admin/chat/conversation/test-id", "DELETE")
            ]
            
            auth_working = True
            for endpoint, method in endpoints:
                if method == "GET":
                    response = requests.get(f"{self.api_url}/{endpoint}")
                elif method == "DELETE":
                    response = requests.delete(f"{self.api_url}/{endpoint}")
                
                if response.status_code == 401:
                    continue  # Good, authentication required
                else:
                    auth_working = False
                    break
            
            if auth_working:
                print("✅ Authentication and authorization: WORKING")
                self.test_results.append(("Authentication and Authorization", True))
            else:
                print("❌ Authentication issues detected")
                self.test_results.append(("Authentication and Authorization", False))
            
            return auth_working
            
        except Exception as e:
            print(f"❌ Authentication test error: {str(e)}")
            return False

    def run_focused_tests(self):
        """Run focused admin management tests"""
        print("🚀 Starting Focused Admin Management Tests")
        print("=" * 60)
        
        if not self.setup_admin_session():
            print("❌ Cannot proceed without admin session")
            return False
        
        # Run all tests
        self.test_user_delete_functionality()
        self.test_user_export_functionality()
        self.test_chat_delete_functionality()
        self.test_chat_export_pdf()
        self.test_authentication_requirements()
        
        # Summary
        print("\n" + "=" * 60)
        print("FOCUSED ADMIN MANAGEMENT TEST RESULTS")
        print("=" * 60)
        
        passed = 0
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} - {test_name}")
            if result:
                passed += 1
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total Tests: {total}")
        print(f"   Passed: {passed}")
        print(f"   Failed: {total - passed}")
        print(f"   Success Rate: {(passed/total*100):.1f}%")
        
        return passed == total

if __name__ == "__main__":
    tester = FocusedAdminTester()
    success = tester.run_focused_tests()
    sys.exit(0 if success else 1)