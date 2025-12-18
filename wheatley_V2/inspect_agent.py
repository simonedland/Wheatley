
import inspect
import sys
from agent_framework.openai import OpenAIResponsesClient
from agent_framework import ChatAgent

print("OpenAIResponsesClient.__init__ parameters:")
print(inspect.signature(OpenAIResponsesClient.__init__))

print("\nChatAgent.run_stream parameters:")
print(inspect.signature(ChatAgent.run_stream))
