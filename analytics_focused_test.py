#!/usr/bin/env python3
"""
Focused Analytics Testing Script for RusiThink Project Planning Software
Testing the specific analytics endpoints that user reported as failing:
- Admin Analytics Endpoint: GET /api/analytics/admin
- Client Analytics Endpoint: GET /api/analytics/client  
- Analytics Calculation: POST /api/analytics/calculate

User reported: "Failed to load analytics" error and $0 revenue showing in frontend
"""

import requests
import sys
from datetime import datetime, timedelta
import json

class AnalyticsFocusedTester:
    def __init__(self, base_url="https://rusithink-planner.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_cookies = None
        self.client_cookies = None
        self.test_client_id = None
        self.test_tasks_created = []

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

    def setup_admin_session(self):
        """Login as admin with provided credentials"""
        print("\n🔐 Setting up Admin Session...")
        
        login_data = {
            "username": "rusithink",
            "password": "20200104Rh"
        }
        
        success, response, cookies = self.run_test(
            "Admin Login", 
            "POST", 
            "auth/admin-login", 
            200, 
            data=login_data
        )
        
        if success:
            self.admin_cookies = cookies
            print(f"   ✅ Admin authenticated: {response['user']['name']}")
            return True
        else:
            print("   ❌ Admin login failed - cannot proceed with analytics tests")
            return False

    def setup_test_client_with_data(self):
        """Create a test client with some tasks for analytics testing"""
        print("\n👤 Setting up Test Client with Sample Data...")
        
        # Create test client
        test_user_data = {
            "email": "analytics_test_client@example.com",
            "password": "testpass123",
            "first_name": "Analytics",
            "last_name": "TestClient",
            "phone": "+1234567890",
            "company_name": "Analytics Test Company",
            "address": "123 Analytics Street"
        }
        
        success, response, cookies = self.run_test(
            "Create Test Client for Analytics",
            "POST",
            "auth/register",
            200,
            data=test_user_data
        )
        
        if not success:
            print("   ❌ Could not create test client")
            return False
        
        self.client_cookies = cookies
        self.test_client_id = response['user']['id']
        print(f"   ✅ Created test client: {response['user']['name']} (ID: {self.test_client_id})")
        
        # Create some test tasks with different prices and dates
        test_tasks = [
            {
                "title": "Analytics Test Project 1 - Website Redesign",
                "description": "Complete website redesign project",
                "due_datetime": (datetime.now() + timedelta(days=30)).isoformat(),
                "project_price": 5000.0,
                "priority": "high"
            },
            {
                "title": "Analytics Test Project 2 - Mobile App",
                "description": "Mobile application development",
                "due_datetime": (datetime.now() + timedelta(days=45)).isoformat(),
                "project_price": 8000.0,
                "priority": "medium"
            },
            {
                "title": "Analytics Test Project 3 - SEO Optimization",
                "description": "Search engine optimization project",
                "due_datetime": (datetime.now() + timedelta(days=60)).isoformat(),
                "project_price": 2500.0,
                "priority": "low"
            }
        ]
        
        created_tasks = 0
        for i, task_data in enumerate(test_tasks):
            success, task_response, _ = self.run_test(
                f"Create Analytics Test Task {i+1}",
                "POST",
                "tasks",
                200,
                data=task_data,
                cookies=self.client_cookies
            )
            
            if success:
                created_tasks += 1
                self.test_tasks_created.append(task_response['id'])
                print(f"   ✅ Created task: {task_response['title']} (${task_response['project_price']})")
        
        print(f"   ✅ Created {created_tasks} test tasks with total value: $15,500")
        return created_tasks > 0

    def test_client_analytics_endpoint(self):
        """Test GET /api/analytics/client endpoint"""
        print("\n📊 TESTING CLIENT ANALYTICS ENDPOINT...")
        
        if not self.client_cookies:
            print("❌ No client session available")
            return False
        
        success, analytics_response, _ = self.run_test(
            "Get Client Analytics",
            "GET",
            "analytics/client",
            200,
            cookies=self.client_cookies
        )
        
        if not success:
            print("❌ CRITICAL: Client analytics endpoint failed")
            return False
        
        # Verify analytics data structure
        required_fields = [
            'client_id', 'total_projects', 'completed_projects', 'pending_projects',
            'total_spent', 'average_project_value', 'monthly_spending', 'project_completion_rate'
        ]
        
        missing_fields = [field for field in required_fields if field not in analytics_response]
        if missing_fields:
            print(f"❌ Missing analytics fields: {missing_fields}")
            return False
        
        print(f"   ✅ Analytics structure correct - all required fields present")
        print(f"   📈 Total projects: {analytics_response.get('total_projects')}")
        print(f"   💰 Total spent: ${analytics_response.get('total_spent')}")
        print(f"   📊 Average project value: ${analytics_response.get('average_project_value')}")
        print(f"   📅 Monthly spending: {analytics_response.get('monthly_spending')}")
        
        # Check for $0 revenue issue
        total_spent = analytics_response.get('total_spent', 0)
        if total_spent == 0:
            print("   ⚠️  WARNING: Total spent is $0 - this might be the issue user reported!")
            print("   🔍 Expected total spent: $15,500 (from test tasks created)")
            return False
        else:
            print(f"   ✅ Revenue data looks correct: ${total_spent}")
        
        return True

    def test_admin_analytics_endpoint(self):
        """Test GET /api/analytics/admin endpoint with different month parameters"""
        print("\n📈 TESTING ADMIN ANALYTICS ENDPOINT...")
        
        if not self.admin_cookies:
            print("❌ No admin session available")
            return False
        
        # Test with different month parameters as specified in review request
        month_params = [6, 12, 24]
        all_tests_passed = True
        
        for months in month_params:
            print(f"\n   🗓️  Testing with {months} months parameter...")
            
            success, analytics_response, _ = self.run_test(
                f"Get Admin Analytics ({months} months)",
                "GET",
                f"analytics/admin?months={months}",
                200,
                cookies=self.admin_cookies
            )
            
            if not success:
                print(f"❌ CRITICAL: Admin analytics failed for {months} months")
                all_tests_passed = False
                continue
            
            # Verify response structure
            if not isinstance(analytics_response, list):
                print(f"❌ Expected list response, got: {type(analytics_response)}")
                all_tests_passed = False
                continue
            
            print(f"   ✅ Admin analytics returned {len(analytics_response)} months of data")
            
            # Check for $0 revenue issue in admin analytics
            total_revenue_found = False
            for month_data in analytics_response:
                if month_data.get('total_revenue', 0) > 0:
                    total_revenue_found = True
                    print(f"   💰 Found revenue in {month_data.get('month_year')}: ${month_data.get('total_revenue')}")
                    break
            
            if not total_revenue_found:
                print(f"   ⚠️  WARNING: No revenue found in {months} months data - this might be the $0 issue!")
                # Don't fail the test yet, might be expected if no completed projects
            
            # Verify required fields in each month's data
            if analytics_response:
                sample_month = analytics_response[0]
                required_fields = [
                    'month_year', 'total_revenue', 'total_projects', 'completed_projects',
                    'pending_projects', 'new_clients', 'active_clients', 'average_project_value',
                    'project_completion_rate', 'revenue_by_client'
                ]
                
                missing_fields = [field for field in required_fields if field not in sample_month]
                if missing_fields:
                    print(f"   ❌ Missing fields in admin analytics: {missing_fields}")
                    all_tests_passed = False
                else:
                    print(f"   ✅ Admin analytics structure correct for {months} months")
        
        return all_tests_passed

    def test_analytics_calculation_endpoint(self):
        """Test POST /api/analytics/calculate endpoint"""
        print("\n🔄 TESTING ANALYTICS CALCULATION ENDPOINT...")
        
        if not self.admin_cookies:
            print("❌ No admin session available")
            return False
        
        success, calc_response, _ = self.run_test(
            "Recalculate All Analytics",
            "POST",
            "analytics/calculate",
            200,
            cookies=self.admin_cookies
        )
        
        if not success:
            print("❌ CRITICAL: Analytics calculation endpoint failed")
            return False
        
        # Verify calculation response structure
        required_fields = ['clients_processed', 'admin_months_processed']
        missing_fields = [field for field in required_fields if field not in calc_response]
        
        if missing_fields:
            print(f"❌ Missing calculation response fields: {missing_fields}")
            return False
        
        print(f"   ✅ Analytics calculation completed successfully")
        print(f"   👥 Clients processed: {calc_response.get('clients_processed')}")
        print(f"   📅 Admin months processed: {calc_response.get('admin_months_processed')}")
        
        return True

    def test_analytics_after_calculation(self):
        """Test analytics endpoints after running calculation to see if data improves"""
        print("\n🔍 TESTING ANALYTICS AFTER RECALCULATION...")
        
        # Test client analytics again
        if self.client_cookies:
            success, client_analytics, _ = self.run_test(
                "Get Client Analytics (After Calculation)",
                "GET",
                "analytics/client",
                200,
                cookies=self.client_cookies
            )
            
            if success:
                total_spent = client_analytics.get('total_spent', 0)
                print(f"   📊 Client total spent after calculation: ${total_spent}")
                if total_spent > 0:
                    print("   ✅ Client analytics showing revenue after calculation")
                else:
                    print("   ⚠️  Client analytics still showing $0 after calculation")
        
        # Test admin analytics again
        if self.admin_cookies:
            success, admin_analytics, _ = self.run_test(
                "Get Admin Analytics (After Calculation)",
                "GET",
                "analytics/admin?months=12",
                200,
                cookies=self.admin_cookies
            )
            
            if success and admin_analytics:
                revenue_found = any(month.get('total_revenue', 0) > 0 for month in admin_analytics)
                if revenue_found:
                    print("   ✅ Admin analytics showing revenue after calculation")
                else:
                    print("   ⚠️  Admin analytics still showing $0 revenue after calculation")

    def test_authentication_requirements(self):
        """Test that analytics endpoints require proper authentication"""
        print("\n🔐 TESTING AUTHENTICATION REQUIREMENTS...")
        
        # Test client analytics without auth
        success, _, _ = self.run_test(
            "Client Analytics (No Auth)",
            "GET",
            "analytics/client",
            401
        )
        
        if success:
            print("   ✅ Client analytics properly requires authentication")
        
        # Test admin analytics without auth
        success, _, _ = self.run_test(
            "Admin Analytics (No Auth)",
            "GET",
            "analytics/admin",
            401
        )
        
        if success:
            print("   ✅ Admin analytics properly requires authentication")
        
        # Test analytics calculation without auth
        success, _, _ = self.run_test(
            "Analytics Calculation (No Auth)",
            "POST",
            "analytics/calculate",
            401
        )
        
        if success:
            print("   ✅ Analytics calculation properly requires authentication")
        
        return True

    def cleanup_test_data(self):
        """Clean up test client and data"""
        print("\n🧹 Cleaning up test data...")
        
        if self.admin_cookies and self.test_client_id:
            success, _, _ = self.run_test(
                "Delete Test Client",
                "DELETE",
                f"admin/users/{self.test_client_id}",
                200,
                cookies=self.admin_cookies
            )
            
            if success:
                print("   ✅ Test client and associated data cleaned up")

    def run_all_analytics_tests(self):
        """Run all analytics-focused tests"""
        print("🚀 STARTING FOCUSED ANALYTICS TESTING")
        print("=" * 60)
        print("Testing analytics endpoints that user reported as failing:")
        print("- Admin Analytics: GET /api/analytics/admin")
        print("- Client Analytics: GET /api/analytics/client")
        print("- Analytics Calculation: POST /api/analytics/calculate")
        print("=" * 60)
        
        # Setup
        if not self.setup_admin_session():
            return False
        
        if not self.setup_test_client_with_data():
            return False
        
        # Run authentication tests first
        self.test_authentication_requirements()
        
        # Run core analytics tests
        client_analytics_passed = self.test_client_analytics_endpoint()
        admin_analytics_passed = self.test_admin_analytics_endpoint()
        calculation_passed = self.test_analytics_calculation_endpoint()
        
        # Test analytics after calculation
        self.test_analytics_after_calculation()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 ANALYTICS TESTING SUMMARY")
        print("=" * 60)
        print(f"Total tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        print("\n🎯 CRITICAL ANALYTICS ENDPOINTS:")
        print(f"   Client Analytics: {'✅ WORKING' if client_analytics_passed else '❌ FAILING'}")
        print(f"   Admin Analytics: {'✅ WORKING' if admin_analytics_passed else '❌ FAILING'}")
        print(f"   Analytics Calculation: {'✅ WORKING' if calculation_passed else '❌ FAILING'}")
        
        if not client_analytics_passed or not admin_analytics_passed or not calculation_passed:
            print("\n⚠️  CRITICAL ISSUES FOUND:")
            if not client_analytics_passed:
                print("   - Client analytics endpoint failing or showing $0 revenue")
            if not admin_analytics_passed:
                print("   - Admin analytics endpoint failing or showing $0 revenue")
            if not calculation_passed:
                print("   - Analytics calculation endpoint failing")
            print("\n💡 These issues likely explain the 'Failed to load analytics' error in frontend")
        else:
            print("\n✅ All critical analytics endpoints are working correctly")
            print("   If user still sees 'Failed to load analytics', check frontend integration")
        
        return client_analytics_passed and admin_analytics_passed and calculation_passed

if __name__ == "__main__":
    tester = AnalyticsFocusedTester()
    success = tester.run_all_analytics_tests()
    sys.exit(0 if success else 1)