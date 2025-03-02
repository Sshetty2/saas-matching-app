import os
from ollama import AsyncClient
from openai import AsyncOpenAI
from pydantic import BaseModel
from graph.workflow_state import SoftwareInfoPydantic
import json
from config import settings

local_model = settings.llm.local_model
openai_model = settings.llm.openai_model
use_local_model = settings.execution.use_local_model
openai_api_key = settings.llm.openai_api_key.get_secret_value()


def use_local_model_client(
    validation_model: BaseModel, system_prompt: str, user_prompt: str
):
    ollama_client = AsyncClient()

    model_args = {
        "model": local_model,
        "prompt": f"{system_prompt}\n\n{user_prompt}",
        "format": validation_model.model_json_schema(),
        "stream": False,
    }
    return ollama_client.generate, model_args


def use_openai_client(system_prompt: str, user_prompt: str):
    openai_client = AsyncOpenAI(api_key=openai_api_key)
    model_args = {
        "model": openai_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }
    return openai_client.chat.completions.create, model_args


def parse_response_function_local(response: str, validation_model: BaseModel):
    analysis_result = validation_model.model_validate_json(response.response)
    result = analysis_result.model_dump()
    return result


def parse_response_function_openai(response: str, _: BaseModel):
    result_text = response.choices[0].message.content.strip()
    try:
        result = json.loads(result_text)
        return result
    except json.JSONDecodeError:
        import re

        json_match = re.search(r"({.*})", result_text.replace("\n", ""), re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(1))
            return result
        else:
            raise ValueError(
                f"Could not parse JSON from model response for alias: {software_alias}"
            )


def get_ai_client(validation_model: BaseModel, system_prompt: str, user_prompt: str):
    if use_local_model:
        completion_function, model_args = use_local_model_client(
            validation_model, system_prompt, user_prompt
        )
        return completion_function, model_args, parse_response_function_local
    else:
        completion_function, model_args = use_openai_client(system_prompt, user_prompt)
        return completion_function, model_args, parse_response_function_openai
