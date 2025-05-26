#!/usr/bin/env python3
"""Simple test runner for verification."""

import subprocess
import sys

def run_tests():
    """Run the specific tests we care about."""
    try:
        # Run only the haystack service tests
        result = subprocess.run(
            ["python", "-m", "pytest", "test/unit/tools/test_haystack_service.py", "-v"],
            capture_output=True,
            text=True,
            check=False
        )
        
        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print(f"\nReturn code: {result.returncode}")
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
