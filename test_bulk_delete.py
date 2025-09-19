#!/usr/bin/env python3

import requests
import json

def test_bulk_delete():
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
    
    # Create test users
    test_users = [
        {
            "email": "bulk_delete_test1@example.com",
            "password": "testpass123",
            "first_name": "BulkDelete",
            "last_name": "Test1",
            "phone": "+1111111111",
            "company_name": "Bulk Delete Test Company 1"
        },
        {
            "email": "bulk_delete_test2@example.com",
            "password": "testpass123",
            "first_name": "BulkDelete",
            "last_name": "Test2",
            "phone": "+2222222222",
            "company_name": "Bulk Delete Test Company 2"
        }
    ]
    
    created_user_ids = []
    
    print("\n👥 Creating test users...")
    for user_data in test_users:
        response = requests.post(f"{api_url}/auth/register", json=user_data)
        if response.status_code == 200:
            user_id = response.json()['user']['id']
            created_user_ids.append(user_id)
            print(f"✅ Created user: {user_data['email']} (ID: {user_id})")
        else:
            print(f"❌ Failed to create user {user_data['email']}: {response.status_code}")
    
    if len(created_user_ids) < 2:
        print("❌ Not enough users created for bulk delete test")
        return False
    
    # Test bulk delete
    print(f"\n🗑️  Testing bulk delete with user IDs: {created_user_ids}")
    
    response = requests.delete(
        f"{api_url}/admin/users/bulk",
        json=created_user_ids,
        headers={'Content-Type': 'application/json'},
        cookies=admin_cookies
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    print(f"Response text: {response.text}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Bulk delete successful!")
        print(f"   Deleted count: {result.get('deleted_count')}")
        print(f"   Message: {result.get('message')}")
        print(f"   Errors: {result.get('errors')}")
        return True
    else:
        print(f"❌ Bulk delete failed: {response.status_code}")
        return False

if __name__ == "__main__":
    test_bulk_delete()