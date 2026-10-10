#!/usr/bin/env python3
"""
Automation script to test all API endpoints.
Run this while the application is running locally.
"""

import json
import sys
import time
import requests
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
HEALTH_CHECK_URL = "http://localhost:8000/health"


class TestStatus(Enum):
    """Test result status."""
    PASSED = "✅ PASS"
    FAILED = "❌ FAIL"
    SKIPPED = "⊘ SKIP"
    ERROR = "⚠️ ERROR"


@dataclass
class TestResult:
    """Result of a single test."""
    endpoint: str
    method: str
    status_code: Optional[int]
    expected_status: int
    status: TestStatus
    message: str
    response_time: float
    response_data: Optional[Dict] = None


class EndpointTester:
    """Test all API endpoints."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results: List[TestResult] = []
        self.session = requests.Session()
        self.access_token: Optional[str] = None
        self.test_user = {
            "email": f"test_{int(time.time())}@example.com",
            "password": "TempPassword123!@#",
            "first_name": "Test",
            "last_name": "User",
            "tenant_name": f"Test Tenant {int(time.time())}",
            "tenant_slug": f"test-tenant-{int(time.time())}",
        }
        self.test_app_id: Optional[str] = None
        self.test_tenant_id: Optional[str] = None
        self.test_role_id: Optional[str] = None

    def _set_auth_header(self, token: Optional[str] = None):
        """Set authorization header."""
        if token or self.access_token:
            self.session.headers.update({
                "Authorization": f"Bearer {token or self.access_token}"
            })
        else:
            self.session.headers.pop("Authorization", None)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        expected_status: int = 200,
        require_auth: bool = True,
    ) -> TestResult:
        """Make an HTTP request and return test result."""
        url = f"{self.base_url}{endpoint}"
        
        if require_auth and not self.access_token:
            return TestResult(
                endpoint=endpoint,
                method=method,
                status_code=None,
                expected_status=expected_status,
                status=TestStatus.SKIPPED,
                message="No authentication token available",
                response_time=0,
            )

        try:
            start_time = time.time()
            
            if method == "GET":
                response = self.session.get(url, timeout=5)
            elif method == "POST":
                response = self.session.post(url, json=data, timeout=5)
            elif method == "PUT":
                response = self.session.put(url, json=data, timeout=5)
            elif method == "DELETE":
                response = self.session.delete(url, timeout=5)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response_time = time.time() - start_time
            response_data = None
            
            try:
                response_data = response.json()
            except:
                pass

            status = TestStatus.PASSED if response.status_code == expected_status else TestStatus.FAILED
            message = f"Status {response.status_code}"
            
            if response.status_code != expected_status:
                message += f" (expected {expected_status})"
                if response_data and isinstance(response_data, dict) and "detail" in response_data:
                    message += f": {response_data['detail']}"

            return TestResult(
                endpoint=endpoint,
                method=method,
                status_code=response.status_code,
                expected_status=expected_status,
                status=status,
                message=message,
                response_time=response_time,
                response_data=response_data,
            )

        except requests.exceptions.Timeout:
            return TestResult(
                endpoint=endpoint,
                method=method,
                status_code=None,
                expected_status=expected_status,
                status=TestStatus.ERROR,
                message="Request timeout",
                response_time=0,
            )
        except requests.exceptions.ConnectionError:
            return TestResult(
                endpoint=endpoint,
                method=method,
                status_code=None,
                expected_status=expected_status,
                status=TestStatus.ERROR,
                message="Connection error",
                response_time=0,
            )
        except Exception as e:
            return TestResult(
                endpoint=endpoint,
                method=method,
                status_code=None,
                expected_status=expected_status,
                status=TestStatus.ERROR,
                message=str(e),
                response_time=0,
            )

    def wait_for_server(self, timeout: int = 30) -> bool:
        """Wait for server to be ready."""
        print("⏳ Waiting for server to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(HEALTH_CHECK_URL, timeout=2)
                if response.status_code == 200:
                    print("✅ Server is ready!")
                    return True
            except:
                pass
            
            time.sleep(1)
        
        print("❌ Server did not respond within timeout")
        return False

    def test_health_check(self):
        """Test health check endpoints."""
        print("\n📋 Testing Health Check Endpoints...")
        
        # Health check (no auth needed)
        result = self._make_request(
            "GET",
            "/",
            expected_status=200,
            require_auth=False,
        )
        result.endpoint = "GET /"
        self.results.append(result)

    def test_authentication(self):
        """Test authentication endpoints."""
        print("\n🔐 Testing Authentication Endpoints...")
        
        # Register
        result = self._make_request(
            "POST",
            "/auth/register",
            data=self.test_user,
            expected_status=200,
            require_auth=False,
        )
        self.results.append(result)
        
        if result.status == TestStatus.PASSED and result.response_data:
            if isinstance(result.response_data, dict) and "data" in result.response_data:
                data = result.response_data["data"]
                if "tokens" in data:
                    self.access_token = data["tokens"].get("access_token")
                    if "tenant" in data:
                        self.test_tenant_id = data["tenant"].get("id")
                    print(f"  ✓ Got access token and tenant_id")
        
        # Login
        result = self._make_request(
            "POST",
            "/auth/login",
            data={
                "email": self.test_user["email"],
                "password": self.test_user["password"],
            },
            expected_status=200,
            require_auth=False,
        )
        self.results.append(result)
        
        if result.status == TestStatus.PASSED and result.response_data:
            if isinstance(result.response_data, dict) and "data" in result.response_data:
                data = result.response_data["data"]
                if "tokens" in data:
                    new_token = data["tokens"].get("access_token")
                    if new_token:
                        self.access_token = new_token
        
        # Get current user
        self._set_auth_header()
        result = self._make_request(
            "GET",
            "/auth/me",
            expected_status=200,
            require_auth=True,
        )
        self.results.append(result)

    def test_rbac(self):
        """Test RBAC endpoints."""
        print("\n👥 Testing RBAC Endpoints...")
        
        # List roles
        result = self._make_request(
            "GET",
            "/roles",
            expected_status=200,
            require_auth=True,
        )
        self.results.append(result)
        
        # Create role
        role_data = {
            "name": f"Test Role {int(time.time())}",
            "description": "A test role for automation",
        }
        result = self._make_request(
            "POST",
            "/roles",
            data=role_data,
            expected_status=201,
            require_auth=True,
        )
        self.results.append(result)
        
        if result.status == TestStatus.PASSED and result.response_data:
            if isinstance(result.response_data, dict):
                role_id = result.response_data.get("id") or \
                         (result.response_data.get("data", {}).get("id") if isinstance(result.response_data.get("data"), dict) else None)
                if role_id:
                    self.test_role_id = role_id
                    print(f"  ✓ Created test role: {role_id}")
        
        # List permissions
        result = self._make_request(
            "GET",
            "/permissions",
            expected_status=200,
            require_auth=True,
        )
        self.results.append(result)

    def test_applications(self):
        """Test application endpoints."""
        print("\n📱 Testing Application Endpoints...")
        
        # List applications
        result = self._make_request(
            "GET",
            "/applications",
            expected_status=200,
            require_auth=True,
        )
        self.results.append(result)
        
        # Create application
        app_data = {
            "name": f"Test App {int(time.time())}",
            "description": "Test application for automation",
            "webhook_url": "https://example.com/webhook",
            "is_active": True,
        }
        result = self._make_request(
            "POST",
            "/applications",
            data=app_data,
            expected_status=201,
            require_auth=True,
        )
        self.results.append(result)
        
        if result.status == TestStatus.PASSED and result.response_data:
            if isinstance(result.response_data, dict):
                app_id = result.response_data.get("id") or \
                        (result.response_data.get("data", {}).get("id") if isinstance(result.response_data.get("data"), dict) else None)
                if app_id:
                    self.test_app_id = app_id
                    print(f"  ✓ Created test application: {app_id}")

    def test_application_operations(self):
        """Test application-specific operations."""
        if not self.test_app_id:
            print("\n⊘ Skipping Application Operations (no test app)")
            return
        
        print("\n⚙️  Testing Application Operations...")
        
        # Get application
        result = self._make_request(
            "GET",
            f"/applications/{self.test_app_id}",
            expected_status=200,
            require_auth=True,
        )
        self.results.append(result)
        
        # Update application
        update_data = {"description": "Updated description"}
        result = self._make_request(
            "PUT",
            f"/applications/{self.test_app_id}",
            data=update_data,
            expected_status=200,
            require_auth=True,
        )
        self.results.append(result)
        
        # List API keys
        result = self._make_request(
            "GET",
            f"/applications/{self.test_app_id}/api-keys",
            expected_status=200,
            require_auth=True,
        )
        self.results.append(result)
        
        # Create API key
        key_data = {"name": f"Test Key {int(time.time())}"}
        result = self._make_request(
            "POST",
            f"/applications/{self.test_app_id}/api-keys",
            data=key_data,
            expected_status=201,
            require_auth=True,
        )
        self.results.append(result)

    def test_billing(self):
        """Test billing endpoints."""
        print("\n💳 Testing Billing Endpoints...")
        
        # List plans
        result = self._make_request(
            "GET",
            "/plans",
            expected_status=200,
            require_auth=True,
        )
        self.results.append(result)
        
        # List subscriptions
        result = self._make_request(
            "GET",
            "/subscriptions",
            expected_status=200,
            require_auth=True,
        )
        self.results.append(result)
        
        # Get usage
        result = self._make_request(
            "GET",
            "/usage",
            expected_status=200,
            require_auth=True,
        )
        self.results.append(result)
        
        # List invoices
        result = self._make_request(
            "GET",
            "/invoices",
            expected_status=200,
            require_auth=True,
        )
        self.results.append(result)
        
        # Get payment methods
        result = self._make_request(
            "GET",
            "/payment-methods",
            expected_status=200,
            require_auth=True,
        )
        self.results.append(result)
        
        # Get billing overview
        result = self._make_request(
            "GET",
            "/billing/overview",
            expected_status=200,
            require_auth=True,
        )
        self.results.append(result)

    def test_advanced(self):
        """Test advanced endpoints."""
        print("\n🔧 Testing Advanced Endpoints...")
        
        # List webhooks
        result = self._make_request(
            "GET",
            "/webhooks",
            expected_status=200,
            require_auth=True,
        )
        self.results.append(result)
        
        # List audit logs
        result = self._make_request(
            "GET",
            "/audit-logs",
            expected_status=200,
            require_auth=True,
        )
        self.results.append(result)
        
        # List data exports
        result = self._make_request(
            "GET",
            "/data-exports",
            expected_status=200,
            require_auth=True,
        )
        self.results.append(result)

    def print_results(self):
        """Print test results summary."""
        print("\n" + "=" * 80)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 80)
        
        # Group by status
        passed = [r for r in self.results if r.status == TestStatus.PASSED]
        failed = [r for r in self.results if r.status == TestStatus.FAILED]
        skipped = [r for r in self.results if r.status == TestStatus.SKIPPED]
        errors = [r for r in self.results if r.status == TestStatus.ERROR]
        
        # Print detailed results
        for result in self.results:
            status_icon = result.status.value
            print(
                f"{status_icon} {result.method:6} {result.endpoint:50} "
                f"({result.response_time:.2f}s) {result.message}"
            )
        
        # Print summary
        print("\n" + "-" * 80)
        print(f"Total: {len(self.results)} | "
              f"✅ Passed: {len(passed)} | "
              f"❌ Failed: {len(failed)} | "
              f"⊘ Skipped: {len(skipped)} | "
              f"⚠️ Errors: {len(errors)}")
        
        # Calculate success rate
        if len(self.results) > 0:
            success_rate = (len(passed) / len(self.results)) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        print("=" * 80)
        
        # Return exit code
        return 0 if len(failed) == 0 and len(errors) == 0 else 1

    def run_all_tests(self) -> int:
        """Run all tests."""
        print("\n" + "=" * 80)
        print("🚀 NEXORA BACKEND - ENDPOINT AUTOMATION TEST SUITE")
        print("=" * 80)
        print(f"Base URL: {self.base_url}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Wait for server
        if not self.wait_for_server():
            print("❌ Cannot connect to server at {HEALTH_CHECK_URL}")
            return 1
        
        # Run test suites
        self.test_health_check()
        self.test_authentication()
        
        if self.access_token:
            self.test_rbac()
            self.test_applications()
            self.test_application_operations()
            self.test_billing()
            self.test_advanced()
        else:
            print("\n❌ Authentication failed, skipping authenticated tests")
        
        # Print results
        return self.print_results()


def main():
    """Main entry point."""
    tester = EndpointTester(API_BASE_URL)
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
