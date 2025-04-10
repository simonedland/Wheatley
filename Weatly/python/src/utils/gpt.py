import openai
from utils.timer import Timer

def get_gpt_text(conversation):
    """
    Calls OpenAI's ChatCompletion API and returns the response along with token usage.
    """
    try:
        with Timer("Total GPT request"):
            completion = openai.chat.completions.create(
                model="o3-mini",
                messages=conversation,
                reasoning_effort="low"
            )
        if not completion.choices:
            return "No response", 0
        tokens_used = completion.usage.total_tokens if hasattr(completion, 'usage') else 0
        return completion.choices[0].message.content, tokens_used
    except Exception as e:
        raise Exception(f"Error during GPT text retrieval: {e}")
