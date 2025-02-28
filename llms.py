import anthropic
import boto3
import botocore
import logging
from abc import abstractmethod
from dataclasses import dataclass, field
import json
import httpx
from openai import OpenAI
import re
from typing import Any, List, Dict, Tuple, Union
import google.generativeai
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from overrides import override
from tenacity import (
    retry,
    wait_random_exponential,
    stop_after_delay,
    retry_if_exception_type,
)
import torch
from utils import tag


USER = "USER"
ASSISTANT = "ASSISTANT"

MAX_TOKEN: int = 8192


@dataclass
class Prompt:
    """
    A structured representation of prompts

    Args:
        history (List[Tuple[str, str]]): A conversation that consists of a list of roles and contents
        preamble (str): A fixed preamble for responses.
    """

    context: str = ""
    instruction: str = ""
    constraints: List[str] = field(default_factory=list)
    extra_information: str = ""

    history: List[Tuple[str, str]] = field(default_factory=list)
    preamble: str = ""

    def __str__(self) -> str:
        constraints_str = ""
        for c_id, constraint in enumerate(self.constraints):
            constraints_str = (
                constraints_str + "\n\t" + str(c_id + 1) + ". " + constraint
            )
        return f"""{self.context}

{self.instruction}

Here are some constraints contained in <list> tags that you should respect:
{tag(constraints_str, "list")}

{self.extra_information}
"""


class QueryError(Exception):
    """
    A wrapper around all sorts of errors thrown by LLMs
    """

    pass


class QueryEngine:
    def __init__(self, global_constraints: List[str]) -> None:
        self.global_constraints = global_constraints

    @abstractmethod
    def raw_query(
        self,
        prompt: Union[str, Prompt],
        model_params: Dict[str, Any],
    ) -> str: ...

    @retry(
        reraise=True,
        retry=retry_if_exception_type(QueryError),
        wait=wait_random_exponential(multiplier=1, max=120),
        stop=stop_after_delay(900),
    )
    def query(
        self,
        prompt: Prompt,
        model_params: Dict[str, Any] = {"temperature": 0.2},
    ) -> str:
        # return self.raw_query(self.stringify_prompt(prompt), model_params)
        return self.raw_query(prompt, model_params)

    def stringify_prompt(self, prompt: Prompt) -> str:
        """
        Override this method to specialise prompt representation to your language model
        """
        messages = self.messages(prompt)
        prompt_str = ""
        for message in messages:
            role = message["role"]
            content = message["content"]
            prompt_str += f"{role}:\n{content}\n"

        return prompt_str

    def generate_code(
        self, prompt: Prompt, model_params: Dict[str, Any] = {"temperature": 0.2}
    ) -> str:
        constrained_prompt = Prompt(
            context=prompt.context,
            instruction=prompt.instruction,
            constraints=prompt.constraints
            + self.global_constraints
            + [
                "Give me code only, no explanation.",
                "Place your code inside a <code></code> tag.",
            ],
            extra_information=prompt.extra_information,
            preamble=prompt.preamble,
            history=prompt.history,
        )
        response = self.query(constrained_prompt, model_params)
        return QueryEngine.extract(response)

    @staticmethod
    def extract(response: str) -> str:
        #print("DEBUG: Query Engine Extracting")
        print("DEBUG: response: " + response)
        tagged_block = re.search(r"<code>(?P<code>[\s\S]*)</code>", response)
        if tagged_block:
           print("Found <> code block")
           print(tagged_block["code"])
           return tagged_block["code"]
        backticked_block = re.search(r"```(rust)?(?P<code>[\s\S]*?)```", response)
        if backticked_block:
            print("Found backtick code block")
            print(backticked_block.group("code"))
            return backticked_block.group("code")

        print("No codeblock found")
        return response

    def messages(
        self,
        prompt: Union[str, Prompt],
    ) -> List[Dict[str, str]]:
        if isinstance(prompt, str):
            messages = [
                {"role": "user", "content": prompt},
            ]
        else:
            messages = []
            for content in prompt.history:
                role, content = content
                if role == USER:
                    messages.append({"role": "user", "content": content})
                elif role == ASSISTANT:
                    messages.append({"role": "assistant", "content": content})
                else:
                    raise ValueError(f"Unidentified role: {role}")

            messages.append({"role": "user", "content": str(prompt)})

            if prompt.preamble:
                messages.append(
                    {"role": "assistant", "content": prompt.preamble.rstrip()}
                )
        return messages


class Claude2(QueryEngine):
    def __init__(self, global_constraints: List[str]) -> None:
        super().__init__(global_constraints)
        config = botocore.config.Config(
            read_timeout=900, connect_timeout=900, retries={"max_attempts": 0}
        )
        session = boto3.Session()
        self.bedrock = session.client("bedrock-runtime", config=config)
        self.modelId = "anthropic.claude-v2:1"

    @override
    def stringify_prompt(self, prompt: Prompt) -> str:
        prompt_str = ""
        for content in prompt.history:
            role, content = content
            if role == USER:
                prompt_str += f"{anthropic.HUMAN_PROMPT}\n{content}"
            elif role == ASSISTANT:
                prompt_str += f"{anthropic.AI_PROMPT}\n{content}"
            else:
                raise ValueError(f"Unidentified role: {role}")

        prompt_str += f"{anthropic.HUMAN_PROMPT}{str(prompt)}{anthropic.AI_PROMPT}\n{prompt.preamble}"

        return prompt_str

    @override
    def raw_query(
        self,
        prompt: Union[str, Prompt],
        model_params: Dict[str, Any],
    ) -> str:
        bedrock = self.bedrock
        if isinstance(prompt, Prompt):
            prompt = self.stringify_prompt(prompt)

        body = json.dumps(
            {
                "prompt": prompt,
                "max_tokens_to_sample": MAX_TOKEN,
                "temperature": model_params["temperature"],
            }
        )

        # modelId = "anthropic.claude-v2:1"  # TODO compare anthropic.claude-v2 and anthropic.claude-v2:1 later
        modelId = self.modelId
        accept = "application/json"
        contentType = "application/json"

        try:
            response = bedrock.invoke_model(
                body=body, modelId=modelId, accept=accept, contentType=contentType
            )
        except Exception as e:
            raise QueryError(e)
        response_body = json.loads(response.get("body").read())
        answer = response_body.get("completion")

        if answer.startswith(" "):
            answer = answer[1:]

        logging.info(
            f"A query to Anthropic Claude2 is made with model paramters as follows: {str(model_params)}"
        )
        return answer


class Claude3(QueryEngine):
    def __init__(self, global_constraints: List[str]) -> None:
        super().__init__(global_constraints)
        config = botocore.config.Config(
            read_timeout=900, connect_timeout=900, retries={"max_attempts": 0}
        )
        self.bedrock = boto3.client(service_name="bedrock-runtime", config=config)
        self.modelId = "anthropic.claude-3-sonnet-20240229-v1:0"

    @override
    def raw_query(
        self, prompt: Union[str, Prompt], model_params: Dict[str, Any]
    ) -> str:
        body = json.dumps(
            {
                "max_tokens": MAX_TOKEN,
                "temperature": model_params["temperature"],
                "messages": self.messages(prompt),
                "anthropic_version": "bedrock-2023-05-31",
            }
        )

        try:
            response = self.bedrock.invoke_model(body=body, modelId=self.modelId)
        except Exception as e:
            raise QueryError(e)
        response_body = json.loads(response.get("body").read())
        response = response_body.get("content")

        logging.info(
            f"A query to Anthropic Claude3 is made with model paramters as follows: {str(model_params)}"
        )
        if not response:
            return ""
        return response[0]["text"]


class Mistral(QueryEngine):
    def __init__(self, global_constraints: List[str]) -> None:
        super().__init__(global_constraints)
        config = botocore.config.Config(
            read_timeout=900, connect_timeout=900, retries={"max_attempts": 0}
        )
        self.bedrock = boto3.client(service_name="bedrock-runtime", config=config)
        self.modelId = "mistral.mixtral-8x7b-instruct-v0:1"

    BOS = "<s>"
    EOS = "</s>"
    INST_START = "[INST] "
    INST_END = " [/INST]"

    @override
    def stringify_prompt(self, prompt: Prompt) -> str:
        """
        https://www.promptingguide.ai/models/mistral-7b
        """

        prompt_str = ""
        for content in prompt.history:
            role, content = content
            if role == USER:
                prompt_str += f"{self.BOS}{self.INST_START}{content}{self.INST_END}"
            elif role == ASSISTANT:
                prompt_str += f" {content}{self.EOS}"
            else:
                raise ValueError(f"Unidentified role: {role}")

        prompt_str += f"{self.INST_START}{str(prompt)}{self.INST_END}"

        # TODO preamble?
        return prompt_str

    @override
    def raw_query(self, prompt: str | Prompt, model_params: Dict[str, Any]) -> str:
        bedrock = self.bedrock
        if isinstance(prompt, Prompt):
            prompt = self.stringify_prompt(prompt)

        body = json.dumps(
            {
                "prompt": prompt,
                "max_tokens": int(MAX_TOKEN / 2),
                "temperature": model_params["temperature"],
            }
        )

        modelId = self.modelId
        accept = "application/json"
        contentType = "application/json"

        try:
            response = bedrock.invoke_model(
                body=body, modelId=modelId, accept=accept, contentType=contentType
            )
        except Exception as e:
            raise QueryError(e)

        response_body = json.loads(response.get("body").read())
        answer = response_body["outputs"][0]["text"]

        logging.info(
            f"A query to Mistral is made with model paramters as follows: {str(model_params)}"
        )
        return answer


class GPT4(QueryEngine):
    def __init__(self, global_constraints: List[str]) -> None:
        super().__init__(global_constraints)
        self.client = OpenAI(timeout=httpx.Timeout(900.0, read=900.0, connect=900.0))
        self.model = "gpt-4-turbo-preview"

    @override
    def raw_query(
        self,
        prompt: Union[str, Prompt],
        model_params: Dict[str, Any],
    ) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=model_params["temperature"],
                messages=self.messages(prompt),
            )
        except Exception as e:
            raise QueryError(e)

        logging.info(
            f"A query to GPT4 is made with model paramters as follows: {str(model_params)}"
        )
        return response.choices[0].message.content

    def __init__(self, global_constraints: List[str]) -> None:
        super().__init__(global_constraints)
        google.generativeai.configure()
        self.model = google.generativeai.GenerativeModel("gemini-pro")

    MAX_TOKEN = 2048

    @override
    def raw_query(self, prompt: str | Prompt, model_params: Dict[str, Any]) -> str:
        generation_config = {
            "temperature": model_params["temperature"],
            "max_output_tokens": self.MAX_TOKEN,
        }

        messages = self.messages(prompt)

        # google.generativeai.count_message_tokens()
        contents = []
        for message in messages:
            match message["role"]:
                case "user":
                    contents.append({"role": "user", "parts": [message["content"]]})
                case "assistant":
                    contents.append({"role": "model", "parts": [message["content"]]})
                case _:
                    raise ValueError("Impossible")

        request_options = {"timeout": 900}

        try:
            response = self.model.generate_content(
                contents,
                generation_config=generation_config,
                request_options=request_options,
            )
        except Exception as e:
            raise QueryError(e)
        response.resolve()
        if len(response.candidates) > 0 and len(response.candidates[0].content.parts) > 0:
            logging.info(
                f"A query to Gemini is made with model paramters as follows: {str(model_params)}"
            )
            return response.candidates[0].content.parts[0].text
        else:
            raise QueryError("Response doesn't contain useful information")

class LocalQwen(QueryEngine):
    def __init__(self, global_constraints: List[str], model_name: str = "Qwen/Qwen2.5-0.5B-Instruct"):
        super().__init__(global_constraints)
        self.model_name = model_name
        self.generator = pipeline("text-generation", model=model_name, device_map="auto")
        print(f"DEBUG: Constructed local model - Qwen")

    def stringify_prompt(self, prompt: Prompt) -> str:
        messages = self.messages(prompt)
        prompt_str = "\n".join(f"{msg['role']}: {msg['content']}" for msg in messages)
        return prompt_str

    def raw_query(self, 
                  prompt: Union[str, Prompt], 
                  model_params: Dict[str, Any]
                  ) -> str:
        
        if isinstance(prompt, Prompt):
            prompt = self.stringify_prompt(prompt)

        logging.info(f"Querying local model '{self.model_name}' with params: {model_params}")

        try:
            output = self.generator(prompt, max_new_tokens=model_params.get("max_length", 2048),
                                    temperature=model_params.get("temperature", 0.2),
                                    do_sample=model_params.get("do_sample", True),
                                    return_full_text=False)
            response = output[0]["generated_text"]
        except Exception as e:
            logging.error(f"Error during model inference: {e}")
            raise QueryError(e)
        #print(response)
        return response
    
class CodeLlama(QueryEngine):
    def __init__(self, global_constraints: List[str], model_name: str = "codellama/CodeLlama-13b-hf"):
        """
        Initialize the codellama local model query engine.
        :param global_constraints: List of global constraints applied to all queries.
        :param model_name: The Hugging Face model to load.
        """
        super().__init__(global_constraints)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.generator = pipeline("text-generation", model=model_name, torch_dtype=torch.float16, device_map="auto")
        self.model_name = model_name

    def stringify_prompt(self, prompt: Prompt) -> str:
        """
        Converts a Prompt object into a plain text format suitable for a local LLM.
        """
        messages = self.messages(prompt)
        prompt_str = "\n".join(f"{msg['role']}: {msg['content']}" for msg in messages)
        return prompt_str

    @retry(
        reraise=True,
        retry=retry_if_exception_type(Exception),
        wait=wait_random_exponential(multiplier=1, max=30),
        stop=stop_after_delay(300),
    )
    def raw_query(self, prompt: Union[str, Prompt], model_params: Dict[str, Any]) -> str:
        """
        Sends a query to the local model and returns the response.
        """
        if isinstance(prompt, Prompt):
            prompt = self.stringify_prompt(prompt)

        logging.info(f"Querying local model '{self.model_name}' with params: {model_params}")

        try:
            output = self.generator(
                prompt,
                do_sample=model_params.get("do_sample", True),
                temperature=model_params.get("temperature", 0.7),
                max_length=model_params.get("max_length", 1024),
                return_full_text=False,
                truncation=True,
            )
            
            response = output[0]['generated_text']

        except Exception as e:
            logging.error(f"Error during model inference: {e}")
            raise QueryError(e)

        return response


class QueryEngineFactory:
    @staticmethod
    def create_engine(model: str, global_constraints: List[str] = []) -> QueryEngine:
        match model:
            case "claude2":
                return Claude2(global_constraints)
            case "claude3":
                return Claude3(global_constraints)
            case "gpt4":
                return GPT4(global_constraints)
            case "mistral":
                return Mistral(global_constraints)
            case "gemini":
                return Gemini(global_constraints)
            case "local-qwen":
                return LocalQwen(global_constraints)
            case "codellama":
                return CodeLlama(global_constraints)
            case _:
                raise ValueError(f"Unknown model: {model}")
