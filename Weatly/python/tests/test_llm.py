import unittest
from src.llm.llm_client import LLMClient

class TestLLMClient(unittest.TestCase):

    def setUp(self):
        self.client = LLMClient()

    def test_initialization(self):
        self.assertIsNotNone(self.client)

    def test_generate_response(self):
        prompt = "What is the capital of France?"
        response = self.client.generate_response(prompt)
        self.assertIsInstance(response, str)
        self.assertEqual(response, "Paris")  # Assuming the expected response is known

    def test_handle_empty_prompt(self):
        response = self.client.generate_response("")
        self.assertEqual(response, "Prompt cannot be empty.")  # Assuming this is the expected behavior

if __name__ == '__main__':
    unittest.main()