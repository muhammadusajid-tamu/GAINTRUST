"""
LangChain integration example for GAINTRUST project.
This file demonstrates how to use LangChain with your existing LLM setup.
"""

import os
from typing import List, Dict, Any, Union

# LangChain imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import HumanMessage, AIMessage

# For OpenAI integration
from langchain_openai import ChatOpenAI

# For Anthropic integration
from langchain_anthropic import ChatAnthropic

# For document handling and embeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

# Import your existing LLM classes
from llms import QueryEngine, Prompt, Claude2, Claude3, GPT4, Mistral

class LangChainAdapter:
    """
    Adapter class to integrate LangChain with existing GAINTRUST LLM infrastructure.
    """
    def __init__(self, model_name: str, global_constraints: List[str] = None):
        """
        Initialize the LangChain adapter.
        
        Args:
            model_name: Name of the model to use (e.g., "gpt-4", "claude-3", etc.)
            global_constraints: List of constraints to apply to all queries
        """
        self.model_name = model_name
        self.global_constraints = global_constraints or []
        self.langchain_model = self._initialize_langchain_model()
        
    def _initialize_langchain_model(self):
        """Initialize the appropriate LangChain model based on model_name."""
        if "gpt" in self.model_name.lower():
            return ChatOpenAI(model_name=self.model_name)
        elif "claude" in self.model_name.lower():
            return ChatAnthropic(model_name=self.model_name)
        else:
            raise ValueError(f"Unsupported model: {self.model_name}")
    
    def create_chain(self, system_prompt: str = None):
        """
        Create a simple LangChain chain with the specified system prompt.
        
        Args:
            system_prompt: Optional system prompt to use
            
        Returns:
            A LangChain chain that can be invoked
        """
        # Create a prompt template
        if system_prompt:
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}")
            ])
        else:
            prompt = ChatPromptTemplate.from_messages([
                ("human", "{input}")
            ])
        
        # Create a simple chain: prompt -> model -> output parser
        chain = (
            {"input": RunnablePassthrough()}
            | prompt
            | self.langchain_model
            | StrOutputParser()
        )
        
        return chain
    
    def query(self, prompt_text: str, system_prompt: str = None) -> str:
        """
        Query the model using LangChain.
        
        Args:
            prompt_text: The prompt to send to the model
            system_prompt: Optional system prompt
            
        Returns:
            The model's response as a string
        """
        chain = self.create_chain(system_prompt)
        return chain.invoke(prompt_text)
    
    def adapt_gaintrust_prompt(self, prompt: Prompt) -> Dict[str, Any]:
        """
        Adapt a GAINTRUST Prompt object to a format suitable for LangChain.
        
        Args:
            prompt: A GAINTRUST Prompt object
            
        Returns:
            A dictionary with the adapted prompt
        """
        # Convert constraints to a string
        constraints_str = "\n".join([f"{i+1}. {constraint}" 
                                    for i, constraint in enumerate(self.global_constraints + prompt.constraints)])
        
        # Build the system message
        system_content = f"{prompt.context}\n\n"
        if constraints_str:
            system_content += f"Constraints:\n{constraints_str}\n\n"
        if prompt.extra_information:
            system_content += f"{prompt.extra_information}\n\n"
            
        # Convert history to LangChain message format
        messages = []
        if system_content.strip():
            messages.append(("system", system_content))
            
        for role, content in prompt.history:
            if role == "USER":
                messages.append(("human", content))
            elif role == "ASSISTANT":
                messages.append(("ai", content))
                
        # Add the current instruction
        if prompt.instruction:
            messages.append(("human", prompt.instruction))
            
        return {"messages": messages}


def example_usage():
    """Example usage of the LangChainAdapter."""
    # Example 1: Simple query
    adapter = LangChainAdapter(model_name="gpt-3.5-turbo")
    response = adapter.query("What is LangChain?")
    print(f"Simple query response:\n{response}\n")
    
    # Example 2: Using a system prompt
    system_prompt = "You are a helpful AI assistant specialized in explaining programming concepts."
    response = adapter.query("Explain what a vector database is.", system_prompt=system_prompt)
    print(f"Query with system prompt response:\n{response}\n")
    
    # Example 3: Adapting a GAINTRUST Prompt
    gaintrust_prompt = Prompt(
        context="You are analyzing Rust code for potential bugs.",
        instruction="Identify potential memory safety issues in the following code snippet.",
        constraints=["Be specific about the line numbers.", "Suggest fixes for each issue."],
        extra_information="The code is part of a larger system that handles file I/O.",
    )
    
    # Add some history
    gaintrust_prompt.history = [
        ("USER", "Can you analyze this code for bugs?"),
        ("ASSISTANT", "I'd be happy to analyze your code. Please share it.")
    ]
    
    # Create a custom chain using the adapted prompt
    adapter = LangChainAdapter(model_name="gpt-4", global_constraints=["Focus on memory safety issues."])
    adapted_prompt = adapter.adapt_gaintrust_prompt(gaintrust_prompt)
    
    # Print the adapted prompt (for demonstration)
    print("Adapted GAINTRUST prompt for LangChain:")
    for role, content in adapted_prompt["messages"]:
        print(f"{role}: {content[:50]}...")
    print()


if __name__ == "__main__":
    example_usage()
