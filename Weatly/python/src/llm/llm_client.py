import openai
import json
import yaml

import os
import logging
import requests

from playsound import playsound
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
import logging
import tempfile
import os
import yaml

logging.basicConfig(level=logging.WARN)

class TextToSpeech:
    def __init__(self):
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
        # Use NamedTemporaryFile for cleaner handling
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.mp3', dir=temp_dir, delete=False) as temp_file:
            for chunk in audio_chunks:
                temp_file.write(chunk)
            file_path = temp_file.name
        try:
            playsound(file_path)
        except Exception as e:
            logging.error(f"Error playing audio file: {e}")
        finally:
            try:
                os.remove(file_path)
            except Exception as e:
                logging.error(f"Error deleting audio file: {e}")

# =================== LLM Client ===================
# This class is responsible for interacting with the OpenAI API

class GPTClient:
    def __init__(self, model="gpt-4o-mini"):
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml")
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        self.api_key = config["secrets"]["openai_api_key"]
        self.model = model
        self.tts_enabled = config["tts"]["enabled"]
        openai.api_key = self.api_key

    def get_text(self, conversation):
        completion = openai.responses.create(
            model=self.model,
            input=conversation,
        )
        if not getattr(completion, "output", None):
            raise Exception("No response from GPT")
        first_msg = completion.output[0]
        if hasattr(first_msg, "content"):
            text = "".join(getattr(item, "text", "") for item in first_msg.content)
        elif hasattr(first_msg, "text"):
            text = first_msg.text
        else:
            raise Exception("No text found in the response message")
        return text

    def reply_with_animation(self, conversation):
        completion = openai.responses.create(
            model=self.model,
            input=conversation,
            tools=set_animation_tool,
            tool_choice={"name": "set_animation", "type": "function"}
        )
        choice = completion.output[0]
        animation = ""
        try:
            args = json.loads(choice.arguments)
            animation = args.get("animation", "")
        except Exception:
            if hasattr(choice.arguments, "function_call") and choice.arguments.function_call:
                func_call = choice.arguments.function_call
                try:
                    args = json.loads(func_call.arguments)
                    animation = args.get("animation", "")
                except Exception:
                    animation = ""
        return animation
        
    def get_workflow(self, conversation):
        completion = openai.responses.create(
            model=self.model,
            input=conversation,
            tools=tools,
            parallel_tool_calls=True
        )
        choice = completion.output
        results = []
        for msg in choice:
            if msg.type == "function_call":
                results.append({
                    "arguments": json.loads(msg.arguments),
                    "name": msg.name,
                    "call_id": msg.call_id
                })
        return results if results else None


set_animation_tool = [
    {
        "type": "function",
        "name": "set_animation",
        "description": "Inform hardware of which animation to use in the reply",
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

tools = [{
    "type": "function",
    "name": "get_weather",
    "description": "Get current temperature for provided coordinates in celsius.",
    "parameters": {
        "type": "object",
        "properties": {
            "latitude": {"type": "number"},
            "longitude": {"type": "number"}
        },
        "required": ["latitude", "longitude"],
        "additionalProperties": False
    },
    "strict": True
},
{
    "type": "function",
    "name": "test_function",
    "description": "Test function to check if the function calling works.",
    "parameters": {
        "type": "object",
        "properties": {
            "test": {"type": "string"}
            },
            "required": ["test"],
            "additionalProperties": False
        }
    }
]

tts_engine = TextToSpeech()


class Functions:
    def __init__(self):
        self.test = GPTClient()
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml")
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        self.tts_enabled = config["tts"]["enabled"]

    def execute_workflow(self, workflow):
        results = []
        for item in workflow:
            print(f"Executing function: {item.get('name')} with arguments: {item.get('arguments')}")
            if self.tts_enabled:
                conversation = [
                    {"role": "system", "content": "Act as Weatly from portal 2. in 10 words summarize the function call as if you are doing what it says. always say numbers out in full. try to enterpet things yourself, so long and lat should be city names. try tobe funny but also short."},
                    {"role": "user", "content": f"Executing function: {item.get('name')} with arguments: {item.get('arguments')}"}
                ]
                text = self.test.get_text(conversation)
                print(f"Text: {text}")
                tts_engine.generate_and_play_advanced(text)

            if item.get("name") == "get_weather":
                get_weather_args = item.get("arguments")
                latitude = get_weather_args.get("latitude")
                longitude = get_weather_args.get("longitude")
                response = self.get_weather(latitude, longitude)
                results.append(response)
            elif item.get("name") == "test_function":
                test_args = item.get("arguments")
                test = test_args.get("test")
                response = f"Test function executed with argument: {test}"
                results.append(response)
            else:
                logging.info("No function to execute")
        return results

    def get_weather(self, latitude, longitude):
        response = requests.get(
            f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
        )
        data = response.json()
        reply_text = f"Weather in {latitude}, {longitude} is {data['current_weather']['temperature']} degrees celsius."
        return reply_text


if __name__ == "__main__":
    test = GPTClient()
    conversation = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the weather like in both New York, and also in stavanger?"}
    ]
    response = test.get_workflow(conversation)
    logging.info(f"Workflow Response: {response}")
    functions_instance = Functions()
    exec_response = functions_instance.execute_workflow(workflow=response)
    logging.info(f"Executed workflow: {exec_response}")