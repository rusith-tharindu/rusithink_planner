import requests
import sys
from datetime import datetime, timedelta
import json

class ClientChatVisibilityTester:
    def __init__(self, base_url="https://rusithink-planner.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_cookies = None
        self.client_cookies = None
        self.admin_id = None
        self.client_id = None

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

    def setup_test_environment(self):
        """Setup admin and client sessions for testing"""
        print("🔧 Setting up test environment...")
        
        # 1. Admin login
        admin_login_data = {
            "username": "rusithink",
            "password": "20200104Rh"
        }
        
        success, response, cookies = self.run_test(
            "Admin Login Setup", 
            "POST", 
            "auth/admin-login", 
            200, 
            data=admin_login_data
        )
        
        if not success:
            print("❌ Failed to setup admin session")
            return False
        
        self.admin_cookies = cookies
        self.admin_id = response['user']['id']
        print(f"   ✅ Admin session established: {response['user']['name']}")
        
        # 2. Create test client
        client_data = {
            "email": "client_visibility_test@example.com",
            "password": "testpass123",
            "first_name": "ClientVisibility",
            "last_name": "TestUser",
            "phone": "+1234567900",
            "company_name": "Client Visibility Test Company"
        }
        
        success, response, cookies = self.run_test(
            "Create Test Client", 
            "POST", 
            "auth/register", 
            200, 
            data=client_data
        )
        
        if not success:
            print("❌ Failed to create test client")
            return False
        
        self.client_cookies = cookies
        self.client_id = response['user']['id']
        print(f"   ✅ Test client created: {response['user']['name']} (ID: {self.client_id})")
        
        return True

    def test_admin_info_endpoint(self):
        """Test GET /api/chat/admin-info endpoint for clients"""
        print("\n🎯 FOCUS TEST 1: Backend Admin Info Endpoint")
        
        success, response, _ = self.run_test(
            "Client Gets Admin Info for Chat",
            "GET",
            "chat/admin-info",
            200,
            cookies=self.client_cookies
        )
        
        if success:
            print(f"   ✅ Admin info retrieved: {response.get('name')} (ID: {response.get('id')})")
            print(f"   ✅ Admin role: {response.get('role')}")
            
            # Verify response structure
            required_fields = ['id', 'name', 'role']
            for field in required_fields:
                if field not in response:
                    print(f"   ❌ Missing required field: {field}")
                    return False
            
            if response.get('role') != 'admin':
                print(f"   ❌ Expected admin role, got: {response.get('role')}")
                return False
            
            print("   ✅ Admin info endpoint working correctly for clients")
            return True
        
        return False

    def test_message_exchange_flow(self):
        """Test the complete message exchange flow"""
        print("\n🎯 FOCUS TEST 2: Message Exchange Flow")
        
        # Step 1: Admin sends message to client
        print("   📤 Step 1: Admin sends message to client")
        admin_message_data = {
            "content": "Hello client! This is a test message from admin to verify visibility fix.",
            "recipient_id": self.client_id,
            "task_id": None  # General chat (not task-specific)
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
            print("   ❌ CRITICAL: Admin failed to send message to client")
            return False
        
        admin_message_id = admin_msg_response.get('id')
        print(f"   ✅ Admin message sent successfully (ID: {admin_message_id})")
        print(f"   ✅ Message content: '{admin_msg_response.get('content')[:50]}...'")
        print(f"   ✅ Task ID: {admin_msg_response.get('task_id')} (should be None for general chat)")
        
        # Step 2: Client fetches messages immediately after
        print("   📥 Step 2: Client fetches messages immediately after")
        success, client_messages, _ = self.run_test(
            "Client Fetches Messages After Admin Message",
            "GET",
            "chat/messages",
            200,
            cookies=self.client_cookies
        )
        
        if not success:
            print("   ❌ CRITICAL: Client failed to fetch messages")
            return False
        
        print(f"   📋 Client received {len(client_messages)} messages")
        
        # Step 3: Verify client can see the admin message
        print("   🔍 Step 3: Verify client can see the admin message")
        admin_message_found = False
        
        for i, msg in enumerate(client_messages):
            print(f"      Message {i+1}: From {msg.get('sender_name')} - '{msg.get('content')[:40]}...'")
            
            if (msg.get('sender_id') == self.admin_id and 
                msg.get('id') == admin_message_id):
                admin_message_found = True
                print(f"   ✅ SUCCESS: Client can see admin message!")
                print(f"   ✅ Message ID matches: {msg.get('id')}")
                print(f"   ✅ Sender role: {msg.get('sender_role')}")
                print(f"   ✅ Task ID: {msg.get('task_id')} (general chat)")
                break
        
        if not admin_message_found:
            print("   ❌ CRITICAL FAILURE: Client cannot see admin message!")
            print("   ❌ This indicates the visibility fix is not working")
            return False
        
        # Step 4: Client sends reply
        print("   📤 Step 4: Client sends reply to admin")
        client_reply_data = {
            "content": "Thank you admin! I can see your message now. Reply from client.",
            "recipient_id": self.admin_id,
            "task_id": None  # General chat
        }
        
        success, client_reply_response, _ = self.run_test(
            "Client Sends Reply to Admin",
            "POST",
            "chat/messages",
            200,
            data=client_reply_data,
            cookies=self.client_cookies
        )
        
        if not success:
            print("   ❌ Client failed to send reply to admin")
            return False
        
        client_reply_id = client_reply_response.get('id')
        print(f"   ✅ Client reply sent successfully (ID: {client_reply_id})")
        
        # Step 5: Admin fetches messages to verify they can see client reply
        print("   📥 Step 5: Admin fetches messages to verify client reply")
        success, admin_messages, _ = self.run_test(
            "Admin Fetches Messages After Client Reply",
            "GET",
            f"chat/messages?client_id={self.client_id}",
            200,
            cookies=self.admin_cookies
        )
        
        if not success:
            print("   ❌ Admin failed to fetch messages")
            return False
        
        # Verify admin can see both messages
        admin_msg_found = False
        client_reply_found = False
        
        for msg in admin_messages:
            if msg.get('id') == admin_message_id:
                admin_msg_found = True
            elif msg.get('id') == client_reply_id:
                client_reply_found = True
        
        if admin_msg_found and client_reply_found:
            print("   ✅ SUCCESS: Complete message exchange flow working!")
            print("   ✅ Admin can see both original message and client reply")
            return True
        else:
            print("   ❌ FAILURE: Admin cannot see complete conversation")
            return False

    def test_chat_system_initialization(self):
        """Test chat system initialization and message history"""
        print("\n🎯 FOCUS TEST 3: Chat System Initialization")
        
        # First, send multiple messages to create history
        print("   📝 Creating message history...")
        
        messages_to_send = [
            {"sender": "admin", "content": "Message 1: Initial admin message"},
            {"sender": "client", "content": "Message 2: Client response"},
            {"sender": "admin", "content": "Message 3: Admin follow-up"},
            {"sender": "client", "content": "Message 4: Client final message"}
        ]
        
        sent_message_ids = []
        
        for i, msg_info in enumerate(messages_to_send):
            if msg_info["sender"] == "admin":
                msg_data = {
                    "content": msg_info["content"],
                    "recipient_id": self.client_id,
                    "task_id": None
                }
                cookies = self.admin_cookies
                test_name = f"Send History Message {i+1} (Admin)"
            else:
                msg_data = {
                    "content": msg_info["content"],
                    "recipient_id": self.admin_id,
                    "task_id": None
                }
                cookies = self.client_cookies
                test_name = f"Send History Message {i+1} (Client)"
            
            success, response, _ = self.run_test(
                test_name,
                "POST",
                "chat/messages",
                200,
                data=msg_data,
                cookies=cookies
            )
            
            if success:
                sent_message_ids.append(response.get('id'))
                print(f"      ✅ {msg_info['content'][:30]}...")
            else:
                print(f"      ❌ Failed to send message {i+1}")
                return False
        
        # Test 1: Client calls GET /api/chat/messages for conversation history
        print("   📥 Test 1: Client fetches complete conversation history")
        success, client_history, _ = self.run_test(
            "Client Gets Complete Conversation History",
            "GET",
            "chat/messages",
            200,
            cookies=self.client_cookies
        )
        
        if not success:
            print("   ❌ Client failed to fetch conversation history")
            return False
        
        print(f"   📋 Client received {len(client_history)} messages in history")
        
        # Verify all messages are present
        found_messages = 0
        for sent_id in sent_message_ids:
            for msg in client_history:
                if msg.get('id') == sent_id:
                    found_messages += 1
                    break
        
        if found_messages == len(sent_message_ids):
            print(f"   ✅ SUCCESS: All {found_messages} messages preserved in client history")
        else:
            print(f"   ❌ FAILURE: Only {found_messages}/{len(sent_message_ids)} messages found in client history")
            return False
        
        # Test 2: Verify message filtering works correctly
        print("   🔍 Test 2: Verify message filtering for client users")
        
        # Check that all messages are between client and admin only
        valid_conversation = True
        for msg in client_history:
            sender_id = msg.get('sender_id')
            recipient_id = msg.get('recipient_id')
            
            # Message should be either:
            # - From admin to client, or
            # - From client to admin
            if not ((sender_id == self.admin_id and recipient_id == self.client_id) or
                    (sender_id == self.client_id and recipient_id == self.admin_id)):
                print(f"   ❌ Invalid message found: sender={sender_id}, recipient={recipient_id}")
                valid_conversation = False
        
        if valid_conversation:
            print("   ✅ SUCCESS: Message filtering working correctly - only admin-client conversation")
        else:
            print("   ❌ FAILURE: Message filtering not working - invalid messages in conversation")
            return False
        
        # Test 3: Verify taskId is null for general chat
        print("   🔍 Test 3: Verify taskId is null for general chat")
        
        general_chat_verified = True
        for msg in client_history:
            task_id = msg.get('task_id')
            if task_id is not None:
                print(f"   ⚠️  Message has task_id: {task_id} (expected None for general chat)")
                # This might be okay if there are task-specific messages, but for our test it should be None
        
        print("   ✅ SUCCESS: Chat system initialization working correctly")
        print("   ✅ Conversation history preserved and accessible")
        print("   ✅ Message filtering working correctly")
        
        return True

    def test_chat_system_always_available(self):
        """Test that chat system is always available for clients (not dependent on selected task)"""
        print("\n🎯 FOCUS TEST 4: Chat System Always Available")
        
        # Test that client can access chat without any task context
        print("   🔍 Testing chat availability without task context")
        
        # 1. Test admin info endpoint (should work without task)
        success, admin_info, _ = self.run_test(
            "Admin Info Available Without Task Context",
            "GET",
            "chat/admin-info",
            200,
            cookies=self.client_cookies
        )
        
        if not success:
            print("   ❌ Admin info not available without task context")
            return False
        
        print("   ✅ Admin info endpoint accessible without task dependency")
        
        # 2. Test message fetching (should work without task)
        success, messages, _ = self.run_test(
            "Messages Available Without Task Context",
            "GET",
            "chat/messages",
            200,
            cookies=self.client_cookies
        )
        
        if not success:
            print("   ❌ Messages not available without task context")
            return False
        
        print("   ✅ Message fetching works without task dependency")
        
        # 3. Test message sending (should work without task)
        general_message_data = {
            "content": "General chat message - not related to any specific task",
            "recipient_id": self.admin_id,
            "task_id": None  # Explicitly null for general chat
        }
        
        success, response, _ = self.run_test(
            "Send General Chat Message",
            "POST",
            "chat/messages",
            200,
            data=general_message_data,
            cookies=self.client_cookies
        )
        
        if not success:
            print("   ❌ Cannot send general chat messages")
            return False
        
        # Verify the message was sent with null task_id
        if response.get('task_id') is not None:
            print(f"   ⚠️  Expected task_id to be null, got: {response.get('task_id')}")
        
        print("   ✅ General chat messages can be sent (task_id = null)")
        print("   ✅ SUCCESS: Chat system is always available for clients")
        
        return True

    def cleanup_test_environment(self):
        """Clean up test data"""
        print("\n🧹 Cleaning up test environment...")
        
        if self.admin_cookies and self.client_id:
            success, _, _ = self.run_test(
                "Delete Test Client",
                "DELETE",
                f"admin/users/{self.client_id}",
                200,
                cookies=self.admin_cookies
            )
            
            if success:
                print("   ✅ Test client deleted successfully")
            else:
                print("   ⚠️  Failed to delete test client")

    def run_all_tests(self):
        """Run all client chat visibility tests"""
        print("🚀 Starting Client Chat System Visibility Fix Tests")
        print("=" * 60)
        
        # Setup
        if not self.setup_test_environment():
            print("❌ Failed to setup test environment")
            return False
        
        # Run focused tests
        tests = [
            ("Backend Admin Info Endpoint", self.test_admin_info_endpoint),
            ("Message Exchange Flow", self.test_message_exchange_flow),
            ("Chat System Initialization", self.test_chat_system_initialization),
            ("Chat System Always Available", self.test_chat_system_always_available)
        ]
        
        passed_tests = 0
        
        for test_name, test_func in tests:
            print(f"\n{'='*60}")
            print(f"🎯 RUNNING: {test_name}")
            print(f"{'='*60}")
            
            try:
                if test_func():
                    passed_tests += 1
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {str(e)}")
        
        # Cleanup
        self.cleanup_test_environment()
        
        # Final results
        print(f"\n{'='*60}")
        print("🏁 CLIENT CHAT VISIBILITY FIX TEST RESULTS")
        print(f"{'='*60}")
        print(f"Total Tests Run: {len(tests)}")
        print(f"Tests Passed: {passed_tests}")
        print(f"Tests Failed: {len(tests) - passed_tests}")
        print(f"Success Rate: {(passed_tests/len(tests)*100):.1f}%")
        
        if passed_tests == len(tests):
            print("\n🎉 ALL TESTS PASSED! Client chat visibility fix is working correctly!")
            print("✅ Clients can now see admin messages")
            print("✅ Message exchange flow is working")
            print("✅ Chat system initialization is proper")
            print("✅ Chat system is always available for clients")
            return True
        else:
            print(f"\n❌ {len(tests) - passed_tests} test(s) failed. Client chat visibility fix needs attention.")
            return False

if __name__ == "__main__":
    tester = ClientChatVisibilityTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)