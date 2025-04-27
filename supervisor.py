"""
Supervisor Architecture for C to Rust Transpilation

This module implements a supervisor architecture that specializes in C to Rust code transpilation,
using LangChain and GAINTRUST's local models.
"""

from typing import List, Dict, Any, Union, Optional, Callable, Type
import logging
import json
import os
import subprocess
from pathlib import Path

# LangChain imports
from langchain_core.language_models import BaseChatModel, BaseLanguageModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.outputs import ChatGeneration, ChatResult, LLMResult
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import Runnable, RunnablePassthrough

# Import GAINTRUST components
from llms import QueryEngine, Prompt, USER, ASSISTANT, LocalQwen, CodeLlama
from llms import QueryEngineFactory
from utils import tag, cd, compile_and_record_query, parse_error_timepass, rudra_suggest
from langchain_local_integration import LocalModelLangChainAdapter, CToRustTranspilerChain, CToRustTranspilerWithFeedback

# Task types for C to Rust transpilation
TASK_TYPES = {
    "DIRECT_TRANSPILATION": "Direct C to Rust transpilation",
    "DECOMPOSITION": "Decompose C code into smaller parts before transpilation",
    "OPTIMIZATION": "Optimize the Rust code after transpilation",
    "ERROR_FIXING": "Fix compilation errors in transpiled Rust code",
    "TESTING": "Generate tests for the transpiled Rust code"
}

class TaskRouter:
    """
    Analyzes C code and determines the appropriate transpilation strategy.
    """
    
    def __init__(
        self,
        model: Union[str, BaseLanguageModel] = "local-qwen",
        global_constraints: List[str] = None
    ):
        """
        Initialize the task router.
        
        Args:
            model: The model to use for routing (model name or LangChain model)
            global_constraints: Optional list of constraints to apply
        """
        self.global_constraints = global_constraints or []
        
        # Initialize the model
        if isinstance(model, str):
            if model in ["local-qwen", "codellama"]:
                # Create a local model
                if model == "local-qwen":
                    engine = LocalQwen(self.global_constraints)
                else:
                    engine = CodeLlama(self.global_constraints)
                self.model = LocalModelLangChainAdapter(engine, model_name=model)
            else:
                # Assume it's a remote model like GPT-4, Claude, etc.
                try:
                    from langchain_integration import LangChainFactory
                    self.model = LangChainFactory.create_langchain_model(
                        model, global_constraints=self.global_constraints
                    )
                except ImportError:
                    # Fallback to local model if remote integration is not available
                    engine = LocalQwen(self.global_constraints)
                    self.model = LocalModelLangChainAdapter(engine, model_name="local-qwen")
        else:
            # Already a LangChain model
            self.model = model
    
    def analyze_code(self, c_code: str) -> Dict[str, Any]:
        """
        Analyze C code to determine the best transpilation strategy.
        
        Args:
            c_code: The C code to analyze
            
        Returns:
            A dictionary with the analysis results
        """
        # Create a prompt for code analysis
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are an expert C and Rust programmer. Your task is to analyze C code and determine 
            the best strategy for transpiling it to Rust. Consider:
            
            1. Code complexity (LOC, nesting depth, control structures)
            2. Memory management patterns
            3. Use of C-specific features (pointers, structs, unions)
            4. Potential safety issues
            5. Potential optimization opportunities
            
            You MUST respond with a valid JSON object containing ONLY these fields:
            {{
                "task_type": "DIRECT_TRANSPILATION", // One of: DIRECT_TRANSPILATION, DECOMPOSITION, OPTIMIZATION, ERROR_FIXING, TESTING
                "reasoning": "Your reasoning here",
                "complexity_score": 5, // A number from 1-10
                "key_challenges": ["Challenge 1", "Challenge 2"],
                "decomposition_strategy": "Strategy description if applicable, otherwise null"
            }}
            
            Do not include any explanations, markdown formatting, or text outside of the JSON object.
            """),
            ("human", """
            Please analyze the following C code and recommend the best transpilation strategy:
            
            ```c
            {{ c_code }}
            ```
            
            Return ONLY a valid JSON object with the specified fields.
            """)
        ])
        
        # Create a chain for analysis with JSON output parsing
        analysis_chain = analysis_prompt | self.model | JsonOutputParser()
        
        # Get the analysis
        try:
            analysis = analysis_chain.invoke({"c_code": c_code})
            logging.info(f"Code analysis: {analysis}")
            return analysis
        except Exception as e:
            logging.error(f"Error in code analysis: {e}")
            # Return a default analysis
            return {
                "task_type": "DIRECT_TRANSPILATION",
                "reasoning": "Failed to analyze code due to error, defaulting to direct transpilation",
                "complexity_score": 5,
                "key_challenges": ["Unknown due to analysis error"],
                "decomposition_strategy": None
            }

class CToRustSupervisor:
    """
    Supervisor architecture specialized for C to Rust transpilation.
    """
    
    def __init__(
        self,
        supervisor_model: Union[str, BaseLanguageModel] = "local-qwen",
        worker_models: Dict[str, Union[str, BaseLanguageModel]] = None,
        global_constraints: List[str] = None,
        work_dir: str = "./workspace"
    ):
        """
        Initialize the C to Rust supervisor.
        
        Args:
            supervisor_model: The model to use as supervisor (model name or LangChain model)
            worker_models: Dictionary mapping task types to worker models
            global_constraints: Optional list of constraints to apply
            work_dir: Working directory for transpilation
        """
        self.global_constraints = global_constraints or []
        self.work_dir = work_dir
        
        # Create directories
        os.makedirs(f"{self.work_dir}/wspace", exist_ok=True)
        os.makedirs(f"{self.work_dir}/results", exist_ok=True)
        
        # Initialize supervisor model
        if isinstance(supervisor_model, str):
            if supervisor_model in ["local-qwen", "codellama"]:
                # Create a local model
                if supervisor_model == "local-qwen":
                    engine = LocalQwen(self.global_constraints)
                else:
                    engine = CodeLlama(self.global_constraints)
                self.supervisor = LocalModelLangChainAdapter(engine, model_name=supervisor_model)
            else:
                # Assume it's a remote model
                try:
                    from langchain_integration import LangChainFactory
                    self.supervisor = LangChainFactory.create_langchain_model(
                        supervisor_model, global_constraints=self.global_constraints
                    )
                except ImportError:
                    # Fallback to local model if remote integration is not available
                    engine = LocalQwen(self.global_constraints)
                    self.supervisor = LocalModelLangChainAdapter(engine, model_name="local-qwen")
        else:
            # Already a LangChain model
            self.supervisor = supervisor_model
        
        # Initialize task router
        self.task_router = TaskRouter(self.supervisor, global_constraints=self.global_constraints)
        
        # Initialize worker models
        self.workers = {}
        default_worker_models = {
            "DIRECT_TRANSPILATION": "local-qwen",
            "DECOMPOSITION": "local-qwen",
            "OPTIMIZATION": "local-qwen",
            "ERROR_FIXING": "local-qwen",
            "TESTING": "local-qwen"
        }
        
        worker_models = worker_models or default_worker_models
        
        for task_type, worker_model in worker_models.items():
            if isinstance(worker_model, str):
                if worker_model in ["local-qwen", "codellama"]:
                    # Create a transpiler chain for this task type
                    if task_type == "ERROR_FIXING":
                        # Use the feedback-enabled transpiler for error fixing
                        self.workers[task_type] = CToRustTranspilerWithFeedback(
                            model_name=worker_model,
                            global_constraints=self.global_constraints,
                            work_dir=f"{self.work_dir}/{task_type.lower()}"
                        )
                    else:
                        # Use the standard transpiler for other tasks
                        self.workers[task_type] = CToRustTranspilerChain(
                            model_name=worker_model,
                            global_constraints=self.global_constraints,
                            work_dir=f"{self.work_dir}/{task_type.lower()}"
                        )
                else:
                    # For remote models, we still use our transpiler chains
                    try:
                        from langchain_integration import LangChainFactory
                        remote_model = LangChainFactory.create_langchain_model(
                            worker_model, global_constraints=self.global_constraints
                        )
                        
                        # Create a transpiler that uses this remote model
                        if task_type == "ERROR_FIXING":
                            self.workers[task_type] = CToRustTranspilerWithFeedback(
                                model_name=worker_model,
                                global_constraints=self.global_constraints,
                                work_dir=f"{self.work_dir}/{task_type.lower()}"
                            )
                        else:
                            self.workers[task_type] = CToRustTranspilerChain(
                                model_name=worker_model,
                                global_constraints=self.global_constraints,
                                work_dir=f"{self.work_dir}/{task_type.lower()}"
                            )
                    except ImportError:
                        # Fallback to local model
                        if task_type == "ERROR_FIXING":
                            self.workers[task_type] = CToRustTranspilerWithFeedback(
                                model_name="local-qwen",
                                global_constraints=self.global_constraints,
                                work_dir=f"{self.work_dir}/{task_type.lower()}"
                            )
                        else:
                            self.workers[task_type] = CToRustTranspilerChain(
                                model_name="local-qwen",
                                global_constraints=self.global_constraints,
                                work_dir=f"{self.work_dir}/{task_type.lower()}"
                            )
            else:
                # Already a LangChain model or transpiler
                self.workers[task_type] = worker_model
    
    def transpile(self, c_code: str, file_name: str = "transpiled") -> Dict[str, Any]:
        """
        Transpile C code to Rust using the supervisor architecture.
        
        Args:
            c_code: The C code to transpile
            file_name: Name for the output file (without extension)
            
        Returns:
            A dictionary with the transpilation results
        """
        logging.info(f"Transpiling C code to Rust using supervisor architecture")
        
        # Step 1: Analyze the code to determine the best transpilation strategy
        analysis = self.task_router.analyze_code(c_code)
        task_type = analysis.get("task_type", "DIRECT_TRANSPILATION")
        
        logging.info(f"Selected task type: {task_type}")
        logging.info(f"Reasoning: {analysis.get('reasoning', 'No reasoning provided')}")
        
        # Step 2: Route to the appropriate worker
        if task_type not in self.workers:
            logging.warning(f"Invalid task type: {task_type}, defaulting to DIRECT_TRANSPILATION")
            task_type = "DIRECT_TRANSPILATION"
        
        worker = self.workers[task_type]
        
        # Step 3: Transpile the code
        if task_type == "DECOMPOSITION":
            # Special handling for decomposition
            return self._handle_decomposition(c_code, file_name, analysis)
        elif task_type == "ERROR_FIXING":
            # Special handling for error fixing
            if isinstance(worker, CToRustTranspilerWithFeedback):
                return worker.transpile_with_feedback(c_code, file_name)
            else:
                # Fallback to direct transpilation with the worker
                return worker.transpile_c_to_rust(c_code, file_name)
        else:
            # Direct transpilation with the worker
            return worker.transpile_c_to_rust(c_code, file_name)
    
    def _handle_decomposition(self, c_code: str, file_name: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle decomposition-based transpilation.
        
        Args:
            c_code: The C code to transpile
            file_name: Name for the output file
            analysis: The code analysis results
            
        Returns:
            A dictionary with the transpilation results
        """
        logging.info("Using decomposition strategy for transpilation")
        
        # Get the decomposition strategy from the analysis
        decomposition_strategy = analysis.get("decomposition_strategy", None)
        
        if not decomposition_strategy:
            logging.warning("No decomposition strategy provided, generating one")
            
            # Create a prompt for generating a decomposition strategy
            decomp_prompt = ChatPromptTemplate.from_messages([
                ("system", """
                You are an expert C programmer. Your task is to decompose a C program into logical parts
                that can be transpiled to Rust independently. Identify:
                
                1. Type definitions and structs
                2. Function declarations
                3. Global variables
                4. Implementation of each function
                
                Respond with a JSON object containing:
                - parts: A list of objects, each with:
                  - name: A descriptive name for this part
                  - code: The C code for this part
                  - description: Brief description of what this part does
                """),
                ("human", f"""
                Please decompose the following C code into logical parts:
                
                ```c
                {{ c_code }}
                ```
                """)
            ])
            
            # Create a chain for decomposition with JSON output parsing
            decomp_chain = decomp_prompt | self.supervisor | JsonOutputParser()
            
            try:
                decomposition = decomp_chain.invoke({})
                parts = decomposition.get("parts", [])
            except Exception as e:
                logging.error(f"Error in decomposition: {e}")
                # Fallback to direct transpilation
                worker = self.workers["DIRECT_TRANSPILATION"]
                return worker.transpile_c_to_rust(c_code, file_name)
        else:
            # Use the provided decomposition strategy
            try:
                parts = decomposition_strategy.get("parts", [])
            except (AttributeError, TypeError):
                logging.error("Invalid decomposition strategy format")
                # Fallback to direct transpilation
                worker = self.workers["DIRECT_TRANSPILATION"]
                return worker.transpile_c_to_rust(c_code, file_name)
        
        if not parts:
            logging.warning("No parts identified for decomposition, falling back to direct transpilation")
            worker = self.workers["DIRECT_TRANSPILATION"]
            return worker.transpile_c_to_rust(c_code, file_name)
        
        # Transpile each part
        transpiled_parts = []
        for i, part in enumerate(parts):
            part_name = part.get("name", f"part_{i}")
            part_code = part.get("code", "")
            
            if not part_code:
                continue
            
            logging.info(f"Transpiling part: {part_name}")
            
            # Use the DIRECT_TRANSPILATION worker for each part
            worker = self.workers["DIRECT_TRANSPILATION"]
            result = worker.transpile_c_to_rust(part_code, f"{file_name}_{part_name}")
            
            if result.get("success", False) and "rust_code" in result:
                transpiled_parts.append({
                    "name": part_name,
                    "c_code": part_code,
                    "rust_code": result["rust_code"],
                    "success": True
                })
            else:
                transpiled_parts.append({
                    "name": part_name,
                    "c_code": part_code,
                    "success": False,
                    "error": result.get("error", "Unknown error")
                })
        
        # Combine the transpiled parts
        combine_prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are an expert Rust programmer. Your task is to combine multiple Rust code snippets
            into a single, coherent Rust module. Ensure:
            
            1. No duplicate imports or type definitions
            2. Proper organization of code
            3. Consistent naming and style
            4. Proper handling of dependencies between parts
            
            Return only the combined Rust code in a markdown rust block.
            """),
            ("human", f"""
            I need to combine several independently transpiled parts of a C program into a single Rust module.
            
            Original C code:
            ```c
            {{ c_code }}
            ```
            
            Transpiled parts:
            {{ parts_json }}
            
            Please create a single, coherent Rust module that combines all these parts correctly.
            The combined code should:
            1. Have no duplicate imports or type definitions
            2. Maintain the correct order of declarations
            3. Be well-organized and follow Rust best practices
            4. Compile without errors
            
            Return the complete Rust code as a single module.
            """)
        ])
        
        # Create a chain for combining parts
        combine_chain = combine_prompt | self.supervisor | StrOutputParser()
        
        try:
            combined_code = combine_chain.invoke({
                "c_code": c_code,
                "parts_json": json.dumps([{
                    "name": part["name"],
                    "rust_code": part.get("rust_code", "// Failed to transpile this part")
                } for part in transpiled_parts], indent=2)
            })
            
            # Extract code from markdown blocks if present
            if "```rust" in combined_code:
                combined_code = combined_code.split("```rust")[1].split("```")[0].strip()
            elif "```" in combined_code:
                combined_code = combined_code.split("```")[1].split("```")[0].strip()
            
            # Compile and check for errors
            src_dir = f"{self.work_dir}/wspace"
            comp_out = compile_and_record_query(
                combined_code, 
                src_dir, 
                combine_prompt.format_messages({})[0].content + combine_prompt.format_messages({})[1].content,
                log_id=file_name
            )
            
            # Parse compilation errors
            parsed_comp_out = parse_error_timepass(comp_out.stderr, file_name)
            num_errs = parsed_comp_out[-1]
            
            logging.info(f"Combined code has {num_errs} errors")
            
            # Save the result
            res_dir = f"{self.work_dir}/results"
            with open(f"{res_dir}/{file_name}.c", "w") as fw:
                fw.write(c_code)
            
            with open(f"{res_dir}/{file_name}.rs", "w") as fw:
                fw.write(combined_code)
            
            # If there are errors, try to fix them
            if num_errs > 0 and "ERROR_FIXING" in self.workers:
                logging.info(f"Combined code has {num_errs} errors, attempting to fix")
                
                # Use the error fixing worker
                error_fixer = self.workers["ERROR_FIXING"]
                if isinstance(error_fixer, CToRustTranspilerWithFeedback):
                    # Create a temporary file with the combined code
                    with open(f"{res_dir}/{file_name}_combined.rs", "w") as fw:
                        fw.write(combined_code)
                    
                    # Fix the errors
                    fix_result = error_fixer.transpile_with_feedback(c_code, f"{file_name}_fixed")
                    
                    if fix_result.get("success", False) and "rust_code" in fix_result:
                        # Update the combined code
                        combined_code = fix_result["rust_code"]
                        num_errs = 0
                        
                        # Save the fixed code
                        with open(f"{res_dir}/{file_name}.rs", "w") as fw:
                            fw.write(combined_code)
            
            return {
                "success": num_errs == 0,
                "num_errors": num_errs,
                "rust_code": combined_code,
                "c_code": c_code,
                "file_name": file_name,
                "output_path": f"{res_dir}/{file_name}.rs",
                "parts": transpiled_parts
            }
            
        except Exception as e:
            logging.error(f"Error in combining parts: {e}")
            
            # Fallback to direct transpilation
            logging.info("Falling back to direct transpilation")
            worker = self.workers["DIRECT_TRANSPILATION"]
            return worker.transpile_c_to_rust(c_code, file_name)


class SupervisorWithFeedback(CToRustSupervisor):
    """
    Enhanced supervisor with feedback loop for improved C to Rust transpilation.
    """
    
    def __init__(
        self,
        supervisor_model: Union[str, BaseLanguageModel] = "local-qwen",
        worker_models: Dict[str, Union[str, BaseLanguageModel]] = None,
        global_constraints: List[str] = None,
        work_dir: str = "./workspace",
        feedback_loops: int = 2,
        use_rudra: bool = False
    ):
        """
        Initialize the supervisor with feedback.
        
        Args:
            supervisor_model: The model to use as supervisor
            worker_models: Dictionary mapping task types to worker models
            global_constraints: Optional list of constraints to apply
            work_dir: Working directory for transpilation
            feedback_loops: Number of feedback loops to perform
            use_rudra: Use rudra-like error explanations in feedback
        """
        super().__init__(supervisor_model, worker_models, global_constraints, work_dir)
        self.feedback_loops = feedback_loops
        self.use_rudra = use_rudra
    
    def transpile_with_feedback(self, c_code: str, file_name: str = "transpiled") -> Dict[str, Any]:
        """
        Transpile C code to Rust with feedback loop for improved results.
        
        Args:
            c_code: The C code to transpile
            file_name: Name for the output file (without extension)
            
        Returns:
            A dictionary with the transpilation results
        """
        # Initial transpilation
        result = self.transpile(c_code, file_name)
        
        # Prepare results directory for this file’s feedback outputs
        res_base_dir = os.path.join(self.work_dir, "results", file_name)
        os.makedirs(res_base_dir, exist_ok=True)
        
        # Initialize list to track feedback output paths
        result["feedback_paths"] = []
        
        # If successful or no Rust code was generated, return immediately
        if result.get("success", False) or "rust_code" not in result:
            return result
        
        # Feedback loop
        for i in range(self.feedback_loops):
            logging.info(f"Starting supervisor feedback loop {i+1}/{self.feedback_loops}")
            
            rust_code = result["rust_code"]
            
            # Prepare compile directory for this feedback iteration under results
            compile_dir = os.path.join(res_base_dir, f"feedback_{i+1}")
            os.makedirs(compile_dir, exist_ok=True)
            os.makedirs(f"{compile_dir}/src", exist_ok=True)
            with open(f"{compile_dir}/src/lib.rs", "w", encoding="utf-8") as fw:
                fw.write(rust_code)
            
            # Compile and get errors
            comp_out = compile_and_record_query(
                rust_code,
                compile_dir,
                "Feedback compilation",
                log_id=f"{file_name}_feedback_{i+1}"
            )
            
            if self.use_rudra:
                error_output = rudra_suggest(compile_dir, f"{file_name}_feedback_{i+1}")
            else:
                error_output = comp_out.stderr.decode("utf-8", errors="ignore") if hasattr(comp_out, 'stderr') else ""
            
            # Create feedback prompt
            feedback_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert Rust programmer. Your task is to fix compilation errors in Rust code that was translated from C."),
                ("human", """
I have the following C code:

```c
{c_code}
```

It was translated to Rust, but there are compilation errors:

```rust
{rust_code}
```

Here are the compilation errors:

```
{error_output}
```

Please fix the Rust code to address all compilation errors. The fixed code should:
- Compile without errors
- Maintain the same functionality as the original C code
- Use safe Rust practices
- Avoid raw pointers
- Use Box pointers when appropriate
- Avoid unnecessary Traits and Generics

Return only the fixed Rust code in a markdown rust block.
""")
            ])
            
            # Create the feedback chain
            feedback_chain = feedback_prompt | self.supervisor | StrOutputParser()
            
            try:
                # Generate improved Rust code
                improved_response = feedback_chain.invoke({
                    "c_code": c_code,
                    "rust_code": rust_code,
                    "error_output": error_output
                })
                
                # Extract code from markdown blocks if present
                improved_rust_code = improved_response
                if "```rust" in improved_response:
                    improved_rust_code = improved_response.split("```rust")[1].split("```")[0].strip()
                elif "```" in improved_response:
                    improved_rust_code = improved_response.split("```")[1].split("```")[0].strip()
                
                # Compile and check for errors using the same compile_dir
                comp_out = compile_and_record_query(
                    improved_rust_code,
                    compile_dir,
                    "",
                    log_id=f"{file_name}_feedback_{i+1}"
                )
                
                # Parse compilation errors
                parsed_comp_out = parse_error_timepass(comp_out.stderr, file_name)
                num_errs = parsed_comp_out[-1]
                
                logging.info(f"Feedback loop {i+1}: {num_errs} errors")
                
                # Update the result
                result["rust_code"] = improved_rust_code
                result["num_errors"] = num_errs
                result["success"] = num_errs == 0
                
                # Save the improved Rust code for this iteration
                feedback_path = os.path.join(res_base_dir, f"{file_name}_feedback_{i+1}.rs")
                with open(feedback_path, "w", encoding="utf-8") as fw:
                    fw.write(improved_rust_code)
                
                # Record this feedback file path
                result["feedback_paths"].append(feedback_path)
                
                # If no errors, we're done
                if num_errs == 0:
                    # Save the final version
                    final_path = os.path.join(res_base_dir, f"{file_name}.rs")
                    with open(final_path, "w", encoding="utf-8") as fw:
                        fw.write(improved_rust_code)
                    result["output_path"] = final_path
                    break
                
            except Exception as e:
                logging.error(f"Error in feedback loop {i+1}: {e}")
                continue
        
        # Clean up
        src_dir = f"{self.work_dir}/wspace"
        with cd(src_dir):
            subprocess.run("cargo clean", capture_output=True, shell=True)
        
        return result


def example_usage():
    """Example usage of the C to Rust supervisor architecture."""
    print("=== C to Rust Supervisor Architecture Examples ===\n")
    
    # Example C code
    c_code = """
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
    """
    
    # Example 1: Basic supervisor
    print("Example 1: Basic C to Rust Supervisor")
    try:
        supervisor = CToRustSupervisor(supervisor_model="local-qwen")
        result = supervisor.transpile(c_code, "linked_list_supervised")
        
        print(f"Success: {result['success']}")
        print(f"Number of errors: {result['num_errors']}")
        print(f"Output file: {result['output_path']}")
        print(f"First few lines of Rust code:")
        print("\n".join(result['rust_code'].split("\n")[:10]))
        print()
    except Exception as e:
        print(f"Error in Example 1: {e}\n")
    
    # Example 2: Supervisor with feedback
    print("Example 2: C to Rust Supervisor with Feedback")
    try:
        supervisor = SupervisorWithFeedback(
            supervisor_model="local-qwen", 
            feedback_loops=2
        )
        result = supervisor.transpile_with_feedback(c_code, "linked_list_supervised_feedback")
        
        print(f"Success: {result['success']}")
        print(f"Number of errors: {result['num_errors']}")
        print(f"Output file: {result['output_path'] if 'output_path' in result else 'Not available'}")
        print(f"First few lines of Rust code:")
        print("\n".join(result['rust_code'].split("\n")[:10]))
        print()
    except Exception as e:
        print(f"Error in Example 2: {e}\n")


if __name__ == "__main__":
    import argparse
    import os
    import glob
    parser = argparse.ArgumentParser(description="C to Rust transpilation (supervisor)")
    parser.add_argument("--file", "-f", help="Path to C source file to transpile")
    parser.add_argument("--method", choices=["supervisor", "supervisor_feedback"], default="supervisor", help="Transpilation method")
    parser.add_argument("--work-dir", "-w", default="./workspace", help="Working directory for transpilation")
    parser.add_argument("--model", default="local-qwen", help="Supervisor model name")
    parser.add_argument("--loops", "-l", type=int, default=2, help="Number of feedback loops to perform")
    parser.add_argument("--use-rudra", action="store_true", help="Use rudra-like error explanations in feedback")
    args = parser.parse_args()

    # Collect C files
    if args.file:
        files = [args.file]
    else:
        wspace = os.path.join(args.work_dir, "wspace")
        files = glob.glob(os.path.join(wspace, "*.c"))
        if not files:
            print(f"No .c files found in {wspace}")
            exit(1)

    # Initialize supervisor
    if args.method == "supervisor_feedback":
        sup = SupervisorWithFeedback(
            supervisor_model=args.model,
            work_dir=args.work_dir,
            feedback_loops=args.loops,
            use_rudra=args.use_rudra
        )
    else:
        sup = CToRustSupervisor(
            supervisor_model=args.model, 
            work_dir=args.work_dir
        )

    # Transpile each file
    for file_path in files:
        print(f"\nTranspiling: {file_path}")
        with open(file_path, "r") as f:
            c_code = f.read()
        base = os.path.splitext(os.path.basename(file_path))[0]
        if args.method == "supervisor_feedback":
            result = sup.transpile_with_feedback(c_code, base)
        else:
            result = sup.transpile(c_code, base)
        print("Success:", result.get("success"))
        print("Number of errors:", result.get("num_errors"))
        print("Output file:", result.get("output_path"))
