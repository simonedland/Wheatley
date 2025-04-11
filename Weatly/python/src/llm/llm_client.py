import openai
import json

class GPTClient:
    def __init__(self, api_key, model="gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        openai.api_key = self.api_key

    def get_text(self, conversation):
        try:
            completion = openai.chat.completions.create(
                model=self.model,
                messages=conversation,
            )
            if not completion.choices:
                raise Exception("No response from GPT")
            return completion.choices[0].message.content
        except Exception as e:
            raise Exception(f"Error during GPT text retrieval: {e}")

    def reply_with_animation(self, conversation):
        openai.api_key = self.api_key
        completion = openai.chat.completions.create(
                    model=self.model,
                    messages=conversation,
                    functions=tools,
                    function_call={"name": "set_animation"}
                )
        #print("Completion:", completion)
        choice = completion.choices[0]
        # Check if the reply includes a function call
        if hasattr(choice.message, "function_call") and choice.message.function_call:
            func_call = choice.message.function_call
            try:
                args = json.loads(func_call.arguments)
            except Exception:
                args = {}
            animation = args.get("animation", "")
            return animation
        else:
            return ""  # Default if no function_call is present

tools = [
    {
        "type": "function",
        "name": "set_animation",
        "description": "Inform hardware of which animation to use in the reply, and include the reply text.",
        "parameters": {
            "type": "object",
            "properties": {
                "animation": {
                    "type": "string",
                    "enum": ["happy", "angry", "sad", "neutral", "excited"]  # allowed animations
                }
            },
            "required": ["animation"],
            "additionalProperties": False
        }
    }
]