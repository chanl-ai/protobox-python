#!/usr/bin/env python3
"""
Minimal client example for ProtoBox API with sessionless authentication.

Demonstrates:
1. Firebase token exchange for JWT
2. Using access tokens for API calls
3. Refreshing tokens
4. API key authentication
"""

import os
import sys
import json
import time
import requests
from typing import Optional, Dict, Any


class ProtoBoxClient:
    """Minimal ProtoBox API client with dual authentication support."""
    
    def __init__(self, base_url: str = "http://localhost:8090"):
        self.base_url = base_url
        self.api_base = f"{base_url}/admin/api/v1"
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.api_key: Optional[str] = None
    
    def exchange_firebase_token(self, firebase_token: str) -> Dict[str, Any]:
        """
        Exchange a Firebase ID token for JWT tokens.
        
        Args:
            firebase_token: Firebase ID token from client authentication
            
        Returns:
            Token response with access_token and refresh_token
        """
        response = requests.post(
            f"{self.api_base}/auth/exchange",
            json={"firebase_token": firebase_token}
        )
        
        if response.status_code != 200:
            raise Exception(f"Token exchange failed: {response.text}")
        
        data = response.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        
        print(f"✅ Token exchange successful")
        print(f"   User: {data['user']['email']}")
        print(f"   Access token expires in: {data['expires_in']} seconds")
        
        return data
    
    def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh the access token using the refresh token.
        
        Returns:
            New token response
        """
        if not self.refresh_token:
            raise Exception("No refresh token available")
        
        response = requests.post(
            f"{self.api_base}/auth/refresh",
            json={"refresh_token": self.refresh_token}
        )
        
        if response.status_code != 200:
            raise Exception(f"Token refresh failed: {response.text}")
        
        data = response.json()
        self.access_token = data["access_token"]
        
        print(f"✅ Token refreshed successfully")
        print(f"   New access token expires in: {data['expires_in']} seconds")
        
        return data
    
    def validate_token(self) -> Dict[str, Any]:
        """
        Validate the current access token.
        
        Returns:
            Validation response
        """
        headers = self._get_auth_headers()
        response = requests.get(
            f"{self.api_base}/auth/validate",
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Token validation failed: {response.text}")
        
        data = response.json()
        print(f"✅ Token validation: {'Valid' if data['valid'] else 'Invalid'}")
        if data['valid']:
            print(f"   User ID: {data['uid']}")
            print(f"   Email: {data['email']}")
        
        return data
    
    def set_api_key(self, api_key: str):
        """Set API key for authentication."""
        self.api_key = api_key
        print(f"✅ API key configured")
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers based on available credentials."""
        headers = {"Content-Type": "application/json"}
        
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        elif self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        return headers
    
    def make_api_call(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Any:
        """
        Make an authenticated API call.
        
        Args:
            endpoint: API endpoint (relative to base)
            method: HTTP method
            data: Request data for POST/PUT
            
        Returns:
            Response data
        """
        url = f"{self.api_base}{endpoint}"
        headers = self._get_auth_headers()
        
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if response.status_code == 401:
            print("⚠️  Access token expired, attempting refresh...")
            self.refresh_access_token()
            # Retry with new token
            headers = self._get_auth_headers()
            response = requests.request(method, url, headers=headers, json=data)
        
        if response.status_code >= 400:
            raise Exception(f"API call failed: {response.status_code} - {response.text}")
        
        return response.json() if response.text else None


def demo_jwt_auth():
    """Demonstrate JWT-based authentication flow."""
    print("\n" + "="*50)
    print("JWT Authentication Demo")
    print("="*50)
    
    client = ProtoBoxClient()
    
    # In a real app, you'd get this from Firebase after user login
    # For testing, we'll use a test token
    print("\n1. Simulating Firebase authentication...")
    firebase_token = "test-firebase-token-12345"
    
    print("\n2. Exchanging Firebase token for JWT...")
    try:
        client.exchange_firebase_token(firebase_token)
    except Exception as e:
        print(f"   Note: {e}")
        print("   (Firebase validation not configured in dev - using test mode)")
    
    print("\n3. Validating access token...")
    client.validate_token()
    
    print("\n4. Making authenticated API call...")
    try:
        health = client.make_api_call("/health")
        print(f"✅ Health check successful: {health['status']}")
    except Exception as e:
        print(f"❌ API call failed: {e}")
    
    print("\n5. Simulating token expiry and refresh...")
    # In real scenario, token would expire after 1 hour
    client.refresh_access_token()
    
    print("\n6. Making another API call with refreshed token...")
    try:
        health = client.make_api_call("/health")
        print(f"✅ Health check successful: {health['status']}")
    except Exception as e:
        print(f"❌ API call failed: {e}")


def demo_api_key_auth():
    """Demonstrate API key authentication."""
    print("\n" + "="*50)
    print("API Key Authentication Demo")
    print("="*50)
    
    client = ProtoBoxClient()
    
    print("\n1. Setting API key...")
    # In production, this would be a real API key from the dashboard
    api_key = os.getenv("PROTOBOX_API_KEY", "pb_test_key_123:secret_456")
    client.set_api_key(api_key)
    
    print("\n2. Making authenticated API call with API key...")
    try:
        health = client.make_api_call("/health")
        print(f"✅ Health check successful: {health['status']}")
    except Exception as e:
        print(f"❌ API call failed: {e}")
        print("   (API key validation not fully implemented yet)")


def main():
    """Run authentication demos."""
    print("""
ProtoBox Minimal Client Example
================================

This demonstrates the sessionless authentication system:
- JWT tokens for user sessions (web, mobile)
- API keys for programmatic access (CLI, CI/CD)
- Automatic token refresh
- Dual authentication support
""")
    
    # Demo JWT authentication flow
    demo_jwt_auth()
    
    # Demo API key authentication
    demo_api_key_auth()
    
    print("\n" + "="*50)
    print("Demo Complete!")
    print("="*50)
    print("""
Next Steps:
1. Implement real Firebase authentication in frontend
2. Generate API keys from user dashboard
3. Use refresh tokens for long-lived sessions
4. Implement token blacklist for critical security
""")


if __name__ == "__main__":
    main()