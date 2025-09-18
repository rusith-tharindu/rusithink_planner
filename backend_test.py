import requests
import sys
from datetime import datetime, timedelta
import json

class ProjectPlannerAPITester:
    def __init__(self, base_url="https://taskmaster-pro-11.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_task_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, params=params)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_api_root(self):
        """Test API root endpoint"""
        return self.run_test("API Root", "GET", "", 200)

    def test_create_task(self):
        """Test task creation"""
        # Create a task due tomorrow at 2 PM
        due_date = datetime.now() + timedelta(days=1)
        due_date = due_date.replace(hour=14, minute=0, second=0, microsecond=0)
        
        task_data = {
            "title": "Website Redesign Project",
            "description": "Complete redesign of company website with modern UI/UX",
            "due_datetime": due_date.isoformat(),
            "project_price": 5000.0,
            "priority": "high"
        }
        
        success, response = self.run_test("Create Task", "POST", "tasks", 201, data=task_data)
        if success and 'id' in response:
            self.created_task_id = response['id']
            print(f"   Created task ID: {self.created_task_id}")
        return success

    def test_get_tasks(self):
        """Test getting all tasks"""
        return self.run_test("Get All Tasks", "GET", "tasks", 200)

    def test_get_single_task(self):
        """Test getting a single task"""
        if not self.created_task_id:
            print("❌ No task ID available for single task test")
            return False
        
        return self.run_test("Get Single Task", "GET", f"tasks/{self.created_task_id}", 200)

    def test_update_task_status(self):
        """Test updating task status"""
        if not self.created_task_id:
            print("❌ No task ID available for status update test")
            return False
        
        return self.run_test(
            "Update Task Status", 
            "PUT", 
            f"tasks/{self.created_task_id}/status", 
            200,
            params={"status": "completed"}
        )

    def test_update_task(self):
        """Test updating task details"""
        if not self.created_task_id:
            print("❌ No task ID available for task update test")
            return False
        
        update_data = {
            "title": "Updated Website Redesign Project",
            "project_price": 6000.0
        }
        
        return self.run_test(
            "Update Task", 
            "PUT", 
            f"tasks/{self.created_task_id}", 
            200,
            data=update_data
        )

    def test_get_stats(self):
        """Test getting task statistics"""
        return self.run_test("Get Task Stats", "GET", "tasks/stats/overview", 200)

    def test_delete_task(self):
        """Test deleting a task"""
        if not self.created_task_id:
            print("❌ No task ID available for delete test")
            return False
        
        return self.run_test("Delete Task", "DELETE", f"tasks/{self.created_task_id}", 200)

    def test_get_nonexistent_task(self):
        """Test getting a non-existent task (should return 404)"""
        fake_id = "non-existent-task-id"
        return self.run_test("Get Non-existent Task", "GET", f"tasks/{fake_id}", 404)

def main():
    print("🚀 Starting Project Planner API Tests")
    print("=" * 50)
    
    tester = ProjectPlannerAPITester()
    
    # Test sequence
    test_results = []
    
    # Basic connectivity
    test_results.append(tester.test_api_root())
    
    # CRUD operations
    test_results.append(tester.test_create_task())
    test_results.append(tester.test_get_tasks())
    test_results.append(tester.test_get_single_task())
    test_results.append(tester.test_update_task_status())
    test_results.append(tester.test_update_task())
    
    # Stats
    test_results.append(tester.test_get_stats())
    
    # Error handling
    test_results.append(tester.test_get_nonexistent_task())
    
    # Cleanup
    test_results.append(tester.test_delete_task())

    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 FINAL RESULTS")
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed! Backend API is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the backend implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())