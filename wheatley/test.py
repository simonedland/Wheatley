"""Basic unit tests exercising the main assistant modules."""

import unittest
import os
import yaml
import io
import sys

from wheatley import main  # Use main.py functions

from wheatley.assistant.assistant import ConversationManager
from wheatley.llm.llm_client import GPTClient
from wheatley.tts.tts_engine import TextToSpeechEngine
from wheatley.stt.stt_engine import SpeechToTextEngine
from wheatley.hardware.arduino_interface import ArduinoInterface
from wheatley.llm.llm_client import Functions

# NEW: Custom base test case for colored output
class ColorfulTestCase(unittest.TestCase):
    def assertEqual(self, first, second, msg=None):
        super().assertEqual(first, second, msg)
    
    def assertIn(self, member, container, msg=None):
        super().assertIn(member, container, msg)
    
    def assertIsInstance(self, obj, cls, msg=None):

        super().assertIsInstance(obj, cls, msg)

# Test config loading as used in main.py
class TestConfigLoad(ColorfulTestCase):
    def test_load_config(self):
        config = main.load_config()
        self.assertIsNotNone(config, "Config should not be None")
        for key in ["app", "logging", "stt", "tts", "llm", "hardware", "assistant", "secrets"]:
            self.assertIn(key, config, f"Config missing key: {key}")

# Test assistant initialization from main.py
class TestInitializationAssistant(ColorfulTestCase):
    def test_initialize_assistant(self):
        config = main.load_config()
        result = main.initialize_assistant(config)
        self.assertEqual(len(result), 7, "Should return 7 components")
        manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled = result
        self.assertIsInstance(manager, ConversationManager)
        self.assertIsInstance(gpt_client, GPTClient)
        self.assertIsInstance(stt_engine, SpeechToTextEngine)
        self.assertIsInstance(tts_engine, TextToSpeechEngine)
        self.assertIsInstance(arduino_interface, ArduinoInterface)
        self.assertIsInstance(stt_enabled, bool)
        self.assertIsInstance(tts_enabled, bool)

# Test the conversation loop based on main.py usage.
class TestConversationLoop(ColorfulTestCase):
    def test_conversation_loop_exit(self):
        # Initialize components from main.py properly.
        config = main.load_config()
        components = main.initialize_assistant(config)
        manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled = components
        
        # Force stt_enabled to False so that input() is used.
        stt_enabled = False
        
        # Simulate user input "exit" via sys.stdin redirection.
        simulated_input = io.StringIO("exit\n")
        original_stdin = sys.stdin
        sys.stdin = simulated_input

        # Capture output.
        captured_output = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured_output
        
        try:
            main.conversation_loop(manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled)
        except Exception as e:
            self.fail(f"conversation_loop raised an exception: {e}")
        finally:
            sys.stdin = original_stdin
            sys.stdout = original_stdout
        
        output = captured_output.getvalue()
        self.assertIn("User:", output, "Conversation loop should output a user prompt")

# New tests for LLM, TTS, and Conversation Manager functionality

class TestLLMFunctionality(ColorfulTestCase):
    def test_get_text(self):
        from wheatley.llm.llm_client import GPTClient
        client = GPTClient()
        conversation = [{"role": "user", "content": "Greet me"}]
        try:
            result = client.get_text(conversation)
        except Exception as e:
            self.fail(f"get_text() raised an exception: {e}")
        self.assertTrue(isinstance(result, str), "LLM get_text should return a string")
        self.assertTrue(len(result.strip()) > 0, "LLM get_text should return non-empty text")

class TestTTSFunctionality(ColorfulTestCase):
    def test_generate_and_play(self):
        from wheatley.tts.tts_engine import TextToSpeechEngine
        engine = TextToSpeechEngine()
        # Call the function with a sample text; it should create, play, and delete a temporary audio file.
        try:
            engine.generate_and_play_advanced("Test TTS")
        except Exception as e:
            self.fail(f"TTS generate_and_play_advanced raised an exception: {e}")
        # Verify that no temporary file remains in the temp directory
        base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
        if os.path.exists(base_dir):
            temp_files = os.listdir(base_dir)
            self.assertEqual(len(temp_files), 0, "Temporary audio files were not cleaned up")

class TestConversationManagerFunctionality(ColorfulTestCase):
    def test_add_and_get_conversation(self):
        from wheatley.assistant.assistant import ConversationManager
        manager = ConversationManager(max_memory=3)
        initial = manager.get_conversation()
        self.assertTrue(len(initial) >= 1, "Conversation should contain at least the system message")
        manager.add_text_to_conversation("user", "Hello")
        manager.add_text_to_conversation("assistant", "Hi!")
        conv = manager.get_conversation()
        self.assertIn("Hello", conv[-2]["content"], "User message should be in conversation")
        self.assertIn("Hi!", conv[-1]["content"], "Assistant message should be in conversation")

class TestLongTermMemory(ColorfulTestCase):
    def test_memory_read_write(self):
        from wheatley.utils.long_term_memory import overwrite_memory, read_memory, edit_memory
        tmp_file = "temp_memory.json"
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
        overwrite_memory({"foo": "bar"}, path=tmp_file)
        long_text = "x" * 300
        edit_memory(5, {"note": long_text}, path=tmp_file)
        data = read_memory(path=tmp_file)
        self.assertIsInstance(data, list)
        self.assertEqual(data[-1]["note"], long_text[:197] + "...")
        edit_memory(0, {"foo": "baz" * 100}, path=tmp_file)
        data = read_memory(path=tmp_file)
        self.assertEqual(data[0]["foo"], ("baz" * 100)[:197] + "...")
        overwrite_memory({"final": "yes"}, path=tmp_file)
        data = read_memory(path=tmp_file)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["final"], "yes")
        os.remove(tmp_file)

if __name__ == '__main__':
    unittest.main(verbosity=2)
