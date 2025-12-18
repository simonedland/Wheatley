
import inspect
from agent_framework.openai import OpenAIAssistantsClient

print("OpenAIAssistantsClient.create_agent parameters:")
print(inspect.signature(OpenAIAssistantsClient.create_agent))

# I can't easily inspect the return type's run_stream without an instance, 
# but I can assume it's similar or check if I can import the agent class.
