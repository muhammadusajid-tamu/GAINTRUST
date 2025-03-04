# GAINTRUST

## Installation

This project is based heavily on the following paper: https://arxiv.org/pdf/2405.11514

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
