#!/usr/bin/env python
"""
Test runner for the Mechanical Options Trade Recommender application.

This script runs all tests and generates a coverage report to verify
that the codebase meets quality standards.
"""

import unittest
import coverage
import os
import sys

def run_tests_with_coverage():
    """Run all tests and generate a coverage report."""
    # Configure coverage
    cov = coverage.Coverage(
        source=["src"],
        omit=[
            "*/\__init\__.py",
            "*/\__pycache\__/*",
            "*/tests/*"
        ],
        branch=True
    )
    
    # Start coverage measurement
    cov.start()
    
    # Discover and run all tests
    loader = unittest.TestLoader()
    tests_dir = os.path.join(os.path.dirname(__file__), "tests")
    suite = loader.discover(tests_dir)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Stop coverage measurement
    cov.stop()
    
    # Generate reports
    print("\nCoverage Summary:")
    cov.report()
    
    # Generate HTML report
    print("\nGenerating HTML coverage report in 'htmlcov' directory...")
    cov.html_report(directory="htmlcov")
    
    return result

if __name__ == "__main__":
    print("=" * 80)
    print("Running tests with coverage for Mechanical Options Trade Recommender")
    print("=" * 80)
    
    # Add the project root to Python path
    sys.path.insert(0, os.path.dirname(__file__))
    
    # Run tests
    result = run_tests_with_coverage()
    
    # Exit with appropriate status code
    sys.exit(not result.wasSuccessful())
