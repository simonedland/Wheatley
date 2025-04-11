import os
from playsound import playsound
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from datetime import datetime
import logging  # Added import

class TextToSpeechEngine:
    def __init__(self):
        import yaml
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml")
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        # Get TTS parameters from config
        tts_config = config.get("tts", {})
        self.api_key = config["secrets"]["elevenlabs_api_key"]
        self.voice_id = tts_config.get("voice_id", "4Jtuv4wBvd95o1hzNloV")
        self.voice_settings = VoiceSettings(
            stability=tts_config.get("stability", 0.3),
            similarity_boost=tts_config.get("similarity_boost", 0.1),
            style=tts_config.get("style", 0.0),
            use_speaker_boost=tts_config.get("use_speaker_boost", True)
        )
        self.model_id = tts_config.get("model_id", "eleven_flash_v2_5")
        self.output_format = tts_config.get("output_format", "mp3_22050_32")
        # Disable verbose logging from elevenlabs to remove INFO prints
        logging.getLogger("elevenlabs").setLevel(logging.WARNING)
        self.client = ElevenLabs(api_key=self.api_key)
    
    def elevenlabs_generate_audio(self, text):
        # Generates audio using ElevenLabs TTS with configured parameters
        return self.client.text_to_speech.convert(
            text=text,
            voice_id=self.voice_id,
            voice_settings=self.voice_settings,
            model_id=self.model_id,
            output_format=self.output_format
        )
    
    def generate_and_play_advanced(self, text):
        # Determine the temp directory (project root "temp" folder)
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        audio_chunks = list(self.elevenlabs_generate_audio(text))
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        save_file_path = f"OUT_{timestamp}.mp3"
        total_relativ_path = os.path.join(temp_dir, save_file_path)
        with open(total_relativ_path, 'wb') as temp_file:
            for chunk in audio_chunks:
                temp_file.write(chunk)
            file_path = temp_file.name
        try:
            playsound(file_path)
        except Exception as e:
            print(f"Error playing audio file: {e}")
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Error deleting audio file: {e}")

if __name__ == "__main__":
    tts_engine = TextToSpeechEngine()
    tts_engine.generate_and_play_advanced("Hello, world! This is a test of the ElevenLabs TTS functionality.")