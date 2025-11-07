#!/usr/bin/env python
"""
Test Suite Runner

This script runs the comprehensive API test suite with proper initialization.
All tests are executed in order to ensure proper test data flow.

Usage:
    python run_tests.py                    # Run all tests with default base URL
    python run_tests.py --base-url http://example.com:8000
    python run_tests.py --verbose
    python run_tests.py -k authentication  # Run only authentication tests
"""

import pytest
import sys
import os


def main():
    """Run the test suite."""
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Build pytest arguments
    args = [
        current_dir,  # Run all tests in this directory
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "-ra",  # Show all test summary
    ]

    # Add any command line arguments passed to this script
    args.extend(sys.argv[1:])

    print("=" * 70)
    print("COMPREHENSIVE API TEST SUITE")
    print("=" * 70)
    print()

    # Run pytest
    exit_code = pytest.main(args)

    print()
    print("=" * 70)
    if exit_code == 0:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 70)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
