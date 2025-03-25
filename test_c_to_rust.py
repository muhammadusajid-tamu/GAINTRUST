#!/usr/bin/env python3
"""
Test script for C to Rust transpilation using LangChain integration.

This script demonstrates the use of the C to Rust transpilation capabilities
implemented in the LangChain integration and supervisor architecture.
"""

import os
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import GAINTRUST components
from langchain_local_integration import CToRustTranspilerChain, CToRustTranspilerWithFeedback
from supervisor import CToRustSupervisor, SupervisorWithFeedback

# Example C code snippets
EXAMPLES = {
    "linked_list": """
    #include <stdio.h>
    #include <stdlib.h>
    
    // A simple linked list node
    struct Node {
        int data;
        struct Node* next;
    };
    
    // Function to create a new node
    struct Node* createNode(int data) {
        struct Node* newNode = (struct Node*)malloc(sizeof(struct Node));
        if (newNode == NULL) {
            printf("Memory allocation failed\\n");
            exit(1);
        }
        newNode->data = data;
        newNode->next = NULL;
        return newNode;
    }
    
    // Function to insert a node at the beginning of the list
    struct Node* insertAtBeginning(struct Node* head, int data) {
        struct Node* newNode = createNode(data);
        newNode->next = head;
        return newNode;
    }
    
    // Function to print the linked list
    void printList(struct Node* head) {
        struct Node* current = head;
        while (current != NULL) {
            printf("%d -> ", current->data);
            current = current->next;
        }
        printf("NULL\\n");
    }
    
    // Function to free the memory used by the linked list
    void freeList(struct Node* head) {
        struct Node* current = head;
        struct Node* next;
        
        while (current != NULL) {
            next = current->next;
            free(current);
            current = next;
        }
    }
    """,
    
    "binary_tree": """
    #include <stdio.h>
    #include <stdlib.h>
    
    // A binary tree node
    struct TreeNode {
        int data;
        struct TreeNode* left;
        struct TreeNode* right;
    };
    
    // Function to create a new node
    struct TreeNode* createNode(int data) {
        struct TreeNode* newNode = (struct TreeNode*)malloc(sizeof(struct TreeNode));
        if (newNode == NULL) {
            printf("Memory allocation failed\\n");
            exit(1);
        }
        newNode->data = data;
        newNode->left = NULL;
        newNode->right = NULL;
        return newNode;
    }
    
    // Function to insert a node into the binary search tree
    struct TreeNode* insert(struct TreeNode* root, int data) {
        // If the tree is empty, return a new node
        if (root == NULL) {
            return createNode(data);
        }
        
        // Otherwise, recur down the tree
        if (data < root->data) {
            root->left = insert(root->left, data);
        } else if (data > root->data) {
            root->right = insert(root->right, data);
        }
        
        // Return the unchanged node pointer
        return root;
    }
    
    // Function to do inorder traversal of the tree
    void inorderTraversal(struct TreeNode* root) {
        if (root != NULL) {
            inorderTraversal(root->left);
            printf("%d ", root->data);
            inorderTraversal(root->right);
        }
    }
    
    // Function to free the memory used by the tree
    void freeTree(struct TreeNode* root) {
        if (root != NULL) {
            freeTree(root->left);
            freeTree(root->right);
            free(root);
        }
    }
    """,
    
    "simple_function": """
    #include <stdio.h>
    
    // Function to calculate the factorial of a number
    int factorial(int n) {
        if (n <= 1) {
            return 1;
        }
        return n * factorial(n - 1);
    }
    
    // Function to check if a number is prime
    int isPrime(int n) {
        if (n <= 1) {
            return 0;  // Not prime
        }
        
        for (int i = 2; i * i <= n; i++) {
            if (n % i == 0) {
                return 0;  // Not prime
            }
        }
        
        return 1;  // Prime
    }
    """
}

def test_direct_transpilation(example_name="linked_list", work_dir="./workspace"):
    """Test direct C to Rust transpilation using CToRustTranspilerChain."""
    logging.info(f"Testing direct transpilation for example: {example_name}")
    
    # Get the example C code
    c_code = EXAMPLES.get(example_name)
    if not c_code:
        logging.error(f"Example '{example_name}' not found")
        return
    
    # Create the transpiler
    transpiler = CToRustTranspilerChain(
        model_name="local-qwen",
        work_dir=work_dir
    )
    
    # Transpile the code
    result = transpiler.transpile_c_to_rust(c_code, example_name)
    
    # Print the results
    print(f"\nDirect Transpilation Results for '{example_name}':")
    print(f"Success: {result['success']}")
    print(f"Number of errors: {result['num_errors']}")
    print(f"Output file: {result['output_path'] if 'output_path' in result else 'Not available'}")
    
    if 'rust_code' in result:
        print("\nFirst 10 lines of Rust code:")
        print("\n".join(result['rust_code'].split("\n")[:10]))
    
    return result

def test_transpilation_with_feedback(example_name="linked_list", work_dir="./workspace"):
    """Test C to Rust transpilation with feedback using CToRustTranspilerWithFeedback."""
    logging.info(f"Testing transpilation with feedback for example: {example_name}")
    
    # Get the example C code
    c_code = EXAMPLES.get(example_name)
    if not c_code:
        logging.error(f"Example '{example_name}' not found")
        return
    
    # Create the transpiler with feedback
    transpiler = CToRustTranspilerWithFeedback(
        model_name="local-qwen",
        work_dir=work_dir,
        feedback_loops=2
    )
    
    # Transpile the code with feedback
    result = transpiler.transpile_with_feedback(c_code, f"{example_name}_feedback")
    
    # Print the results
    print(f"\nTranspilation with Feedback Results for '{example_name}':")
    print(f"Success: {result['success']}")
    print(f"Number of errors: {result['num_errors']}")
    print(f"Output file: {result['output_path'] if 'output_path' in result else 'Not available'}")
    
    if 'rust_code' in result:
        print("\nFirst 10 lines of Rust code:")
        print("\n".join(result['rust_code'].split("\n")[:10]))
    
    return result

def test_supervisor_transpilation(example_name="linked_list", work_dir="./workspace"):
    """Test C to Rust transpilation using the supervisor architecture."""
    logging.info(f"Testing supervisor transpilation for example: {example_name}")
    
    # Get the example C code
    c_code = EXAMPLES.get(example_name)
    if not c_code:
        logging.error(f"Example '{example_name}' not found")
        return
    
    # Create the supervisor
    supervisor = CToRustSupervisor(
        supervisor_model="local-qwen",
        work_dir=work_dir
    )
    
    # Transpile the code using the supervisor
    result = supervisor.transpile(c_code, f"{example_name}_supervised")
    
    # Print the results
    print(f"\nSupervisor Transpilation Results for '{example_name}':")
    print(f"Success: {result['success']}")
    print(f"Number of errors: {result['num_errors']}")
    print(f"Output file: {result['output_path'] if 'output_path' in result else 'Not available'}")
    
    if 'rust_code' in result:
        print("\nFirst 10 lines of Rust code:")
        print("\n".join(result['rust_code'].split("\n")[:10]))
    
    return result

def test_supervisor_with_feedback(example_name="linked_list", work_dir="./workspace"):
    """Test C to Rust transpilation using the supervisor architecture with feedback."""
    logging.info(f"Testing supervisor with feedback for example: {example_name}")
    
    # Get the example C code
    c_code = EXAMPLES.get(example_name)
    if not c_code:
        logging.error(f"Example '{example_name}' not found")
        return
    
    # Create the supervisor with feedback
    supervisor = SupervisorWithFeedback(
        supervisor_model="local-qwen",
        work_dir=work_dir,
        feedback_loops=2
    )
    
    # Transpile the code using the supervisor with feedback
    result = supervisor.transpile_with_feedback(c_code, f"{example_name}_supervised_feedback")
    
    # Print the results
    print(f"\nSupervisor with Feedback Results for '{example_name}':")
    print(f"Success: {result['success']}")
    print(f"Number of errors: {result['num_errors']}")
    print(f"Output file: {result['output_path'] if 'output_path' in result else 'Not available'}")
    
    if 'rust_code' in result:
        print("\nFirst 10 lines of Rust code:")
        print("\n".join(result['rust_code'].split("\n")[:10]))
    
    return result

def test_from_file(file_path, method="direct", work_dir="./workspace"):
    """Test C to Rust transpilation from a file."""
    logging.info(f"Testing transpilation from file: {file_path} using method: {method}")
    
    # Read the C code from the file
    with open(file_path, "r") as f:
        c_code = f.read()
    
    # Extract the file name without extension
    file_name = os.path.basename(file_path).split(".")[0]
    
    # Create the transpiler based on the method
    if method == "direct":
        transpiler = CToRustTranspilerChain(
            model_name="local-qwen",
            work_dir=work_dir
        )
        
        # Transpile the code
        result = transpiler.transpile_c_to_rust(c_code, file_name)
    
    elif method == "feedback":
        transpiler = CToRustTranspilerWithFeedback(
            model_name="local-qwen",
            work_dir=work_dir,
            feedback_loops=2
        )
        
        # Transpile the code with feedback
        result = transpiler.transpile_with_feedback(c_code, file_name)
    
    elif method == "supervisor":
        supervisor = CToRustSupervisor(
            supervisor_model="local-qwen",
            work_dir=work_dir
        )
        
        # Transpile using the supervisor
        result = supervisor.transpile(c_code, file_name)
    
    elif method == "supervisor_feedback":
        supervisor = SupervisorWithFeedback(
            supervisor_model="local-qwen",
            work_dir=work_dir,
            feedback_loops=2
        )
        
        # Transpile using the supervisor with feedback
        result = supervisor.transpile_with_feedback(c_code, file_name)
    
    else:
        logging.error(f"Unknown method: {method}")
        return
    
    # Print the results
    print(f"\nTranspilation Results for '{file_path}' using method '{method}':")
    print(f"Success: {result.get('success', False)}")
    print(f"Number of errors: {result.get('num_errors', 0)}")
    print(f"Output file: {result.get('output_path', 'Not available')}")
    
    # Always display the Rust code if it exists, even if compilation failed
    if 'rust_code' in result and result['rust_code']:
        print("\nFirst 10 lines of Rust code:")
        code_lines = result['rust_code'].split("\n")
        print("\n".join(code_lines[:min(10, len(code_lines))]))
    else:
        print("\nNo Rust code was generated.")
    
    return result

def main():
    """Main function to run the test script."""
    parser = argparse.ArgumentParser(description="Test C to Rust transpilation")
    parser.add_argument("--example", choices=list(EXAMPLES.keys()), default="linked_list",
                        help="Example C code to transpile")
    parser.add_argument("--method", choices=["direct", "feedback", "supervisor", "supervisor_feedback", "all"],
                        default="all", help="Transpilation method to use")
    parser.add_argument("--file", help="Path to a C file to transpile")
    parser.add_argument("--work-dir", default="./workspace", help="Working directory for transpilation")
    
    args = parser.parse_args()
    
    # Create the work directory if it doesn't exist
    os.makedirs(args.work_dir, exist_ok=True)
    
    # If a file is specified, transpile it
    if args.file:
        test_from_file(args.file, args.method, args.work_dir)
        return
    
    # Otherwise, run the specified tests
    if args.method == "direct" or args.method == "all":
        test_direct_transpilation(args.example, args.work_dir)
    
    if args.method == "feedback" or args.method == "all":
        test_transpilation_with_feedback(args.example, args.work_dir)
    
    if args.method == "supervisor" or args.method == "all":
        test_supervisor_transpilation(args.example, args.work_dir)
    
    if args.method == "supervisor_feedback" or args.method == "all":
        test_supervisor_with_feedback(args.example, args.work_dir)

if __name__ == "__main__":
    main()
