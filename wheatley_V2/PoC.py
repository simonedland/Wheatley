# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os
import asyncio
import os
from pathlib import Path
from typing import Any, Dict
from random import randint
from typing import Annotated
import yaml

from agent_framework.openai import OpenAIAssistantsClient
from pydantic import Field

"""
OpenAI Assistants Basic Example

This sample demonstrates basic usage of OpenAIAssistantsClient with automatic
assistant lifecycle management, showing streaming responses.
"""

CONFIG_PATH = Path(__file__).parent / "config" / "config.yaml"

def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    """Load config/config.yaml with safe defaults."""
    cfg: Dict[str, Any] = {"llm": {"model": "gpt-4o"}, "secrets": {"openai_api_key": ""}}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
            if isinstance(loaded, dict):
                cfg = {**cfg, **loaded}

    key_env = cfg["secrets"].get("openai_api_key")
    model_env = cfg["llm"].get("model")

    cfg["secrets"]["openai_api_key"] = key_env
    cfg["llm"]["model"] = model_env
    return cfg

config = load_config()
os.environ["OPENAI_API_KEY"] = config["secrets"]["openai_api_key"]
os.environ["OPENAI_RESPONSES_MODEL_ID"] = config["llm"]["model"]
os.environ["OPENAI_CHAT_MODEL_ID"] = config["llm"]["model"]

def get_weather(
    location: Annotated[str, Field(description="The location to get the weather for.")],
) -> str:
    """Get the weather for a given location."""
    conditions = ["sunny", "cloudy", "rainy", "stormy"]
    return f"The weather in {location} is {conditions[randint(0, 3)]} with a high of {randint(10, 30)}°C."


async def streaming_example() -> None:
    """Example of streaming response (get results as they are generated)."""
    print("=== Streaming Response Example ===")

    # Since no assistant ID is provided, the assistant will be automatically created
    # and deleted after getting a response
    async with OpenAIAssistantsClient().create_agent(
        instructions="You are a helpful weather agent.",
        tools=get_weather,
        store=True,
    ) as agent:
        query = "What's the weather like in Portland?"
        print(f"User: {query}")
        print("Agent: ", end="", flush=True)
        async for chunk in agent.run_stream(query):
            if chunk.text:
                print(chunk.text, end="", flush=True)
        print("\n")


async def main() -> None:
    print("=== Basic OpenAI Assistants Chat Client Agent Example ===")

    await streaming_example()


if __name__ == "__main__":
    asyncio.run(main())