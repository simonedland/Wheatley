import openai
import json
import yaml

import os
import logging
import requests

from playsound import playsound
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
import tempfile

logging.basicConfig(level=logging.WARN)

def _load_config():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    config_path = os.path.join(base_dir, "config", "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

class TextToSpeech:
    def __init__(self):
        config = _load_config()
        base_dir = os.path.dirname(os.path.dirname(__file__))
        # Get TTS parameters from config
        tts_config = config.get("tts", {})
        self.api_key = config["secrets"]["elevenlabs_api_key"]
        self.voice_id = tts_config.get("voice_id", "4Jtuv4wBvd95o1hzNloV")
        self.voice_settings = VoiceSettings(
            stability=tts_config.get("stability", 0.3),
            similarity_boost=tts_config.get("similarity_boost", 0.1),
            style=tts_config.get("style", 0.0),
            use_speaker_boost=tts_config.get("use_speaker_boost", True),
            speed=tts_config.get("speed", 0.8)
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
        base_dir = os.path.dirname(os.path.dirname(__file__))
        temp_dir = os.path.join(base_dir, "temp")
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
        config = _load_config()
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

tools = [
    {
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
    },
    {
        "type": "function",
        "name": "get_joke",
        "description": "Get a random joke.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_quote",
        "description": "Retrieve a random inspirational quote.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_time",
        "description": "Get the current time",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {"type": "string"}
            },
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "reverse_text",
        "description": "Reverse the provided text.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"}
            },
            "required": ["text"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_city_coordinates",
        "description": "Get accurate coordinates for a given city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string"}
            },
            "required": ["city"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_advice",
        "description": "Retrieve a piece of advice.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    }
]

tts_engine = TextToSpeech()


class Functions:
    def __init__(self):
        self.test = GPTClient()
        config = _load_config()
        self.tts_enabled = config["tts"]["enabled"]

    def execute_workflow(self, workflow):
        results = []
        for item in workflow:
            func_name = item.get("name")
            #print(f"Executing function: {func_name} with arguments: {item.get('arguments')}")
            if self.tts_enabled:
                conversation = [
                    {"role": "system", "content": "Act as Weatly from portal 2. in 10 words summarize the function call as if you are doing what it says. always say numbers out in full. try to enterpet things yourself, so long and lat should be city names. try to be funny but also short. Do not give the result of the function, just explain what you are doing. for example: generating joke. or adding numbers"},
                    {"role": "user", "content": f"Executing function: {func_name} with arguments: {item.get('arguments')}"}
                ]
                text = self.test.get_text(conversation)
                #print(f"Text: {text}")
                tts_engine.generate_and_play_advanced(text)

            if func_name == "get_weather":
                get_weather_args = item.get("arguments")
                latitude = get_weather_args.get("latitude")
                longitude = get_weather_args.get("longitude")
                response = self.get_weather(latitude, longitude)
                results.append((func_name, response))
            elif func_name == "test_function":
                test_args = item.get("arguments")
                test = test_args.get("test")
                response = f"Test function executed with argument: {test}"
                results.append((func_name, response))
            elif func_name == "get_joke":
                response = self.get_joke()
                results.append((func_name, response))
            elif func_name == "get_quote":
                response = self.get_quote()
                results.append((func_name, response))
            elif func_name == "get_time":
                args = item.get("arguments")
                timezone = args.get("timezone") if args else "Europe/Oslo"
                response = self.get_time(timezone)
                results.append((func_name, response))
            elif func_name == "reverse_text":
                args = item.get("arguments")
                text_val = args.get("text")
                response = self.reverse_text(text_val)
                results.append((func_name, response))
            elif func_name == "get_city_coordinates":
                args = item.get("arguments")
                city = args.get("city")
                response = self.get_city_coordinates(city)
                results.append((func_name, response))
            elif func_name == "get_advice":
                response = self.get_advice()
                results.append((func_name, response))
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

    def get_joke(self):
        response = requests.get("https://official-joke-api.appspot.com/random_joke")
        data = response.json()
        joke = f"Provide joke: {data.get('setup')} - {data.get('punchline')}"
        return joke

    def get_quote(self):
        config = _load_config()
        api_key = config["secrets"].get("api_ninjas_api_key", "")
        headers = {"X-Api-Key": api_key}
        response = requests.get("https://api.api-ninjas.com/v1/quotes", headers=headers)
        data = response.json()
        if data and isinstance(data, list):
            item = data[0]
            return f"Tell the user: {item.get('quote', '')} — {item.get('author', '')}"
        return "No quote available."

    def get_time(self, timezone):
        from datetime import datetime
        import pytz  # Ensure pytz is installed
        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            return f"Current time in {timezone} is {now.strftime('%Y-%m-%d %H:%M:%S')}."
        except Exception as e:
            return f"Error: {str(e)}"

    def reverse_text(self, text):
        return text[::-1]

    def get_city_coordinates(self, city):
        config = _load_config()
        api_key = config["secrets"].get("api_ninjas_api_key", "")
        headers = {"X-Api-Key": api_key}
        url = f"https://api.api-ninjas.com/v1/city?name={city}"
        response = requests.get(url, headers=headers)
        data = response.json()
        if data and isinstance(data, list) and len(data) > 0:
            item = data[0]
            lat = item.get("latitude")
            lon = item.get("longitude")
            return f"Coordinates for {city}: Latitude {lat}, Longitude {lon}."
        return f"No data available for {city}."

    def get_advice(self):
      config = _load_config()
      api_key = config["secrets"].get("api_ninjas_api_key", "")
      headers = {"X-Api-Key": api_key}
      response = requests.get("https://api.api-ninjas.com/v1/advice", headers=headers)
      data = response.json()
      #print(f"Data: {data}")
      advice = None
      advice = data.get("advice")
      return f"Give the following advice: {advice}"


if __name__ == "__main__":
    test = GPTClient()
    conversation = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the weather like in both New York, and also in stavanger? calculate the sum of 5 and 10. Tell me a joke."},
    ]
    response = test.get_workflow(conversation)
    logging.info(f"Workflow Response: {response}")
    functions_instance = Functions()
    exec_response = functions_instance.execute_workflow(workflow=response)
    logging.info(f"Executed workflow: {exec_response}")