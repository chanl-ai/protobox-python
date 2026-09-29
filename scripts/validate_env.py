#!/usr/bin/env python3
"""
Server environment validation script
Ensures all required environment variables are set before deployment
"""

import os
import sys
from typing import List, Dict, Tuple
import json

# ANSI color codes
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
NC = '\033[0m'  # No Color

# Required environment variables for server
REQUIRED_VARS = {
    'core': [
        'ADMIN_SECRET_KEY',  # Changed from MCP_SECRET_KEY
        'ENVIRONMENT',       # Changed from MCP_ENVIRONMENT
        'ADMIN_ENABLED'      # Changed from MCP_ADMIN_ENABLED
    ],
    'database': [
        'MCP_MONGODB_URL'
    ],
    'auth': [
        # Removed deprecated AUTH_MODE - now always uses Firebase authentication
        'AUTH_TEST_MODE',  # Optional: Enable test mode for Firebase auth
        'AUTH_ALLOW_TEST_TOKENS'  # Optional: Allow test tokens for development
    ],
    'external_services': [
        'OPENAI_API_KEY'
    ],
    'optional': [
        'SENTRY_DSN',
        'LOG_LEVEL',
        'FIREBASE_PRIVATE_KEY',
        'FIREBASE_PROJECT_ID',
        'FIREBASE_CLIENT_EMAIL'
    ]
}

def check_environment() -> Tuple[bool, List[str], List[str]]:
    """Check if all required environment variables are set"""
    missing_vars = []
    warnings = []
    
    # Check required variables
    for category, vars_list in REQUIRED_VARS.items():
        if category == 'optional':
            continue
            
        for var in vars_list:
            if not os.getenv(var):
                missing_vars.append(f"{category}.{var}")
    
    # Check for common issues
    env = os.getenv('ENVIRONMENT', '')
    mongodb_url = os.getenv('MCP_MONGODB_URL', '')
    
    # Validation warnings
    if env == 'production' and 'localhost' in mongodb_url:
        warnings.append("MongoDB URL contains 'localhost' in production!")
    
    # Removed AUTH_MODE validation - now always uses Firebase authentication
    if env == 'production' and os.getenv('AUTH_TEST_MODE') == 'true':
        warnings.append("AUTH_TEST_MODE is enabled in production!")
    
    if not os.getenv('FIREBASE_PRIVATE_KEY') and env == 'production':
        warnings.append("FIREBASE_PRIVATE_KEY not set for production")
    
    return len(missing_vars) == 0, missing_vars, warnings

def test_connections():
    """Test database and external service connections"""
    results = []
    
    # Test MongoDB connection
    mongodb_url = os.getenv('MCP_MONGODB_URL')
    if mongodb_url:
        try:
            from pymongo import MongoClient
            client = MongoClient(mongodb_url, serverSelectionTimeoutMS=5000)
            client.server_info()
            results.append(('MongoDB', True, 'Connected'))
            client.close()
        except Exception as e:
            results.append(('MongoDB', False, str(e)))
    
    # Test OpenAI API
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        try:
            import httpx
            response = httpx.get(
                'https://api.openai.com/v1/models',
                headers={'Authorization': f'Bearer {openai_key}'},
                timeout=5.0
            )
            if response.status_code == 200:
                results.append(('OpenAI API', True, 'Connected'))
            else:
                results.append(('OpenAI API', False, f'HTTP {response.status_code}'))
        except Exception as e:
            results.append(('OpenAI API', False, str(e)))
    
    return results

def main():
    """Main validation function"""
    print(f"{YELLOW}🔍 Validating server environment variables...{NC}\n")
    
    # Get environment
    env = os.getenv('ENVIRONMENT', 'unknown')
    print(f"Environment: {env}\n")
    
    # Check environment variables
    is_valid, missing, warnings = check_environment()
    
    # Print results
    print(f"{YELLOW}Required Variables:{NC}")
    for category, vars_list in REQUIRED_VARS.items():
        if category == 'optional':
            continue
            
        print(f"\n{category}:")
        for var in vars_list:
            value = os.getenv(var)
            if value:
                # Don't print sensitive values
                if 'SECRET' in var or 'KEY' in var or 'PASSWORD' in var:
                    print(f"  ✅ {var}: [SET]")
                else:
                    print(f"  ✅ {var}: {value[:50]}...")
            else:
                print(f"  ❌ {var}: [MISSING]")
    
    # Print warnings
    if warnings:
        print(f"\n{YELLOW}⚠️  Warnings:{NC}")
        for warning in warnings:
            print(f"  - {warning}")
    
    # Test connections if requested
    if '--check-connections' in sys.argv:
        print(f"\n{YELLOW}🔌 Testing connections...{NC}\n")
        connection_results = test_connections()
        
        for service, success, message in connection_results:
            if success:
                print(f"  ✅ {service}: {message}")
            else:
                print(f"  ❌ {service}: {message}")
    
    # Summary
    print(f"\n{YELLOW}Summary:{NC}")
    if is_valid:
        print(f"{GREEN}✅ All required environment variables are set!{NC}")
        return 0
    else:
        print(f"{RED}❌ Missing environment variables:{NC}")
        for var in missing:
            print(f"  - {var}")
        return 1

if __name__ == '__main__':
    sys.exit(main())