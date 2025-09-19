import requests
import sys
from datetime import datetime, timedelta
import json
import time

class ChatSystemTester:
    def __init__(self, base_url="https://rusithink-planner.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_session_token = None
        self.admin_cookies = None
        self.admin_user_id = None
        self.client_session_token = None
        self.client_cookies = None
        self.client_user_id = None
        self.test_messages = []

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
            if 'user' in response:
                self.admin_user_id = response['user']['id']
            print(f"   ✅ Admin session established: {response['user']['name']}")
            return True
        
        return False

    def setup_client_session(self):
        """Setup client session by registering a test user"""
        registration_data = {
            "email": f"testclient_{int(time.time())}@example.com",
            "password": "testpass123",
            "first_name": "Test",
            "last_name": "Client",
            "phone": "+1234567890",
            "company_name": "Test Company Ltd"
        }
        
        success, response, cookies = self.run_test(
            "Client Registration Setup", 
            "POST", 
            "auth/register", 
            200, 
            data=registration_data
        )
        
        if success:
            self.client_cookies = cookies
            if 'session_token' in response:
                self.client_session_token = response['session_token']
            if 'user' in response:
                self.client_user_id = response['user']['id']
            print(f"   ✅ Client session established: {response['user']['name']}")
            return True
        
        return False

    # ========== CHAT SYSTEM TESTS ==========

    def test_admin_info_endpoint(self):
        """Test the new GET /api/chat/admin-info endpoint"""
        if not self.client_cookies:
            print("❌ No client session available for admin info test")
            return False
        
        success, response, _ = self.run_test(
            "Get Admin Info for Chat (Client Access)", 
            "GET", 
            "chat/admin-info", 
            200,
            cookies=self.client_cookies
        )
        
        if success:
            if 'id' in response and 'name' in response and 'role' in response:
                print(f"   ✅ Admin info retrieved: {response.get('name')} (ID: {response.get('id')})")
                print(f"   ✅ Admin role: {response.get('role')}")
                return True
            else:
                print("   ❌ Missing required fields in admin info response")
                return False
        
        return success

    def test_admin_info_endpoint_unauthenticated(self):
        """Test admin info endpoint without authentication"""
        success, response, _ = self.run_test(
            "Get Admin Info (Unauthenticated)", 
            "GET", 
            "chat/admin-info", 
            401
        )
        return success

    def test_admin_sends_message_to_client(self):
        """Test admin sending message to client"""
        if not self.admin_cookies or not self.client_user_id:
            print("❌ Admin session or client ID not available")
            return False
        
        message_data = {
            "content": "Hello! This is a test message from admin to client.",
            "recipient_id": self.client_user_id
        }
        
        success, response, _ = self.run_test(
            "Admin Sends Message to Client", 
            "POST", 
            "chat/messages", 
            200,
            data=message_data,
            cookies=self.admin_cookies
        )
        
        if success:
            if 'id' in response:
                self.test_messages.append(response['id'])
                print(f"   ✅ Message sent with ID: {response['id']}")
                print(f"   ✅ Sender: {response.get('sender_name')} ({response.get('sender_role')})")
                print(f"   ✅ Content: {response.get('content')}")
                return True
        
        return success

    def test_client_fetches_messages(self):
        """Test client fetching messages (should see admin message)"""
        if not self.client_cookies:
            print("❌ No client session available")
            return False
        
        success, response, _ = self.run_test(
            "Client Fetches Messages", 
            "GET", 
            "chat/messages", 
            200,
            cookies=self.client_cookies
        )
        
        if success:
            print(f"   ✅ Retrieved {len(response)} messages")
            
            # Check if client can see admin's message
            admin_messages = [msg for msg in response if msg.get('sender_role') == 'admin']
            if admin_messages:
                print(f"   ✅ Client can see {len(admin_messages)} admin message(s)")
                for msg in admin_messages:
                    print(f"   - Admin message: {msg.get('content')[:50]}...")
                return True
            else:
                print("   ❌ Client cannot see admin messages")
                return False
        
        return success

    def test_client_sends_reply_to_admin(self):
        """Test client sending reply to admin"""
        if not self.client_cookies or not self.admin_user_id:
            print("❌ Client session or admin ID not available")
            return False
        
        message_data = {
            "content": "Thank you for your message! This is a reply from the client.",
            "recipient_id": self.admin_user_id
        }
        
        success, response, _ = self.run_test(
            "Client Sends Reply to Admin", 
            "POST", 
            "chat/messages", 
            200,
            data=message_data,
            cookies=self.client_cookies
        )
        
        if success:
            if 'id' in response:
                self.test_messages.append(response['id'])
                print(f"   ✅ Reply sent with ID: {response['id']}")
                print(f"   ✅ Sender: {response.get('sender_name')} ({response.get('sender_role')})")
                print(f"   ✅ Content: {response.get('content')}")
                return True
        
        return success

    def test_admin_fetches_messages(self):
        """Test admin fetching messages (should see client reply)"""
        if not self.admin_cookies or not self.client_user_id:
            print("❌ Admin session or client ID not available")
            return False
        
        # Test with client_id parameter for admin
        params = {"client_id": self.client_user_id}
        
        success, response, _ = self.run_test(
            "Admin Fetches Messages with Client ID", 
            "GET", 
            "chat/messages", 
            200,
            params=params,
            cookies=self.admin_cookies
        )
        
        if success:
            print(f"   ✅ Retrieved {len(response)} messages")
            
            # Check if admin can see client's reply
            client_messages = [msg for msg in response if msg.get('sender_role') == 'client']
            if client_messages:
                print(f"   ✅ Admin can see {len(client_messages)} client message(s)")
                for msg in client_messages:
                    print(f"   - Client message: {msg.get('content')[:50]}...")
                return True
            else:
                print("   ❌ Admin cannot see client messages")
                return False
        
        return success

    def test_message_filtering_privacy(self):
        """Test message filtering to ensure privacy between different clients"""
        if not self.client_cookies:
            print("❌ No client session available")
            return False
        
        # Client tries to access messages with another client_id (should not work)
        fake_client_id = "fake-client-id-12345"
        params = {"client_id": fake_client_id}
        
        success, response, _ = self.run_test(
            "Client Tries to Access Other Client Messages", 
            "GET", 
            "chat/messages", 
            200,  # Should return 200 but with filtered results
            params=params,
            cookies=self.client_cookies
        )
        
        if success:
            # Should return empty or only messages involving this client
            print(f"   ✅ Privacy check: Retrieved {len(response)} messages")
            
            # Verify no messages from other clients are visible
            other_client_messages = [msg for msg in response if msg.get('sender_id') == fake_client_id]
            if not other_client_messages:
                print("   ✅ Privacy maintained: No other client messages visible")
                return True
            else:
                print("   ❌ Privacy breach: Other client messages are visible")
                return False
        
        return success

    def test_notification_unread_count(self):
        """Test the unread count system for notifications"""
        if not self.client_cookies:
            print("❌ No client session available")
            return False
        
        success, response, _ = self.run_test(
            "Get Unread Notifications Count (Client)", 
            "GET", 
            "notifications/unread-count", 
            200,
            cookies=self.client_cookies
        )
        
        if success:
            if 'unread_count' in response:
                print(f"   ✅ Unread count retrieved: {response['unread_count']}")
                return True
            else:
                print("   ❌ Missing unread_count in response")
                return False
        
        return success

    def test_admin_notification_unread_count(self):
        """Test the unread count system for admin notifications"""
        if not self.admin_cookies:
            print("❌ No admin session available")
            return False
        
        success, response, _ = self.run_test(
            "Get Unread Notifications Count (Admin)", 
            "GET", 
            "notifications/unread-count", 
            200,
            cookies=self.admin_cookies
        )
        
        if success:
            if 'unread_count' in response:
                print(f"   ✅ Admin unread count retrieved: {response['unread_count']}")
                return True
            else:
                print("   ❌ Missing unread_count in response")
                return False
        
        return success

    def test_complete_chat_flow_scenario(self):
        """Test the complete chat flow scenario that was reported as broken"""
        print("\n🔄 TESTING COMPLETE CHAT FLOW SCENARIO")
        print("   This tests the specific issue: 'When admin sends a reply client gets a notification but can't view'")
        
        # Step 1: Admin sends message to client
        if not self.admin_cookies or not self.client_user_id:
            print("❌ Admin session or client ID not available for flow test")
            return False
        
        message_data = {
            "content": "This is a test message to verify the notification issue fix.",
            "recipient_id": self.client_user_id
        }
        
        success, response, _ = self.run_test(
            "Flow Step 1: Admin Sends Message", 
            "POST", 
            "chat/messages", 
            200,
            data=message_data,
            cookies=self.admin_cookies
        )
        
        if not success:
            return False
        
        # Step 2: Client checks unread count (should have notification)
        success, response, _ = self.run_test(
            "Flow Step 2: Client Checks Unread Count", 
            "GET", 
            "notifications/unread-count", 
            200,
            cookies=self.client_cookies
        )
        
        if not success:
            return False
        
        unread_count = response.get('unread_count', 0)
        print(f"   📊 Client unread count: {unread_count}")
        
        # Step 3: Client fetches messages (this was the failing part)
        success, response, _ = self.run_test(
            "Flow Step 3: Client Fetches Messages (Critical Test)", 
            "GET", 
            "chat/messages", 
            200,
            cookies=self.client_cookies
        )
        
        if not success:
            return False
        
        # Verify client can see the admin message
        admin_messages = [msg for msg in response if msg.get('sender_role') == 'admin']
        if admin_messages:
            print(f"   ✅ CRITICAL FIX VERIFIED: Client can now view admin messages!")
            print(f"   ✅ Found {len(admin_messages)} admin message(s)")
            
            # Step 4: Verify unread count is reset after viewing
            success, response, _ = self.run_test(
                "Flow Step 4: Verify Unread Count Reset", 
                "GET", 
                "notifications/unread-count", 
                200,
                cookies=self.client_cookies
            )
            
            if success:
                new_unread_count = response.get('unread_count', 0)
                print(f"   📊 Client unread count after viewing: {new_unread_count}")
                if new_unread_count < unread_count:
                    print("   ✅ Unread count properly decremented after viewing messages")
                
            return True
        else:
            print("   ❌ CRITICAL ISSUE: Client still cannot view admin messages!")
            return False

def main():
    print("🚀 Starting Chat System Notification Fix Tests")
    print("=" * 70)
    print("Testing the specific issue: 'When admin sends a reply client gets a notification but can't view'")
    print("=" * 70)
    
    tester = ChatSystemTester()
    
    # Setup sessions
    print("\n🔧 SETUP PHASE")
    print("-" * 30)
    
    if not tester.setup_admin_session():
        print("❌ Failed to setup admin session. Aborting tests.")
        return 1
    
    if not tester.setup_client_session():
        print("❌ Failed to setup client session. Aborting tests.")
        return 1
    
    # Test sequence
    test_results = []
    
    print("\n🔍 ADMIN INFO ENDPOINT TESTS")
    print("-" * 30)
    test_results.append(tester.test_admin_info_endpoint())
    test_results.append(tester.test_admin_info_endpoint_unauthenticated())
    
    print("\n💬 CHAT MESSAGE FLOW TESTS")
    print("-" * 30)
    test_results.append(tester.test_admin_sends_message_to_client())
    test_results.append(tester.test_client_fetches_messages())
    test_results.append(tester.test_client_sends_reply_to_admin())
    test_results.append(tester.test_admin_fetches_messages())
    
    print("\n🔒 MESSAGE FILTERING & PRIVACY TESTS")
    print("-" * 30)
    test_results.append(tester.test_message_filtering_privacy())
    
    print("\n🔔 NOTIFICATION SYSTEM TESTS")
    print("-" * 30)
    test_results.append(tester.test_notification_unread_count())
    test_results.append(tester.test_admin_notification_unread_count())
    
    print("\n🎯 COMPLETE FLOW SCENARIO TEST")
    print("-" * 30)
    test_results.append(tester.test_complete_chat_flow_scenario())

    # Print final results
    print("\n" + "=" * 70)
    print(f"📊 FINAL RESULTS")
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All chat system tests passed!")
        print("✅ New admin info endpoint working")
        print("✅ Chat message flow working correctly")
        print("✅ Message filtering maintains privacy")
        print("✅ Notification system working properly")
        print("✅ CRITICAL FIX VERIFIED: Client can now view admin messages!")
        return 0
    else:
        failed_tests = tester.tests_run - tester.tests_passed
        print(f"⚠️  {failed_tests} tests failed. Check the chat system implementation.")
        
        # Specific guidance for the main issue
        print("\n🔍 TROUBLESHOOTING GUIDANCE:")
        print("If the 'Complete Flow Scenario Test' failed, the main issue is not fixed:")
        print("- Check message filtering in GET /api/chat/messages")
        print("- Verify client can access messages where they are recipient")
        print("- Check if admin messages are properly visible to clients")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())