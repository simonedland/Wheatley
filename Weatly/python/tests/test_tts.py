import unittest
from src.tts.tts_engine import TextToSpeech

class TestTextToSpeech(unittest.TestCase):

    def setUp(self):
        self.tts = TextToSpeech()

    def test_speak(self):
        result = self.tts.speak("Hello, world!")
        self.assertIsNone(result)  # Assuming speak() returns None on success

    def test_speak_empty_string(self):
        result = self.tts.speak("")
        self.assertIsNone(result)  # Assuming speak() handles empty strings gracefully

    def test_speak_invalid_input(self):
        with self.assertRaises(ValueError):
            self.tts.speak(None)  # Assuming speak() raises ValueError for None input

if __name__ == '__main__':
    unittest.main()