#!/usr/bin/env python3
"""
Generate Firebase emulator token and exchange for JWT.
Outputs the JWT token to stdout for use in testing.
"""

import json
import sys
import requests
from typing import Optional

def get_emulator_token(uid: str = "test_user", email: str = "test@example.com") -> Optional[str]:
    """
    Generate a Firebase emulator token.
    
    Note: This requires Firebase emulator to be running on port 9099.
    """
    try:
        # Check if emulator is running
        emulator_url = "http://localhost:9099"
        response = requests.get(f"{emulator_url}/emulator/v1/projects", timeout=1)
        if response.status_code != 200:
            print("Firebase emulator not running", file=sys.stderr)
            return None
            
        # In a real implementation, you'd use Firebase Admin SDK
        # For now, return a test token that the backend accepts
        return f"test-{uid}"
        
    except requests.RequestException:
        print("Firebase emulator not accessible", file=sys.stderr)
        return None

def exchange_for_jwt(firebase_token: str) -> Optional[str]:
    """Exchange Firebase token for JWT."""
    try:
        response = requests.post(
            "http://localhost:8090/admin/api/v1/auth/exchange",
            json={"firebase_token": firebase_token},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print(f"Token exchange failed: {response.status_code}", file=sys.stderr)
            return None
            
    except requests.RequestException as e:
        print(f"Failed to exchange token: {e}", file=sys.stderr)
        return None

def main():
    """Main function."""
    # Try to get Firebase emulator token
    firebase_token = get_emulator_token()
    
    if not firebase_token:
        # Fall back to test token if emulator not available
        firebase_token = "test-user123"
        print("Using test token (emulator not available)", file=sys.stderr)
    
    # Exchange for JWT
    jwt_token = exchange_for_jwt(firebase_token)
    
    if jwt_token:
        # Output just the token to stdout
        print(jwt_token)
        sys.exit(0)
    else:
        print("Failed to get JWT token", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()