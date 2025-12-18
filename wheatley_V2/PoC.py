"""Basic OpenAI Assistants streaming example for weather queries."""

# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os
from pathlib import Path
from typing import Any, Dict
from random import randint
from typing import Annotated
import yaml

from agent_framework.openai import OpenAIAssistantsClient  # type: ignore[import-not-found]
from pydantic import Field  # type: ignore[import-not-found]

from helper.config import load_config

"""
OpenAI Assistants Basic Example

This sample demonstrates basic usage of OpenAIAssistantsClient with automatic
assistant lifecycle management, showing streaming responses.
"""

config = load_config()
openai_key = config["secrets"]["openai_api_key"]
llm_model = config["llm"]["model"]
max_tokens = config["llm"].get("max_tokens", 1000)
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
        max_tokens=max_tokens,
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
