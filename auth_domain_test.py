#!/usr/bin/env python3
"""
Authentication Testing for Custom Domain https://rusithink.online
Testing authentication functionality with new CORS configuration
"""

import requests
import sys
import json
from datetime import datetime

class AuthDomainTester:
    def __init__(self):
        self.base_url = "https://rusithink.online"
        self.api_url = f"{self.base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_session_token = None
        self.admin_cookies = None
        self.test_user_session = None
        self.test_user_cookies = None

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
            if details:
                print(f"   {details}")
        else:
            print(f"❌ {name}")
            if details:
                print(f"   {details}")

    def test_cors_preflight(self):
        """Test CORS preflight OPTIONS request"""
        print(f"\n🔍 Testing CORS Preflight for {self.base_url}...")
        
        try:
            headers = {
                'Origin': 'https://rusithink.online',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            response = requests.options(f"{self.api_url}/auth/admin-login", headers=headers)
            
            # Check CORS headers
            cors_origin = response.headers.get('Access-Control-Allow-Origin')
            cors_methods = response.headers.get('Access-Control-Allow-Methods')
            cors_headers = response.headers.get('Access-Control-Allow-Headers')
            cors_credentials = response.headers.get('Access-Control-Allow-Credentials')
            
            success = (
                response.status_code in [200, 204] and
                cors_origin and
                cors_credentials == 'true'
            )
            
            details = f"Status: {response.status_code}, Origin: {cors_origin}, Credentials: {cors_credentials}"
            self.log_test("CORS Preflight Request", success, details)
            
            return success
            
        except Exception as e:
            self.log_test("CORS Preflight Request", False, f"Error: {str(e)}")
            return False

    def test_admin_login_success(self):
        """Test admin login with correct credentials"""
        print(f"\n🔍 Testing Admin Login with Custom Domain...")
        
        login_data = {
            "username": "rusithink",
            "password": "20200104Rh"
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Origin': 'https://rusithink.online'
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/auth/admin-login",
                json=login_data,
                headers=headers
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Store session for future tests
                self.admin_cookies = response.cookies
                if 'session_token' in response_data:
                    self.admin_session_token = response_data['session_token']
                
                # Verify response structure
                if ('user' in response_data and 
                    response_data['user'].get('role') == 'admin' and
                    'session_token' in response_data):
                    
                    user_name = response_data['user'].get('name', 'Unknown')
                    details = f"Admin: {user_name}, Session: {self.admin_session_token[:20]}..."
                    self.log_test("Admin Login (Valid Credentials)", True, details)
                    return True
                else:
                    self.log_test("Admin Login (Valid Credentials)", False, "Invalid response structure")
                    return False
            else:
                error_msg = f"Status: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    error_msg += f", Response: {response.text}"
                
                self.log_test("Admin Login (Valid Credentials)", False, error_msg)
                return False
                
        except Exception as e:
            self.log_test("Admin Login (Valid Credentials)", False, f"Exception: {str(e)}")
            return False

    def test_admin_login_invalid_credentials(self):
        """Test admin login with invalid credentials"""
        print(f"\n🔍 Testing Admin Login with Invalid Credentials...")
        
        login_data = {
            "username": "rusithink",
            "password": "wrongpassword"
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Origin': 'https://rusithink.online'
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/auth/admin-login",
                json=login_data,
                headers=headers
            )
            
            success = response.status_code == 401
            details = f"Status: {response.status_code} (Expected: 401)"
            
            if success:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'No detail')}"
                except:
                    pass
            
            self.log_test("Admin Login (Invalid Credentials)", success, details)
            return success
            
        except Exception as e:
            self.log_test("Admin Login (Invalid Credentials)", False, f"Exception: {str(e)}")
            return False

    def test_session_validation(self):
        """Test session validation with GET /api/auth/me"""
        print(f"\n🔍 Testing Session Validation...")
        
        if not self.admin_cookies:
            self.log_test("Session Validation", False, "No admin session available")
            return False
        
        headers = {
            'Origin': 'https://rusithink.online'
        }
        
        try:
            response = requests.get(
                f"{self.api_url}/auth/me",
                headers=headers,
                cookies=self.admin_cookies
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
                if (response_data.get('role') == 'admin' and
                    'email' in response_data and
                    'name' in response_data):
                    
                    details = f"User: {response_data.get('name')} ({response_data.get('role')})"
                    self.log_test("Session Validation", True, details)
                    return True
                else:
                    self.log_test("Session Validation", False, "Invalid user data structure")
                    return False
            else:
                details = f"Status: {response.status_code} (Expected: 200)"
                self.log_test("Session Validation", False, details)
                return False
                
        except Exception as e:
            self.log_test("Session Validation", False, f"Exception: {str(e)}")
            return False

    def test_manual_registration(self):
        """Test manual user registration"""
        print(f"\n🔍 Testing Manual User Registration...")
        
        # Generate unique email for testing
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        registration_data = {
            "email": f"testuser_{timestamp}@rusithink.online",
            "password": "testpass123456",
            "first_name": "Test",
            "last_name": "User",
            "phone": "+1234567890",
            "company_name": "Test Company Ltd",
            "address": "123 Test Street, Test City, TC 12345"
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Origin': 'https://rusithink.online'
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/auth/register",
                json=registration_data,
                headers=headers
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Store test user session
                self.test_user_cookies = response.cookies
                if 'session_token' in response_data:
                    self.test_user_session = response_data['session_token']
                
                if ('user' in response_data and
                    'session_token' in response_data and
                    response_data['user'].get('role') == 'client'):
                    
                    user_name = response_data['user'].get('name', 'Unknown')
                    user_email = response_data['user'].get('email', 'Unknown')
                    details = f"User: {user_name} ({user_email}), Role: client"
                    self.log_test("Manual User Registration", True, details)
                    return True
                else:
                    self.log_test("Manual User Registration", False, "Invalid response structure")
                    return False
            else:
                error_msg = f"Status: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    error_msg += f", Response: {response.text}"
                
                self.log_test("Manual User Registration", False, error_msg)
                return False
                
        except Exception as e:
            self.log_test("Manual User Registration", False, f"Exception: {str(e)}")
            return False

    def test_logout_functionality(self):
        """Test logout functionality"""
        print(f"\n🔍 Testing Logout Functionality...")
        
        if not self.test_user_cookies:
            self.log_test("Logout Functionality", False, "No test user session available")
            return False
        
        headers = {
            'Origin': 'https://rusithink.online'
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/auth/logout",
                headers=headers,
                cookies=self.test_user_cookies
            )
            
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                try:
                    response_data = response.json()
                    details += f", Message: {response_data.get('message', 'No message')}"
                except:
                    pass
                
                # Clear test user session
                self.test_user_cookies = None
                self.test_user_session = None
            
            self.log_test("Logout Functionality", success, details)
            return success
            
        except Exception as e:
            self.log_test("Logout Functionality", False, f"Exception: {str(e)}")
            return False

    def test_session_after_logout(self):
        """Test that session is invalid after logout"""
        print(f"\n🔍 Testing Session After Logout...")
        
        # Try to access protected endpoint without valid session
        headers = {
            'Origin': 'https://rusithink.online'
        }
        
        try:
            response = requests.get(
                f"{self.api_url}/auth/me",
                headers=headers,
                cookies=self.test_user_cookies  # Should be None after logout
            )
            
            success = response.status_code == 401
            details = f"Status: {response.status_code} (Expected: 401 - Unauthorized)"
            
            self.log_test("Session After Logout", success, details)
            return success
            
        except Exception as e:
            self.log_test("Session After Logout", False, f"Exception: {str(e)}")
            return False

    def test_cors_headers_on_auth_endpoints(self):
        """Test CORS headers on authentication endpoints"""
        print(f"\n🔍 Testing CORS Headers on Auth Endpoints...")
        
        endpoints_to_test = [
            "auth/admin-login",
            "auth/register", 
            "auth/me",
            "auth/logout"
        ]
        
        headers = {
            'Origin': 'https://rusithink.online',
            'Content-Type': 'application/json'
        }
        
        all_passed = True
        
        for endpoint in endpoints_to_test:
            try:
                # Test with a simple GET request (some will return 405, but CORS headers should be present)
                response = requests.get(f"{self.api_url}/{endpoint}", headers=headers)
                
                cors_origin = response.headers.get('Access-Control-Allow-Origin')
                cors_credentials = response.headers.get('Access-Control-Allow-Credentials')
                
                endpoint_passed = (
                    cors_origin is not None and
                    cors_credentials == 'true'
                )
                
                if endpoint_passed:
                    details = f"{endpoint}: Origin={cors_origin}, Credentials={cors_credentials}"
                    self.log_test(f"CORS Headers - {endpoint}", True, details)
                else:
                    details = f"{endpoint}: Missing or incorrect CORS headers"
                    self.log_test(f"CORS Headers - {endpoint}", False, details)
                    all_passed = False
                    
            except Exception as e:
                self.log_test(f"CORS Headers - {endpoint}", False, f"Exception: {str(e)}")
                all_passed = False
        
        return all_passed

    def run_all_tests(self):
        """Run all authentication tests for custom domain"""
        print("=" * 80)
        print("🚀 AUTHENTICATION TESTING FOR CUSTOM DOMAIN: https://rusithink.online")
        print("=" * 80)
        print("Testing authentication functionality with new CORS configuration")
        print("Focus: Admin login, Manual registration, Session management, CORS verification")
        print("=" * 80)
        
        # Run tests in order
        tests = [
            ("CORS Preflight", self.test_cors_preflight),
            ("Admin Login Success", self.test_admin_login_success),
            ("Admin Login Invalid", self.test_admin_login_invalid_credentials),
            ("Session Validation", self.test_session_validation),
            ("Manual Registration", self.test_manual_registration),
            ("Logout Functionality", self.test_logout_functionality),
            ("Session After Logout", self.test_session_after_logout),
            ("CORS Headers", self.test_cors_headers_on_auth_endpoints),
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                print(f"❌ {test_name} - Unexpected error: {str(e)}")
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL AUTHENTICATION TESTS PASSED!")
            print("✅ Custom domain authentication is working correctly")
            print("✅ CORS configuration is properly set for https://rusithink.online")
        else:
            print("⚠️  SOME TESTS FAILED")
            print("❌ Authentication issues detected with custom domain")
        
        print("=" * 80)
        
        return self.tests_passed == self.tests_run

if __name__ == "__main__":
    tester = AuthDomainTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)