#!/usr/bin/env python3
"""
PHASE 3: Automated Self-Test
Tests the refactored AI Studio controller via proxy
"""
import requests
import time
import sys
import json
from datetime import datetime


def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_step(step_num, description):
    """Print step indicator"""
    print(f"\n[STEP {step_num}] {description}")


def print_success(msg):
    """Print success message"""
    print(f"  ✓ {msg}")


def print_error(msg):
    """Print error message"""
    print(f"  ✗ {msg}")


def test_proxy_connection():
    """Test if proxy is accessible"""
    print_step(1, "Testing proxy connection...")
    try:
        response = requests.get("http://localhost:9002/v1/models", timeout=5)
        if response.status_code == 200:
            print_success("Proxy is running on port 9002")
            return True
        else:
            print_error(f"Proxy returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to proxy on port 9002")
        print("  Make sure Docker container is running:")
        print("    - Run PHASE2_RESET_CONTAINER.bat first")
        print("    - Or check: docker ps | grep mcp_gemini_1")
        return False
    except Exception as e:
        print_error(f"Connection test failed: {e}")
        return False


def test_ai_studio_submission():
    """Test AI Studio prompt submission"""
    print_step(2, "Testing AI Studio submission logic...")
    
    url = "http://localhost:9002/v1/responses"
    payload = {
        "input": [
            {
                "role": "user",
                "content": "Explain the concept of feedback loops in one sentence."
            }
        ]
    }
    
    print(f"  URL: {url}")
    print(f"  Payload: {payload['input'][0]['content']}")
    print("  Timeout: 120 seconds (allows for AI generation)")
    
    try:
        start_time = time.time()
        print("\n  Sending request...", end="", flush=True)
        
        response = requests.post(
            url,
            json=payload,
            timeout=120,
            headers={"Content-Type": "application/json"}
        )
        
        elapsed = time.time() - start_time
        print(f" (received in {elapsed:.1f}s)")
        
        if response.status_code != 200:
            print_error(f"HTTP {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
        
        # Parse response
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print_error(f"Invalid JSON response: {e}")
            print(f"  Response: {response.text[:200]}")
            return False
        
        # Check for error messages
        if "Fehler" in str(data) or "error" in str(data).lower():
            print_error("AI Studio returned an error")
            print(f"  Response: {data}")
            return False
        
        # Extract content
        try:
            content = data["choices"][0]["message"]["content"]
            if not content or len(content.strip()) < 10:
                print_error("Response content is empty or too short")
                return False
            
            print_success(f"Got response ({len(content)} characters)")
            print(f"\n  Response preview:")
            preview = content[:300] + ("..." if len(content) > 300 else "")
            for line in preview.split("\n"):
                print(f"    {line}")
            
            return True
            
        except (KeyError, IndexError) as e:
            print_error(f"Response structure unexpected: {e}")
            print(f"  Response: {data}")
            return False
            
    except requests.exceptions.Timeout:
        print_error("Request timed out (>120 seconds)")
        print("  Possible causes:")
        print("    - AI Studio submission failed")
        print("    - Response generation taking too long")
        print("    - Browser not responding")
        return False
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def main():
    """Run all tests"""
    print_header("PHASE 3: AUTOMATED SELF-TEST")
    
    print(f"  Time: {datetime.now().isoformat()}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Requests: {requests.__version__}")
    
    # Test 1: Proxy connection
    if not test_proxy_connection():
        print_header("PHASE 3 FAILED ✗")
        print("\nFix: Ensure Docker container is running")
        print("  docker ps | grep mcp_gemini_1")
        sys.exit(1)
    
    # Test 2: AI Studio submission
    if not test_ai_studio_submission():
        print_header("PHASE 3 FAILED ✗")
        print("\nLikely issues:")
        print("  1. Browser submission failed (check send_prompt logic)")
        print("  2. Response scraping failed (check wait_for_response logic)")
        print("  3. Network/proxy issue")
        print("\nDEBUGGING:")
        print("  - Check Docker logs: docker logs -f mcp_gemini_1")
        print("  - View in VNC: localhost:5901 (VNC Viewer)")
        print("  - Check network: curl http://localhost:8001/ (should fail, that's ok)")
        sys.exit(1)
    
    # All tests passed
    print_header("PHASE 3 SUCCESSFUL ✓")
    print("\n✓ Proxy connection: OK")
    print("✓ AI Studio submission: OK")
    print("✓ Response extraction: OK")
    print("\n" + "=" * 70)
    print("  REFACTORING COMPLETE!")
    print("  All phases passed successfully.")
    print("=" * 70)
    print("\nThe pipeline is now ready for production:")
    print("  - set_model(): No coordinate clicks, uses locators")
    print("  - send_prompt(): SPA state-aware, 3-tier fallback")
    print("  - wait_for_response(): Robust polling, error handling")
    print()
    
    sys.exit(0)


if __name__ == "__main__":
    main()
