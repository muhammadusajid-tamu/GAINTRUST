"""
LangChain Integration Module for GAINTRUST

This module provides integration between GAINTRUST's existing LLM infrastructure
and LangChain's ecosystem, allowing you to leverage LangChain's components
while maintaining compatibility with your current codebase.
"""

import os
from typing import List, Dict, Any, Union, Optional, Callable
import json

# LangChain Core imports
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableSerializable
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.callbacks import CallbackManager

# LangChain specific model integrations
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.llms import HuggingFacePipeline

# LangChain tools and agents
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import BaseTool, StructuredTool, tool

# Vector stores and embeddings
from langchain_community.vectorstores import FAISS, Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

# Memory components
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory

# Import GAINTRUST components
from llms import QueryEngine, Prompt, USER, ASSISTANT
from llms import Claude2, Claude3, GPT4, Mistral, CodeLlama, LocalQwen


class GaintrustLangChainModel(BaseChatModel):
    """
    Adapter class that wraps GAINTRUST QueryEngine classes to be compatible with LangChain.
    This allows using your existing LLM infrastructure with LangChain components.
    """
    
    def __init__(
        self, 
        query_engine: QueryEngine,
        model_name: str = None
    ):
        """
        Initialize the LangChain adapter for GAINTRUST models.
        
        Args:
            query_engine: An instance of a GAINTRUST QueryEngine
            model_name: Optional name to identify this model
        """
        super().__init__()
        self.query_engine = query_engine
        self.model_name = model_name or type(query_engine).__name__
    
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """
        Generate a response using the GAINTRUST QueryEngine.
        This method is required by LangChain's BaseChatModel.
        """
        # Convert LangChain messages to GAINTRUST Prompt format
        prompt = self._convert_messages_to_prompt(messages)
        
        # Add any additional model parameters from kwargs
        model_params = {"temperature": 0.2}  # Default
        if "temperature" in kwargs:
            model_params["temperature"] = kwargs["temperature"]
        
        # Query the model using GAINTRUST's QueryEngine
        response = self.query_engine.query(prompt, model_params)
        
        # Format the response for LangChain
        message = AIMessage(content=response)
        return {"generations": [[message]]}
    
    def _convert_messages_to_prompt(self, messages) -> Prompt:
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
        for message in messages:
            if isinstance(message, SystemMessage):
                # Extract constraints if they're in a list format
                content = message.content
                if "Constraints:" in content:
                    parts = content.split("Constraints:")
                    context += parts[0]
                    constraints_text = parts[1].strip()
                    # Try to parse constraints as numbered list
                    for line in constraints_text.split("\n"):
                        line = line.strip()
                        if line and (line[0].isdigit() or line.startswith("- ")):
                            # Remove numbering or bullet points
                            constraint = line.split(".", 1)[-1].strip() if "." in line else line[2:].strip()
                            constraints.append(constraint)
                    
                else:
                    context += content
            
            elif isinstance(message, HumanMessage):
                # If this is the last human message, treat it as the instruction
                # Otherwise, add it to the conversation history
                if message == messages[-1] or (
                    message == messages[-2] and isinstance(messages[-1], AIMessage) and not messages[-1].content
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
        return f"gaintrust_{self.model_name.lower()}"


class LangChainFactory:
    """
    Factory class for creating LangChain components that work with GAINTRUST.
    """
    
    @staticmethod
    def create_langchain_model(
        model_name: str, 
        global_constraints: List[str] = None,
        use_native: bool = False,
        **kwargs
    ) -> BaseChatModel:
        """
        Create a LangChain-compatible model using either native LangChain models
        or by wrapping GAINTRUST QueryEngine instances.
        
        Args:
            model_name: Name of the model to use (e.g., "gpt-4", "claude-3", "mistral")
            global_constraints: Optional list of constraints to apply
            use_native: If True, use native LangChain model implementations when available
            **kwargs: Additional parameters to pass to the model constructor
            
        Returns:
            A LangChain-compatible model
        """
        global_constraints = global_constraints or []
        
        # If using native LangChain implementations where available
        if use_native:
            if "gpt" in model_name.lower():
                return ChatOpenAI(model_name=model_name, **kwargs)
            elif "claude" in model_name.lower():
                return ChatAnthropic(model_name=model_name, **kwargs)
        
        # Otherwise, use GAINTRUST models wrapped for LangChain
        if "gpt-4" in model_name.lower():
            engine = GPT4(global_constraints)
            return GaintrustLangChainModel(engine, model_name="GPT4")
        elif "claude-3" in model_name.lower():
            engine = Claude3(global_constraints)
            return GaintrustLangChainModel(engine, model_name="Claude3")
        elif "claude-2" in model_name.lower():
            engine = Claude2(global_constraints)
            return GaintrustLangChainModel(engine, model_name="Claude2")
        elif "mistral" in model_name.lower():
            engine = Mistral(global_constraints)
            return GaintrustLangChainModel(engine, model_name="Mistral")
        elif "codellama" in model_name.lower():
            engine = CodeLlama(global_constraints)
            return GaintrustLangChainModel(engine, model_name="CodeLlama")
        elif "qwen" in model_name.lower():
            engine = LocalQwen(global_constraints)
            return GaintrustLangChainModel(engine, model_name="Qwen")
        else:
            raise ValueError(f"Unsupported model: {model_name}")
    
    @staticmethod
    def create_chain(
        model: Union[str, BaseChatModel],
        system_prompt: str = None,
        global_constraints: List[str] = None,
        memory: bool = False,
        output_parser: Any = None,
        **kwargs
    ) -> RunnableSerializable:
        """
        Create a LangChain chain with the specified components.
        
        Args:
            model: Either a model name string or a LangChain model instance
            system_prompt: Optional system prompt to use
            global_constraints: Optional list of constraints to apply
            memory: Whether to include conversation memory
            output_parser: Optional output parser (defaults to StrOutputParser)
            **kwargs: Additional parameters to pass to the model constructor
            
        Returns:
            A LangChain chain that can be invoked
        """
        # Resolve the model
        if isinstance(model, str):
            llm = LangChainFactory.create_langchain_model(
                model, global_constraints=global_constraints, **kwargs
            )
        else:
            llm = model
        
        # Set up the output parser
        if output_parser is None:
            output_parser = StrOutputParser()
        
        # Create the prompt template
        if memory:
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt or "You are a helpful AI assistant."),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}")
            ])
            
            # Set up memory
            memory_instance = ConversationBufferMemory(return_messages=True)
            
            # Create the chain with memory
            chain = RunnablePassthrough.assign(
                history=lambda _: memory_instance.load_memory_variables({})["history"]
            ) | prompt | llm | output_parser
            
            # Add a method to save memory
            def invoke_with_memory(input_text):
                result = chain.invoke({"input": input_text})
                memory_instance.save_context(
                    {"input": input_text}, 
                    {"output": result}
                )
                return result
                
            # Return a callable that handles memory
            return invoke_with_memory
        else:
            # Create a simple chain without memory
            if system_prompt:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("human", "{input}")
                ])
            else:
                prompt = ChatPromptTemplate.from_messages([
                    ("human", "{input}")
                ])
            
            # Create and return the chain
            return {"input": RunnablePassthrough()} | prompt | llm | output_parser
    
    @staticmethod
    def create_agent(
        model: Union[str, BaseChatModel],
        tools: List[BaseTool],
        system_prompt: str = None,
        global_constraints: List[str] = None,
        **kwargs
    ) -> AgentExecutor:
        """
        Create a LangChain agent with the specified tools.
        
        Args:
            model: Either a model name string or a LangChain model instance
            tools: List of LangChain tools for the agent to use
            system_prompt: Optional system prompt to use
            global_constraints: Optional list of constraints to apply
            **kwargs: Additional parameters to pass to the model constructor
            
        Returns:
            A LangChain AgentExecutor
        """
        # Resolve the model
        if isinstance(model, str):
            llm = LangChainFactory.create_langchain_model(
                model, global_constraints=global_constraints, **kwargs
            )
        else:
            llm = model
        
        # Set up the system prompt
        if system_prompt is None:
            system_prompt = """You are a helpful AI assistant. You have access to the following tools:
            
{tools}

Use these tools to best assist the user with their request.
"""
        
        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create the agent
        agent = create_openai_functions_agent(llm, tools, prompt)
        
        # Create and return the agent executor
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
        )


# Example tools that can be used with LangChain agents
@tool
def search_code(query: str) -> str:
    """Search for code in the codebase using the provided query."""
    # This is a placeholder - implement actual code search logic
    return f"Results for code search: {query}"

@tool
def analyze_code(code: str) -> str:
    """Analyze the provided code for potential issues."""
    # This is a placeholder - implement actual code analysis logic
    return f"Analysis of code: No major issues found in the provided code."


def example_usage():
    """Example usage of the LangChain integration with GAINTRUST."""
    print("=== LangChain Integration Examples ===\n")
    
    # Example 1: Simple chain with GPT-4
    print("Example 1: Simple LangChain chain with GPT-4")
    try:
        chain = LangChainFactory.create_chain(
            model="gpt-4",
            system_prompt="You are a helpful AI assistant specialized in Rust programming.",
            temperature=0.7
        )
        response = chain.invoke("What are some best practices for memory management in Rust?")
        print(f"Response: {response[:150]}...\n")
    except Exception as e:
        print(f"Error in Example 1: {e}\n")
    
    # Example 2: Using GAINTRUST's Claude3 with LangChain
    print("Example 2: Using GAINTRUST's Claude3 with LangChain")
    try:
        model = LangChainFactory.create_langchain_model(
            "claude-3",
            global_constraints=["Be concise", "Focus on practical examples"]
        )
        chain = LangChainFactory.create_chain(model=model)
        response = chain.invoke("Explain how ownership works in Rust")
        print(f"Response: {response[:150]}...\n")
    except Exception as e:
        print(f"Error in Example 2: {e}\n")
    
    # Example 3: Creating an agent with tools
    print("Example 3: Creating an agent with tools")
    try:
        tools = [search_code, analyze_code]
        agent = LangChainFactory.create_agent(
            model="gpt-4",
            tools=tools,
            system_prompt="You are a code assistant that helps with programming tasks."
        )
        response = agent.invoke("Can you search for code related to error handling and analyze it?")
        print(f"Agent response: {response['output'][:150]}...\n")
    except Exception as e:
        print(f"Error in Example 3: {e}\n")
    
    # Example 4: Using memory to maintain conversation context
    print("Example 4: Using memory to maintain conversation context")
    try:
        chain_with_memory = LangChainFactory.create_chain(
            model="gpt-4",
            system_prompt="You are a helpful coding assistant.",
            memory=True
        )
        
        # First interaction
        response1 = chain_with_memory("What is a vector database?")
        print(f"First response: {response1[:100]}...\n")
        
        # Second interaction (should remember context)
        response2 = chain_with_memory("How would I use one with LangChain?")
        print(f"Second response (with context): {response2[:100]}...\n")
    except Exception as e:
        print(f"Error in Example 4: {e}\n")


if __name__ == "__main__":
    example_usage()
