#!/usr/bin/env python3
"""
Focused Chat Message Visibility Debug Test
Testing the specific issue: "Admin chat box works fine but client doesn't get admin's messages"
"""

import requests
import json
from datetime import datetime, timedelta

class ChatDebugTester:
    def __init__(self, base_url="https://rusithink-planner.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.admin_cookies = None
        self.client_cookies = None
        self.admin_id = None
        self.client_id = None
        
    def login_admin(self):
        """Login as admin"""
        login_data = {
            "username": "rusithink",
            "password": "20200104Rh"
        }
        
        response = requests.post(f"{self.api_url}/auth/admin-login", json=login_data)
        if response.status_code == 200:
            self.admin_cookies = response.cookies
            data = response.json()
            self.admin_id = data['user']['id']
            print(f"✅ Admin logged in: {data['user']['name']} (ID: {self.admin_id})")
            return True
        else:
            print(f"❌ Admin login failed: {response.status_code}")
            return False
    
    def create_test_client(self):
        """Create a test client"""
        client_data = {
            "email": "debug_client@example.com",
            "password": "testpass123",
            "first_name": "Debug",
            "last_name": "Client",
            "phone": "+1234567890",
            "company_name": "Debug Test Company"
        }
        
        response = requests.post(f"{self.api_url}/auth/register", json=client_data)
        if response.status_code == 200:
            self.client_cookies = response.cookies
            data = response.json()
            self.client_id = data['user']['id']
            print(f"✅ Test client created: {data['user']['name']} (ID: {self.client_id})")
            return True
        else:
            print(f"❌ Client creation failed: {response.status_code}")
            return False
    
    def admin_send_message_to_client(self, message_content):
        """Admin sends message to client"""
        message_data = {
            "content": message_content,
            "recipient_id": self.client_id
        }
        
        response = requests.post(f"{self.api_url}/chat/messages", json=message_data, cookies=self.admin_cookies)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Admin message sent: '{message_content}' (ID: {data['id']})")
            return data['id']
        else:
            print(f"❌ Admin message failed: {response.status_code} - {response.text}")
            return None
    
    def client_fetch_messages(self):
        """Client fetches messages"""
        response = requests.get(f"{self.api_url}/chat/messages", cookies=self.client_cookies)
        if response.status_code == 200:
            messages = response.json()
            print(f"✅ Client fetched {len(messages)} messages")
            return messages
        else:
            print(f"❌ Client message fetch failed: {response.status_code} - {response.text}")
            return []
    
    def client_send_message_to_admin(self, message_content):
        """Client sends message to admin"""
        message_data = {
            "content": message_content,
            "recipient_id": self.admin_id
        }
        
        response = requests.post(f"{self.api_url}/chat/messages", json=message_data, cookies=self.client_cookies)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Client message sent: '{message_content}' (ID: {data['id']})")
            return data['id']
        else:
            print(f"❌ Client message failed: {response.status_code} - {response.text}")
            return None
    
    def admin_fetch_client_messages(self):
        """Admin fetches messages with specific client"""
        response = requests.get(f"{self.api_url}/chat/messages?client_id={self.client_id}", cookies=self.admin_cookies)
        if response.status_code == 200:
            messages = response.json()
            print(f"✅ Admin fetched {len(messages)} messages with client")
            return messages
        else:
            print(f"❌ Admin message fetch failed: {response.status_code} - {response.text}")
            return []
    
    def cleanup_test_client(self):
        """Delete test client"""
        if self.client_id and self.admin_cookies:
            response = requests.delete(f"{self.api_url}/admin/users/{self.client_id}", cookies=self.admin_cookies)
            if response.status_code == 200:
                print(f"✅ Test client cleaned up")
            else:
                print(f"⚠️ Cleanup failed: {response.status_code}")
    
    def run_debug_test(self):
        """Run the complete debug test"""
        print("🔍 CHAT MESSAGE VISIBILITY DEBUG TEST")
        print("=" * 50)
        print("Testing: Admin → Client Message Flow")
        print("Issue: 'Admin chat box works fine but client doesn't get admin's messages'")
        print()
        
        # Step 1: Setup
        if not self.login_admin():
            return False
        
        if not self.create_test_client():
            return False
        
        print()
        print("📝 STEP 1: Admin sends message to client")
        print("-" * 40)
        admin_msg_id = self.admin_send_message_to_client("Hello from admin - debug test message")
        if not admin_msg_id:
            return False
        
        print()
        print("📥 STEP 2: Client fetches messages")
        print("-" * 40)
        client_messages = self.client_fetch_messages()
        
        # Check if client can see admin message
        admin_message_found = False
        for msg in client_messages:
            if msg.get('id') == admin_msg_id:
                admin_message_found = True
                print(f"✅ SUCCESS: Client can see admin message!")
                print(f"   Message: '{msg.get('content')}'")
                print(f"   From: {msg.get('sender_name')} ({msg.get('sender_role')})")
                break
        
        if not admin_message_found:
            print("❌ CRITICAL ISSUE: Client CANNOT see admin message!")
            print("📋 Messages client received:")
            for i, msg in enumerate(client_messages):
                print(f"   {i+1}. From: {msg.get('sender_name')} - '{msg.get('content')[:50]}...'")
            return False
        
        print()
        print("📝 STEP 3: Client sends reply to admin")
        print("-" * 40)
        client_msg_id = self.client_send_message_to_admin("Reply from client - debug test response")
        if not client_msg_id:
            return False
        
        print()
        print("📥 STEP 4: Admin fetches conversation with client")
        print("-" * 40)
        admin_messages = self.admin_fetch_client_messages()
        
        # Check if admin can see both messages
        admin_msg_found = False
        client_msg_found = False
        
        for msg in admin_messages:
            if msg.get('id') == admin_msg_id:
                admin_msg_found = True
                print(f"✅ Admin can see their own message: '{msg.get('content')[:50]}...'")
            elif msg.get('id') == client_msg_id:
                client_msg_found = True
                print(f"✅ Admin can see client reply: '{msg.get('content')[:50]}...'")
        
        if not admin_msg_found:
            print("❌ Admin cannot see their own message in conversation")
            return False
        
        if not client_msg_found:
            print("❌ Admin cannot see client reply")
            return False
        
        print()
        print("📥 STEP 5: Client fetches messages again (bidirectional test)")
        print("-" * 40)
        final_client_messages = self.client_fetch_messages()
        
        # Check if client can see both messages
        admin_msg_found_final = False
        client_msg_found_final = False
        
        print(f"📋 Client received {len(final_client_messages)} messages:")
        for i, msg in enumerate(final_client_messages):
            sender_name = msg.get('sender_name', 'Unknown')
            content_preview = msg.get('content', '')[:40]
            print(f"   {i+1}. From: {sender_name} - '{content_preview}...'")
            
            if msg.get('id') == admin_msg_id:
                admin_msg_found_final = True
            elif msg.get('id') == client_msg_id:
                client_msg_found_final = True
        
        if not admin_msg_found_final:
            print("❌ CRITICAL: Client cannot see admin message in final fetch!")
            return False
        else:
            print("✅ SUCCESS: Client can see admin message in bidirectional conversation")
        
        if not client_msg_found_final:
            print("❌ CRITICAL: Client's own message disappeared!")
            return False
        else:
            print("✅ SUCCESS: Client's own message preserved")
        
        print()
        print("🎉 CHAT MESSAGE VISIBILITY DEBUG TEST: PASSED!")
        print("✅ Admin → Client message flow working correctly")
        print("✅ Client can fetch and see admin messages")
        print("✅ Bidirectional message flow working")
        print("✅ Message parameters working correctly")
        
        # Cleanup
        self.cleanup_test_client()
        return True

if __name__ == "__main__":
    tester = ChatDebugTester()
    success = tester.run_debug_test()
    
    if success:
        print("\n🎯 CONCLUSION: The chat message visibility issue has been RESOLVED!")
        print("The reported problem 'Admin chat box works fine but client doesn't get admin's messages' is FIXED.")
    else:
        print("\n❌ CONCLUSION: Chat message visibility issue still exists!")
        print("Further debugging required.")