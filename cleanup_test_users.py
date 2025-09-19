#!/usr/bin/env python3

import requests
import json

def cleanup_test_users():
    base_url = "https://rusithink-manage.preview.emergentagent.com"
    api_url = f"{base_url}/api"
    
    # Login as admin
    login_data = {
        "username": "rusithink",
        "password": "20200104Rh"
    }
    
    print("🔐 Logging in as admin...")
    response = requests.post(f"{api_url}/auth/admin-login", json=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    admin_cookies = response.cookies
    print("✅ Admin login successful")
    
    # Get all users
    response = requests.get(f"{api_url}/admin/users", cookies=admin_cookies)
    if response.status_code != 200:
        print(f"❌ Failed to get users: {response.status_code}")
        return False
    
    users = response.json()
    
    # Find test users to delete
    test_emails = [
        "bulk_delete_test1@example.com",
        "bulk_delete_test2@example.com",
        "testclient1@example.com",
        "testclient2@example.com",
        "testclient3@example.com"
    ]
    
    users_to_delete = []
    for user in users:
        if user.get('email') in test_emails:
            users_to_delete.append(user['id'])
            print(f"Found test user to delete: {user['email']} (ID: {user['id']})")
    
    if users_to_delete:
        print(f"\n🗑️  Deleting {len(users_to_delete)} test users...")
        for user_id in users_to_delete:
            response = requests.delete(f"{api_url}/admin/users/{user_id}", cookies=admin_cookies)
            if response.status_code == 200:
                print(f"✅ Deleted user: {user_id}")
            else:
                print(f"❌ Failed to delete user {user_id}: {response.status_code}")
    else:
        print("No test users found to delete")
    
    return True

if __name__ == "__main__":
    cleanup_test_users()