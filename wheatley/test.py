"""Basic unit tests for main assistant functionalities: LLM and TTS."""

import os
import unittest
from llm.llm_client import GPTClient  # type: ignore[import-not-found]
from tts.tts_engine import TextToSpeechEngine  # type: ignore[import-not-found]


class ColorfulTestCase(unittest.TestCase):
    """Custom base test case for colored output."""

    def assert_equal(self, first, second, msg=None):
        """Assert that two values are equal."""
        super().assertEqual(first, second, msg)

    def assert_in(self, member, container, msg=None):
        """Assert that member is in container."""
        super().assertIn(member, container, msg)

    def assert_is_instance(self, obj, cls, msg=None):
        """Assert that object is instance of class."""
        super().assertIsInstance(obj, cls, msg)


class TestLLMFunctionality(ColorfulTestCase):
    """Test LLM functionality using GPTClient."""

    def test_get_text(self):
        """Test that GPTClient.get_text returns a non-empty string."""
        print("[TestLLMFunctionality] Starting test_get_text...")
        client = GPTClient()
        conversation = [{"role": "user", "content": "Greet me"}]
        try:
            print("[TestLLMFunctionality] Calling client.get_text...")
            result = client.get_text(conversation)
            print(f"[TestLLMFunctionality] Received result: {result}")
        except Exception as e:
            print(f"[TestLLMFunctionality] Exception occurred: {e}")
            self.fail(f"get_text() raised an exception: {e}")
        self.assertTrue(isinstance(result, str), "LLM get_text should return a string")
        self.assertTrue(
            len(result.strip()) > 0, "LLM get_text should return non-empty text"
        )
        print("[TestLLMFunctionality] test_get_text completed successfully.")


class TestTTSFunctionality(ColorfulTestCase):
    """Test TTS functionality using TextToSpeechEngine."""

    def test_generate_and_play(self):
        """Test that generate_and_play_advanced works and cleans up temp files."""
        print("[TestTTSFunctionality] Starting test_generate_and_play...")
        engine = TextToSpeechEngine()
        try:
            print("[TestTTSFunctionality] Calling engine.generate_and_play_advanced...")
            engine.generate_and_play_advanced("Test TTS")
            print("[TestTTSFunctionality] generate_and_play_advanced executed.")
        except Exception as e:
            print(f"[TestTTSFunctionality] Exception occurred: {e}")
            self.fail(f"TTS generate_and_play_advanced raised an exception: {e}")
        base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
        if os.path.exists(base_dir):
            temp_files = os.listdir(base_dir)
            print(f"[TestTTSFunctionality] Temp files after TTS: {temp_files}")
            self.assertEqual(
                len(temp_files), 0, "Temporary audio files were not cleaned up"
            )
        print("[TestTTSFunctionality] test_generate_and_play completed successfully.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
