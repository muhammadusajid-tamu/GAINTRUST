"""
LangChain integration for local models in GAINTRUST

This module provides specialized integration between GAINTRUST's local LLM implementations
(like LocalQwen) and LangChain's ecosystem, specifically for C to Rust transpilation.
"""

from typing import List, Dict, Any, Union, Optional, Callable, Type, ClassVar
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
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnablePassthrough

# Import GAINTRUST components
from llms import QueryEngine, Prompt, USER, ASSISTANT, LocalQwen, CodeLlama
from llms import QueryEngineFactory
from utils import tag, cd, compile_and_record_query, parse_error_timepass

class LocalModelLangChainAdapter(BaseChatModel):
    """
    Adapter for GAINTRUST's local models (LocalQwen, CodeLlama) to work with LangChain.
    Specialized for C to Rust transpilation.
    """
    
    # Class attributes for Pydantic compatibility
    _query_engine: Optional[QueryEngine] = None
    _model_name: Optional[str] = None
    
    def __init__(
        self, 
        query_engine: QueryEngine,
        model_name: str = None,
        verbose: bool = False
    ):
        """
        Initialize the adapter for local models.
        
        Args:
            query_engine: An instance of a GAINTRUST QueryEngine for a local model
            model_name: Optional name to identify this model
            verbose: Whether to print verbose output
        """
        super().__init__(verbose=verbose)
        self._query_engine = query_engine
        self._model_name = model_name or type(query_engine).__name__
    
    @property
    def query_engine(self) -> QueryEngine:
        """Get the query engine."""
        return self._query_engine
    
    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self._model_name
    
    def _generate(
        self, 
        messages: List[BaseMessage], 
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> ChatResult:
        """
        Generate a response using the GAINTRUST local model.
        This method is required by LangChain's BaseChatModel.
        """
        # Convert LangChain messages to GAINTRUST Prompt format
        prompt = self._convert_messages_to_prompt(messages)
        
        # Add any additional model parameters from kwargs
        model_params = {"temperature": 0.2}  # Default
        if "temperature" in kwargs:
            model_params["temperature"] = kwargs["temperature"]
        if "max_length" in kwargs:
            model_params["max_length"] = kwargs["max_length"]
        if "do_sample" in kwargs:
            model_params["do_sample"] = kwargs["do_sample"]
        
        # Query the model using GAINTRUST's QueryEngine
        response = self.query_engine.query(prompt, model_params)
        
        # Format the response for LangChain
        message = AIMessage(content=response)
        generation = ChatGeneration(message=message)
        
        return ChatResult(generations=[generation])
    
    def _convert_messages_to_prompt(self, messages: List[BaseMessage]) -> Prompt:
        """
        Convert LangChain messages to a GAINTRUST Prompt object.
        
        Args:
            messages: List of LangChain message objects
            
        Returns:
            A GAINTRUST Prompt object
        """
        context = ""
        instruction = ""
        constraints = []
        extra_information = ""
        history = []
        
        # Process each message
        for i, message in enumerate(messages):
            if isinstance(message, SystemMessage):
                # System messages become context
                context += message.content + "\n"
            
            elif isinstance(message, HumanMessage):
                # If this is the last human message, treat it as the instruction
                # Otherwise, add it to the conversation history
                if i == len(messages) - 1 or (
                    i == len(messages) - 2 and isinstance(messages[-1], AIMessage) and not messages[-1].content
                ):
                    instruction = message.content
                else:
                    history.append((USER, message.content))
            
            elif isinstance(message, AIMessage):
                # Add to conversation history if it has content
                if message.content:
                    history.append((ASSISTANT, message.content))
        
        # Create and return the GAINTRUST Prompt
        return Prompt(
            context=context.strip(),
            instruction=instruction.strip(),
            constraints=constraints,
            extra_information=extra_information.strip(),
            history=history
        )
    
    @property
    def _llm_type(self) -> str:
        """Return the type of LLM."""
        return f"gaintrust_local_{self.model_name.lower()}"


class CToRustTranspilerChain:
    """
    LangChain implementation for C to Rust transpilation using GAINTRUST's local models.
    """
    
    def __init__(
        self,
        model_name: str = "local-qwen",
        global_constraints: List[str] = None,
        model_kwargs: Dict[str, Any] = None,
        work_dir: str = "./workspace",
        attempt_budget: int = 3
    ):
        """
        Initialize the C to Rust transpiler chain.
        
        Args:
            model_name: Name of the model to use (e.g., "local-qwen", "codellama")
            global_constraints: Optional list of constraints to apply
            model_kwargs: Additional parameters for model initialization
            work_dir: Working directory for transpilation
            attempt_budget: Number of attempts to make for transpilation
        """
        self.global_constraints = global_constraints or []
        self.model_kwargs = model_kwargs or {}
        self.work_dir = work_dir
        self.attempt_budget = attempt_budget
        
        # Create directories
        os.makedirs(f"{self.work_dir}/wspace", exist_ok=True)
        os.makedirs(f"{self.work_dir}/results", exist_ok=True)
        
        # Initialize the model
        if model_name == "local-qwen":
            qwen_model_name = self.model_kwargs.get("model_name", "Qwen/Qwen2.5-0.5B-Instruct")
            self.model = LocalQwen(self.global_constraints, model_name=qwen_model_name)
        elif model_name == "codellama":
            codellama_model_name = self.model_kwargs.get("model_name", "codellama/CodeLlama-13b-hf")
            self.model = CodeLlama(self.global_constraints, model_name=codellama_model_name)
        else:
            # Try to use the factory to create any supported engine
            try:
                self.model = QueryEngineFactory.create_engine(model_name, self.global_constraints)
            except ValueError:
                raise ValueError(f"Unsupported model: {model_name}")
        
        # Create LangChain adapter - pass the model as a query engine
        self.langchain_model = LocalModelLangChainAdapter(query_engine=self.model, model_name=model_name)
        
        # Set up default constraints for C to Rust transpilation
        self.default_constraints = [
            "Make sure it includes all imports, uses safe rust, and compiles.",
            "Use the same function name, same argument and return types.",
            "Don't use raw pointers.",
            "Use box pointer whenever possible. Box pointers are preferable to other alternatives.",
            "Try not to use Traits if possible. I would not like to have Traits in resulting Rust code.",
            "Try not to use custom Generics if possible.",
            "Do not give me main function.",
            "Do not add any explanations or examples comments.",
            "Put the translated rust code in a markdown rust block."
        ]
    
    def _extract_code_from_markdown(self, text: str) -> str:
        """
        Extract code from markdown code blocks.
        
        Args:
            text: Text potentially containing markdown code blocks
            
        Returns:
            Extracted code or the original text if no code blocks found
        """
        # Look for ```rust ... ``` blocks
        import re
        
        # First, check if the text is already clean Rust code (no markdown)
        # If it contains typical Rust keywords and no markdown formatting
        if re.search(r'\b(fn|pub|use|struct|impl|let|mut)\b', text) and not re.search(r'```|<code>|<\/code>', text):
            return text.strip()
            
        # Look for ```rust ... ``` blocks
        rust_code_blocks = re.findall(r'```rust\s*(.*?)\s*```', text, re.DOTALL)
        
        if rust_code_blocks:
            # Return the first rust code block found
            return rust_code_blocks[0].strip()
        
        # If no rust blocks, look for any code blocks
        code_blocks = re.findall(r'```\w*\s*(.*?)\s*```', text, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()
            
        # Look for <code> ... </code> blocks
        code_tags = re.findall(r'<code>\s*(.*?)\s*</code>', text, re.DOTALL)
        if code_tags:
            return code_tags[0].strip()
        
        # Remove any lines that start with bullet points or dashes
        lines = text.split('\n')
        code_lines = []
        skipping_bullet_section = False
        
        for line in lines:
            stripped = line.strip()
            # Skip empty lines, bullet points, and lines that look like instructions
            if stripped.startswith('-') or stripped.startswith('*'):
                skipping_bullet_section = True
                continue
            
            # If we were in a bullet section and hit a non-bullet line with content, we're out of the section
            if skipping_bullet_section and stripped and not stripped.startswith('-') and not stripped.startswith('*'):
                skipping_bullet_section = False
            
            # Skip lines that look like they're part of instructions
            if any(keyword in stripped.lower() for keyword in ["must be", "should be", "the code", "the rust", "your code"]):
                continue
                
            # Add lines that look like actual code
            if stripped and not skipping_bullet_section:
                code_lines.append(line)
        
        # If we have valid code lines, return them
        if code_lines:
            return '\n'.join(code_lines).strip()
            
        # If all else fails, return the original text
        return text.strip()
    
    def transpile_c_to_rust(self, c_code: str, file_name: str = "transpiled") -> Dict[str, Any]:
        """
        Transpile C code to Rust using LangChain.
        
        Args:
            c_code: The C code to transpile
            file_name: Name for the output file (without extension)
            
        Returns:
            A dictionary with the transpilation results
        """
        logging.info(f"Transpiling C code to Rust using LangChain")
        
        # Set up directories
        src_dir = f"{self.work_dir}/wspace"
        res_dir = f"{self.work_dir}/results"
        
        # Create LangChain prompt template
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are an expert C to Rust transpiler. Your task is to convert C code to safe, idiomatic Rust code. Provide ONLY the Rust code without any explanations or constraints. Do not include any bullet points or instructions in your response."),
            ("human", """
            I need you to translate the following C code to Rust:
            
            {code_block}
            
            IMPORTANT: Return ONLY the Rust code itself, with no explanations, comments, or bullet points.
            DO NOT include any text that starts with dashes or bullet points.
            DO NOT include any constraints or requirements in your response.
            DO NOT wrap the code in markdown code blocks.
            
            Just output the raw Rust code directly.
            """)
        ])
        
        # Create the chain
        chain = prompt_template | self.langchain_model | StrOutputParser()
        
        # Make multiple attempts to generate correct Rust code
        min_num_errs = 2**32
        best_answer = None
        
        for attempt in range(1, self.attempt_budget + 1):
            logging.info(f"Transpilation attempt {attempt}/{self.attempt_budget}")
            
            try:
                # Generate Rust code
                rust_code = chain.invoke({"code_block": tag(c_code, "code")})
                
                # Extract code from markdown if present
                rust_code = self._extract_code_from_markdown(rust_code)
                
                # Save to file
                rust_file_path = f"{src_dir}/{file_name}.rs"
                with open(rust_file_path, "w") as f:
                    f.write(rust_code)
                
                # Compile and check for errors
                compile_dir = f"{self.work_dir}/compile_{file_name}"
                os.makedirs(compile_dir, exist_ok=True)
                
                # Create the src directory if it doesn't exist
                os.makedirs(f"{compile_dir}/src", exist_ok=True)
                
                # Copy the Rust file to the compilation directory
                with open(f"{compile_dir}/src/lib.rs", "w", encoding="utf-8") as f:
                    f.write(rust_code)
                
                # Call compile_and_record_query with the proper directory
                compile_result = compile_and_record_query(rust_code, compile_dir)
                
                # Parse errors - CompletedProcess object has stdout and stderr attributes
                num_errs = 0
                error_output = ""
                if compile_result and hasattr(compile_result, 'stderr'):
                    error_output = compile_result.stderr.decode('utf-8', errors='ignore')
                    num_errs = error_output.count("error")
                
                # Check if this is the best result so far
                if num_errs < min_num_errs:
                    min_num_errs = num_errs
                    best_answer = {
                        "success": num_errs == 0,
                        "num_errors": num_errs,
                        "rust_code": rust_code,
                        "output_path": rust_file_path,
                        "error_output": error_output if num_errs > 0 else ""
                    }
                
                # If no errors, we're done
                if num_errs == 0:
                    logging.info(f"Transpilation successful on attempt {attempt}")
                    break
                
                logging.info(f"Transpilation attempt {attempt} had {num_errs} errors")
                
            except Exception as e:
                logging.error(f"Error in transpilation attempt {attempt}: {str(e)}")
        
        # Return the best result or a failure message
        if best_answer:
            return best_answer
        else:
            # Even if all attempts failed, try to return the last generated Rust code
            return {
                "success": False,
                "num_errors": 0,
                "rust_code": rust_code if 'rust_code' in locals() else "",
                "error": "Failed to generate valid Rust code after multiple attempts"
            }


class CToRustTranspilerWithFeedback(CToRustTranspilerChain):
    """
    Enhanced C to Rust transpiler with feedback loop for improved results.
    """
    
    def __init__(
        self,
        model_name: str = "local-qwen",
        global_constraints: List[str] = None,
        model_kwargs: Dict[str, Any] = None,
        work_dir: str = "./workspace",
        attempt_budget: int = 3,
        feedback_loops: int = 2
    ):
        """
        Initialize the transpiler with feedback.
        
        Args:
            model_name: Name of the model to use
            global_constraints: Optional list of constraints to apply
            model_kwargs: Additional parameters for model initialization
            work_dir: Working directory for transpilation
            attempt_budget: Number of attempts to make for transpilation
            feedback_loops: Number of feedback loops to perform
        """
        super().__init__(model_name, global_constraints, model_kwargs, work_dir, attempt_budget)
        self.feedback_loops = feedback_loops
    
    def _extract_code_from_markdown(self, text: str) -> str:
        """
        Extract code from markdown code blocks.
        
        Args:
            text: Text potentially containing markdown code blocks
            
        Returns:
            Extracted code or the original text if no code blocks found
        """
        if "```rust" in text:
            return text.split("```rust")[1].split("```")[0].strip()
        elif "```" in text:
            return text.split("```")[1].split("```")[0].strip()
        return text

    def transpile_with_feedback(self, c_code: str, file_name: str = "transpiled") -> Dict[str, Any]:
        """
        Transpile C code to Rust with feedback loop for improved results.
        
        Args:
            c_code: The C code to transpile
            file_name: Name for the output file (without extension)
            
        Returns:
            A dictionary with the transpilation results
        """
        # First, do the basic transpilation
        result = self.transpile_c_to_rust(c_code, file_name)
        
        # If successful or no rust code was generated, return the result
        if result["success"] or "rust_code" not in result:
            return result
        
        # Set up directories
        src_dir = f"{self.work_dir}/wspace"
        res_dir = f"{self.work_dir}/results"
        
        # Get the initial Rust code and error output
        rust_code = result["rust_code"]
        error_output = result.get("error_output", "")
        
        # Run feedback loops
        for i in range(self.feedback_loops):
            logging.info(f"Running feedback loop {i+1}/{self.feedback_loops}")
            
            # Create feedback prompt
            feedback_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert Rust programmer. Your task is to fix compilation errors in Rust code that was translated from C."),
                ("human", """
                I have the following C code:
                
                {code_block}
                
                It was translated to Rust, but there are compilation errors:
                
                {rust_code}
                
                Here are the compilation errors:
                
                {error_output}
                
                Please fix the Rust code to address all compilation errors. The fixed code should:
                - Compile without errors
                - Maintain the same functionality as the original C code
                - Use safe Rust practices
                - Avoid raw pointers
                - Avoid unnecessary Traits and Generics
                
                Return only the fixed Rust code in a markdown rust block.
                """)
            ])
            
            # Create the feedback chain
            feedback_chain = feedback_prompt | self.langchain_model | StrOutputParser()
            
            try:
                # Generate improved Rust code
                improved_response = feedback_chain.invoke({
                    "code_block": tag(c_code, "code"), 
                    "rust_code": tag(rust_code, "rust"), 
                    "error_output": tag(error_output, "errors")
                })
                
                # Extract code from markdown if present
                improved_rust_code = self._extract_code_from_markdown(improved_response)
                
                # Save to file
                improved_rust_file_path = f"{src_dir}/{file_name}_feedback_{i+1}.rs"
                with open(improved_rust_file_path, "w") as f:
                    f.write(improved_rust_code)
                
                # Compile and check for errors
                compile_dir = f"{self.work_dir}/compile_{file_name}_feedback_{i+1}"
                os.makedirs(compile_dir, exist_ok=True)
                
                # Create the src directory if it doesn't exist
                os.makedirs(f"{compile_dir}/src", exist_ok=True)
                
                # Copy the Rust file to the compilation directory
                with open(f"{compile_dir}/src/lib.rs", "w", encoding="utf-8") as f:
                    f.write(improved_rust_code)
                
                # Call compile_and_record_query with the proper directory
                improved_compile_result = compile_and_record_query(improved_rust_code, compile_dir)
                
                # Parse errors - CompletedProcess object has stdout and stderr attributes
                num_errs = 0
                improved_error_output = ""
                if improved_compile_result and hasattr(improved_compile_result, 'stderr'):
                    improved_error_output = improved_compile_result.stderr.decode('utf-8', errors='ignore')
                    num_errs = improved_error_output.count("error")
                
                logging.info(f"Feedback loop {i+1}: {num_errs} errors")
                
                # Update the result
                result["rust_code"] = improved_rust_code
                result["num_errors"] = num_errs
                result["success"] = num_errs == 0
                result["output_path"] = improved_rust_file_path
                result["error_output"] = improved_error_output
                
                # If no errors, we're done
                if num_errs == 0:
                    logging.info(f"Feedback loop {i+1} successful")
                    
                    # Save the final version
                    final_path = f"{res_dir}/{file_name}_final.rs"
                    with open(final_path, "w") as f:
                        f.write(improved_rust_code)
                    
                    result["output_path"] = final_path
                    break
                
                # Update for next iteration
                rust_code = improved_rust_code
                error_output = improved_error_output
                
            except Exception as e:
                logging.error(f"Error in feedback loop {i+1}: {str(e)}")
        
        return result


def example_usage():
    """Example usage of the C to Rust transpilation with LangChain."""
    print("=== C to Rust Transpilation with LangChain ===\n")
    
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
    
    # Example 1: Basic transpilation
    print("Example 1: Basic C to Rust Transpilation")
    try:
        transpiler = CToRustTranspilerChain(model_name="local-qwen")
        result = transpiler.transpile_c_to_rust(c_code, "linked_list")
        
        print(f"Success: {result['success']}")
        print(f"Number of errors: {result['num_errors']}")
        print(f"Output file: {result['output_path']}")
        print(f"First few lines of Rust code:")
        print("\n".join(result['rust_code'].split("\n")[:10]))
        print()
    except Exception as e:
        print(f"Error in Example 1: {e}\n")
    
    # Example 2: Transpilation with feedback
    print("Example 2: C to Rust Transpilation with Feedback")
    try:
        transpiler = CToRustTranspilerWithFeedback(
            model_name="local-qwen", 
            feedback_loops=2
        )
        result = transpiler.transpile_with_feedback(c_code, "linked_list_with_feedback")
        
        print(f"Success: {result['success']}")
        print(f"Number of errors: {result['num_errors']}")
        print(f"Output file: {result['output_path'] if 'output_path' in result else 'Not available'}")
        print(f"First few lines of Rust code:")
        print("\n".join(result['rust_code'].split("\n")[:10]))
        print()
    except Exception as e:
        print(f"Error in Example 2: {e}\n")


if __name__ == "__main__":
    example_usage()
