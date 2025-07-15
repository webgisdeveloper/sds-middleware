#!/usr/bin/env python3
"""
Demo script showing how site-specific client secret authentication works.
This script demonstrates the different authentication scenarios.
"""

import requests
from app.core.config import settings

# Base URL for the API
BASE_URL = "http://localhost:8080"

def test_authentication_scenarios():
    """Test various authentication scenarios."""
    print("=== SDS Middleware Site-Specific Authentication Demo ===\n")
    
    print("Configuration:")
    print(f"Default client secret: {settings.webserver.client_secret}")
    print(f"Site secrets: {settings.webserver.site_secrets}")
    print()
    
    # Test 1: Localhost request (should work without auth)
    print("1. Testing localhost request (no auth required):")
    try:
        response = requests.get(f"{BASE_URL}/", headers={"X-Forwarded-For": "127.0.0.1"})
        print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code == 200 else '✗ FAIL'}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: External request without auth (should fail)
    print("\n2. Testing external request without auth (should fail):")
    try:
        response = requests.get(f"{BASE_URL}/", headers={"X-Forwarded-For": "192.168.1.100"})
        print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code == 401 else '✗ FAIL'}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: External request with default secret
    print("\n3. Testing external request with default client secret:")
    try:
        response = requests.get(
            f"{BASE_URL}/", 
            headers={
                "X-Forwarded-For": "192.168.1.100",
                "Authorization": f"Bearer {settings.webserver.client_secret}"
            }
        )
        print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code == 200 else '✗ FAIL'}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Site1 request with site-specific secret
    site1_secret = settings.webserver.site_secrets.get("site1")
    if site1_secret:
        print(f"\n4. Testing site1 request with site-specific secret ({site1_secret}):")
        try:
            response = requests.get(
                f"{BASE_URL}/", 
                headers={
                    "X-Forwarded-For": "192.168.1.100",
                    "X-Site": "site1",
                    "X-Client-Secret": site1_secret
                }
            )
            print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code == 200 else '✗ FAIL'}")
        except Exception as e:
            print(f"   Error: {e}")
    
    # Test 5: Site2 request with Authorization header
    site2_secret = settings.webserver.site_secrets.get("site2")
    if site2_secret:
        print(f"\n5. Testing site2 request with Bearer token ({site2_secret}):")
        try:
            response = requests.get(
                f"{BASE_URL}/", 
                headers={
                    "X-Forwarded-For": "192.168.1.100",
                    "X-Site": "site2",
                    "Authorization": f"Bearer {site2_secret}"
                }
            )
            print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code == 200 else '✗ FAIL'}")
        except Exception as e:
            print(f"   Error: {e}")
    
    # Test 6: Site3 request with query parameter
    site3_secret = settings.webserver.site_secrets.get("site3")
    if site3_secret:
        print(f"\n6. Testing site3 request with query parameter ({site3_secret}):")
        try:
            response = requests.get(
                f"{BASE_URL}/?site=site3&client_secret={site3_secret}", 
                headers={"X-Forwarded-For": "192.168.1.100"}
            )
            print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code == 200 else '✗ FAIL'}")
        except Exception as e:
            print(f"   Error: {e}")
    
    # Test 7: Site1 request with wrong secret (should fail)
    print("\n7. Testing site1 request with wrong secret (should fail):")
    try:
        response = requests.get(
            f"{BASE_URL}/", 
            headers={
                "X-Forwarded-For": "192.168.1.100",
                "X-Site": "site1",
                "X-Client-Secret": "wrong-secret"
            }
        )
        print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code == 401 else '✗ FAIL'}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 8: Unknown site with default secret
    print("\n8. Testing unknown site with default secret:")
    try:
        response = requests.get(
            f"{BASE_URL}/", 
            headers={
                "X-Forwarded-For": "192.168.1.100",
                "X-Site": "unknown_site",
                "X-Client-Secret": settings.webserver.client_secret
            }
        )
        print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code == 200 else '✗ FAIL'}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n=== Demo Complete ===")

if __name__ == "__main__":
    test_authentication_scenarios()
