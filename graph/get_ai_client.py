import os
from ollama import AsyncClient
from openai import AsyncOpenAI

DEFAULT_MODEL = "deepseek-r1:7b"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


def use_local_model_client():
    model = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
    ollama_client = AsyncClient()
    return model, ollama_client.chat


def use_openai_client():
    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return model, openai_client.chat.completions.create


def get_ai_client():
    use_local_model = os.getenv("USE_LOCAL_MODEL", "False").lower() == "true"
    if use_local_model:
        model, completion_function = use_local_model_client()
        return model, completion_function
    else:
        model, completion_function = use_openai_client()
        return model, completion_function
