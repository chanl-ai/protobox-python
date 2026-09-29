#!/usr/bin/env python3
"""
Wait for server to be ready.
Simple script that waits for the server to respond to health checks.
"""

import requests
import sys
import time
import argparse


def wait_for_server(url: str = "http://localhost:8090", timeout: int = 30) -> bool:
    """Wait for server to be ready."""
    health_url = f"{url}/admin/api/v1/health"
    
    print(f"⏳ Waiting for server at {url}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    print(f"✅ Server is ready at {url}")
                    return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(1)
    
    print(f"❌ Server not ready after {timeout}s")
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wait for server to be ready")
    parser.add_argument("--url", default="http://localhost:8090", help="Server URL")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    
    args = parser.parse_args()
    
    success = wait_for_server(args.url, args.timeout)
    sys.exit(0 if success else 1)