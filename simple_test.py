#!/usr/bin/env python3
"""
Simple test script for C to Rust transpilation using LangChain integration.
This script demonstrates a basic usage example with minimal dependencies.
"""

import os
import sys
from pathlib import Path

# Sample C code for testing
SAMPLE_C_CODE = """
#include <stdio.h>

// Simple function to calculate factorial
int factorial(int n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

// Main function
int main() {
    int num = 5;
    printf("Factorial of %d is %d\\n", num, factorial(num));
    return 0;
}
"""

def main():
    """Run a simple test of the C to Rust transpilation."""
    # Create workspace directory if it doesn't exist
    workspace_dir = Path("./workspace")
    workspace_dir.mkdir(exist_ok=True)
    
    # Save the sample C code to a file
    c_file_path = workspace_dir / "sample_factorial.c"
    with open(c_file_path, "w") as f:
        f.write(SAMPLE_C_CODE)
    
    print(f"Created sample C file at: {c_file_path}")
    print("\nC code:")
    print(SAMPLE_C_CODE)
    
    print("\nTo transpile this code to Rust, you can use:")
    print("python test_c_to_rust.py --file workspace/sample_factorial.c --method direct")
    print("python test_c_to_rust.py --file workspace/sample_factorial.c --method feedback")
    print("python test_c_to_rust.py --file workspace/sample_factorial.c --method supervisor")
    print("python test_c_to_rust.py --file workspace/sample_factorial.c --method supervisor_feedback")

if __name__ == "__main__":
    main()
