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

## C to Rust Transpilation with LangChain & Supervisor

This project provides two ways to convert C code to Rust using LangChain and the supervisor architecture:

1. **Test Script** (`test_c_to_rust.py`)
   ```sh
   # Run built-in examples:
   python test_c_to_rust.py --example linked_list --method all

   # Transpile a custom C file:
   python test_c_to_rust.py --file path/to/sample.c --method supervisor_feedback
   ```
   Available methods:
   - `direct`: Basic transpilation
   - `feedback`: Transpilation with error-correction loops
   - `supervisor`: Task-routing supervisor
   - `supervisor_feedback`: Supervisor + feedback loops
   - `all`: Run all methods (built-in examples only)

2. **CLI** (`supervisor.py`)
   Place your C files in `workspace/wspace/`, then from the project root:
   ```powershell
   # Transpile all .c files in workspace/wspace:
   python supervisor.py --work-dir workspace

   # Transpile a single file with feedback:
   python supervisor.py --file workspace/wspace/sample_binsearch.c \
     --work-dir workspace --method supervisor_feedback
   ```
   Flags:
   - `--work-dir`: Working directory (default: `workspace`)
   - `--file`: Path to a single C file (optional)
   - `--method`: `supervisor` or `supervisor_feedback` (default: `supervisor`)
   - `--model`: Supervisor model name (default: `local-qwen`)

Outputs are written to:
```
workspace/results/<task_type>/<file_name>.rs
```

Enjoy translating!
