#!/usr/bin/env python3
"""
Set up test users in Firebase emulator for automated testing.
This script creates standard test users that integration tests can use.
"""

import requests
import json
import time
import sys

EMULATOR_HOST = "localhost:9099"
EMULATOR_URL = f"http://{EMULATOR_HOST}"
PROJECT_ID = "demo-test"
API_KEY = "fake-api-key"  # Emulator accepts any API key


def wait_for_emulator(max_attempts=30):
    """Wait for Firebase emulator to be ready."""
    print(f"Waiting for Firebase emulator at {EMULATOR_URL}...")
    for i in range(max_attempts):
        try:
            response = requests.get(f"{EMULATOR_URL}/", timeout=1)
            if response.status_code == 200:
                print("✅ Firebase emulator is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
        print(f"  Attempt {i+1}/{max_attempts}...")
    print("❌ Firebase emulator is not responding")
    return False


def create_test_user(email, password, uid=None, display_name=None):
    """Create a user in Firebase emulator."""
    # Use the REST API endpoint for Firebase Auth emulator
    url = f"{EMULATOR_URL}/emulator/v1/projects/{PROJECT_ID}/accounts"
    
    # Alternative: Try using the standard endpoint format
    # The emulator should accept the same API as production
    url = f"{EMULATOR_URL}/identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
    
    data = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    
    # Firebase emulator may support setting custom UID differently
    if uid:
        # Try adding it to the request
        data["localId"] = uid
    if display_name:
        data["displayName"] = display_name
    
    try:
        # First try with emulator-specific headers
        headers = {
            "Authorization": f"Bearer owner",  # Emulator uses "owner" token
            "Content-Type": "application/json"
        }
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code != 200:
            # Try without special headers
            response = requests.post(url, json=data)
        
        response.raise_for_status()
        result = response.json()
        print(f"✅ Created user: {email} (uid: {result.get('localId')})")
        return result
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create user {email}: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Response: {e.response.text}")
        return None


def get_id_token(email, password):
    """Get Firebase ID token for testing."""
    url = f"{EMULATOR_URL}/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    try:
        response = requests.post(url, json={
            "email": email,
            "password": password,
            "returnSecureToken": True
        })
        response.raise_for_status()
        token = response.json().get("idToken")
        print(f"✅ Got token for {email}: {token[:20]}...")
        return token
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to get token for {email}: {e}")
        return None


def verify_user_can_login(email, password):
    """Verify that a user can log in and get a token."""
    token = get_id_token(email, password)
    return token is not None


def exchange_token_with_backend(firebase_token):
    """Exchange Firebase token with our backend for a JWT."""
    url = "http://localhost:8090/admin/api/v1/auth/exchange"
    try:
        response = requests.post(url, json={"firebase_token": firebase_token})
        response.raise_for_status()
        result = response.json()
        print(f"✅ Token exchange successful! JWT: {result['access_token'][:20]}...")
        return result
    except requests.exceptions.RequestException as e:
        print(f"❌ Token exchange failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Response: {e.response.text}")
        return None


def main():
    # Wait for emulator to be ready
    if not wait_for_emulator():
        print("Please start the Firebase emulator first:")
        print("  docker-compose -f docker-compose.test.yml up firebase-emulator")
        sys.exit(1)
    
    print("\n📝 Creating test users...")
    
    # Standard test users with predictable UIDs
    test_users = [
        {
            "email": "test@example.com",
            "password": "testpass123",
            "uid": "test-user-001",
            "display_name": "Test User"
        },
        {
            "email": "admin@example.com",
            "password": "adminpass123",
            "uid": "admin-user-001",
            "display_name": "Admin User"
        },
        {
            "email": "readonly@example.com",
            "password": "readpass123",
            "uid": "readonly-user-001",
            "display_name": "ReadOnly User"
        },
        {
            "email": "integration@test.com",
            "password": "integration123",
            "uid": "integration-test-001",
            "display_name": "Integration Test User"
        }
    ]
    
    created_users = []
    for user_data in test_users:
        result = create_test_user(**user_data)
        if result:
            created_users.append(user_data)
    
    print(f"\n✅ Created {len(created_users)} test users")
    
    # Test login for each user
    print("\n🔑 Testing login for each user...")
    for user_data in created_users:
        if verify_user_can_login(user_data["email"], user_data["password"]):
            print(f"  ✅ {user_data['email']} can log in")
        else:
            print(f"  ❌ {user_data['email']} cannot log in")
    
    # Test token exchange with backend (if running)
    print("\n🔄 Testing token exchange with backend...")
    test_user = created_users[0] if created_users else None
    if test_user:
        firebase_token = get_id_token(test_user["email"], test_user["password"])
        if firebase_token:
            jwt_result = exchange_token_with_backend(firebase_token)
            if jwt_result:
                print("\n🎉 Full authentication flow works!")
                print(f"   User: {test_user['email']}")
                print(f"   UID: {test_user['uid']}")
                print(f"   JWT Token: {jwt_result['access_token'][:30]}...")
                
                # Save token for manual testing
                with open(".emulator-test-token", "w") as f:
                    f.write(jwt_result['access_token'])
                print(f"\n💾 Token saved to .emulator-test-token for manual testing")
    
    print("\n✨ Firebase emulator setup complete!")
    print("   Emulator UI: http://localhost:4000")
    print("   Auth API: http://localhost:9099")


if __name__ == "__main__":
    main()