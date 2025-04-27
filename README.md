# GAINTRUST

This project is based heavily on and extends the codebase of the following paper: https://arxiv.org/pdf/2405.11514

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
        "tag": "base_translation"
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

    If c2rust is enabled
    ```json
        "c2rust": true
    ```
    c2rust will attempt to transpile the C code to unsafe Rust, then use that as the basis for translation. The prompt will be updated and the 

3. **Execution**
    ```sh
    python driver.py
    ```

## C to Rust Transpilation with LangChain & Supervisor
   **CLI** (`supervisor.py`)
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


## FAQ

1. How can I use a different model? 

Each model is an implementation of the abstract QueryEngine class located in llms.py. If a custom implemtation is desired that is the place to look. It is possible, but not recommended, to change the link for the model of an existing implementation in order to use a new model without a custom implementation.


2. How are models stored?

Models are downloaded through the huggingface python api and stored locally on first run. If you'd like a gated model please login using the huggingface cli before running. It should automatically pick up your token. Alternatively, you can specificy your token as a parameter in the pipeline creation. 
```python
pipe = pipeline(
    "text-generation",
    model="gated-model-name",
    token="hf_yourAccessTokenHere"
)
```
[HuggingFace CLI Docs](https://huggingface.co/docs/huggingface_hub/en/guides/cli) 

3. Its running slow.

The device is automatically selected based on your system resources. If GPU is forced but not enough VRAM is available, memory transfers between RAM and VRAM will destroy performance. First, ensure your hardware and drivers are working properly. If performance is still slower, a smaller model would likely be your solution. 
