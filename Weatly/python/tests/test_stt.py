import unittest
from src.stt.stt_engine import STTEngine  # Adjust the import based on your actual implementation

class TestSTTEngine(unittest.TestCase):

    def setUp(self):
        self.stt_engine = STTEngine()

    def test_initialization(self):
        self.assertIsNotNone(self.stt_engine)

    def test_recognize_speech(self):
        # Example test case for recognizing speech
        test_audio_input = "path/to/test/audio.wav"  # Replace with actual test audio path
        expected_output = "Hello, world!"  # Replace with expected output
        result = self.stt_engine.recognize_speech(test_audio_input)
        self.assertEqual(result, expected_output)

    def test_handle_noise(self):
        # Example test case for handling noisy input
        noisy_audio_input = "path/to/noisy/audio.wav"  # Replace with actual noisy test audio path
        result = self.stt_engine.recognize_speech(noisy_audio_input)
        self.assertIsInstance(result, str)  # Ensure it returns a string

if __name__ == '__main__':
    unittest.main()