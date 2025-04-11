# llm_client.py

import requests

class LLMClient:
    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.api_key = api_key

    def query(self, prompt):
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'prompt': prompt,
            'max_tokens': 200
        }
        response = requests.post(self.api_url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def get_response(self, prompt):
        result = self.query(prompt)
        return result.get('choices', [{}])[0].get('text', '').strip()

class GPTClient:
    def __init__(self, api_key, model="gpt-4o-mini"):
        import openai
        self.api_key = api_key
        self.model = model
        openai.api_key = self.api_key

    def get_text(self, conversation):
        import openai
        from utils.timer import Timer
        try:
            with Timer("Total GPT request"):
                completion = openai.chat.completions.create(
                    model=self.model,
                    messages=conversation,
                )
            if not completion.choices:
                raise Exception("No response from GPT")
            return completion.choices[0].message.content
        except Exception as e:
            raise Exception(f"Error during GPT text retrieval: {e}")