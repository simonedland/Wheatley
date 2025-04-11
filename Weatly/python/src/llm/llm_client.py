class GPTClient:
    def __init__(self, api_key, model="gpt-4o-mini"):
        import openai
        self.api_key = api_key
        self.model = model
        openai.api_key = self.api_key

    def get_text(self, conversation):
        import openai
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