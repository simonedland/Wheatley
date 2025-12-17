"""Basic OpenAI Assistants streaming example for weather queries."""

# Copyright (c) Microsoft. All rights reserved.

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


def _require(cfg: Dict[str, Any], path: list[str]) -> Any:
    """Return nested config value or raise a clear error if missing."""
    cur: Any = cfg
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            joined = "/".join(path)
            raise KeyError(f"Missing required config key: {joined}")
        cur = cur[key]
    return cur


def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    """Load config/config.yaml and require all referenced values."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f)

    if not isinstance(loaded, dict):
        raise ValueError("Config file must contain a YAML mapping")

    _require(loaded, ["secrets", "openai_api_key"])
    _require(loaded, ["llm", "model"])

    return loaded


config = load_config()
openai_key = _require(config, ["secrets", "openai_api_key"])
llm_model = _require(config, ["llm", "model"])
os.environ["OPENAI_API_KEY"] = openai_key
os.environ["OPENAI_RESPONSES_MODEL_ID"] = llm_model
os.environ["OPENAI_CHAT_MODEL_ID"] = llm_model


def get_weather(
    location: Annotated[str, Field(description="The location to get the weather for.")],
) -> str:
    """Get the weather for a given location."""
    conditions = ["sunny", "cloudy", "rainy", "stormy"]
    return f"The weather in {location} is {conditions[randint(0, 3)]} with a high of {randint(10, 30)}°C."


async def streaming_example() -> None:
    """Stream responses as they are generated."""
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
    """Run the streaming example."""
    print("=== Basic OpenAI Assistants Chat Client Agent Example ===")

    await streaming_example()


if __name__ == "__main__":
    asyncio.run(main())
