"""
Debug test script for the API endpoints.
Tests each endpoint individually with detailed error reporting.
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:3000"

def print_separator(title):
    print("\n" + "=" * 50)
    print(f" {title} ".center(50, "="))
    print("=" * 50)

def test_endpoint(url_path, method="get", data=None):
    """Test a single endpoint with detailed error reporting"""
    full_url = f"{BASE_URL}{url_path}"
    print(f"Testing {method.upper()} {full_url}")
    print(f"Request data: {data}")
    
    try:
        if method.lower() == "get":
            response = requests.get(full_url)
        else:  # POST
            response = requests.post(full_url, json=data)
        
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        content_type = response.headers.get('content-type', '')
        if 'application/json' in content_type:
            try:
                # Try to parse as JSON
                json_response = response.json()
                print(f"JSON response: {json.dumps(json_response, indent=2)}")
            except json.JSONDecodeError:
                # Not valid JSON, print as text
                print(f"Text response: {response.text[:200]}")
        else:
            # Not JSON, print as text
            print(f"Text response: {response.text[:200]}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"Exception: {str(e)}")
        return False

def main():
    print_separator("DEBUG TESTING")
    
    # List of endpoints to test
    endpoints = [
        # Basic server check
        {"path": "/", "method": "get"},
        {"path": "/debug/routes", "method": "get"},
        
        # API endpoints
        {"path": "/api/parseAppId", "method": "post"},
        {"path": "/api/registerPage", "method": "post"},
        {"path": "/api/posthog", "method": "post"},
        {"path": "/api/updateSchemas", "method": "post"},
        
        # Auth endpoints
        {"path": "/api/auth/register", "method": "post", "data": {
            "email": f"test_user_{int(time.time())}@example.com",
            "username": "testuser",
            "password": "password123"
        }},
        {"path": "/api/auth/login", "method": "post", "data": {
            "email": "test@example.com",
            "password": "password123"
        }},
        
        # Parse endpoints
        {"path": "/parse/login", "method": "post", "data": {
            "username": "test@example.com",
            "password": "password123"
        }}
    ]
    
    # Test each endpoint
    success_count = 0
    for endpoint in endpoints:
        print_separator(f"Testing {endpoint['path']}")
        success = test_endpoint(
            endpoint["path"], 
            endpoint.get("method", "get"),
            endpoint.get("data")
        )
        if success:
            success_count += 1
            print("✅ SUCCESS")
        else:
            print("❌ FAILED")
        
        print(f"\nProgress: {success_count}/{len(endpoints)} endpoints working")
    
    print_separator("SUMMARY")
    print(f"{success_count}/{len(endpoints)} endpoints working")
    if success_count < len(endpoints):
        print("Some endpoints are not working correctly!")
    else:
        print("All endpoints are working correctly!")

if __name__ == "__main__":
    main() 