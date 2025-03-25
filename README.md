# GAINTRUST

This project is based heavily on the following paper: https://arxiv.org/pdf/2405.11514

## Installation

Follow these steps to set up and run the project:

1. **Clone and setup**  
   ```sh
   git clone https://github.com/muhammadusajid-tamu/GAINTRUST.git
   cd GAINTRUST
   chmod u+x setup.sh
   ./setup.sh
   ```
   This will install all python and rust dependencies, as well as create a virtual python environment for the project.

2. **Configuartion**  
    The configuration is loaded from config.json in the same directory as driver.py

    The file to translate must be located at:
    ```
    /bms/language/lib_name/function_name/function_name.language
    ```
    The following arguments are required:
    ```json
        "benchmark_name": "lib_name/function_name",
        "submodule_name": "function_name",
        "tag": "test"
    ```

    Other arguments can be changed, but are not required:
    ```json
        "language": "c"
    ```
    The default translation language is C.

    The translation output will be in the directory:
    ```
    /transpilations/language/lib_name/function_name/tag/
    ```

3. **Execution**
    ```sh
    python driver.py
    ```

## C to Rust Transpilation with LangChain

This project now includes enhanced C to Rust transpilation capabilities using LangChain integration and a supervisor architecture. These new features provide more efficient and effective code conversion with feedback loops for improved results.

### Key Components

1. **LangChain Integration**
   - `langchain_local_integration.py`: Adapts local models for use with LangChain and implements specialized C to Rust transpilation chains
   - Provides direct transpilation and transpilation with feedback loops

2. **Supervisor Architecture**
   - `supervisor.py`: Implements a task routing system that analyzes C code and determines the appropriate transpilation strategy
   - Manages the workflow and incorporates feedback loops for improved results

3. **Testing**
   - `test_c_to_rust.py`: Demonstrates the use of the C to Rust transpilation capabilities with various examples
   - Supports multiple transpilation methods: direct, with feedback, supervisor-based, and supervisor with feedback

### Usage

To test the C to Rust transpilation system:

```sh
# Test with built-in examples
python test_c_to_rust.py --example linked_list --method all

# Test with a custom C file
python test_c_to_rust.py --file test_samples/sample.c --method supervisor_feedback

# Available methods:
# - direct: Basic transpilation
# - feedback: Transpilation with error correction feedback loops
# - supervisor: Transpilation with task routing
# - supervisor_feedback: Transpilation with task routing and feedback loops
# - all: Run all methods (only for built-in examples)
