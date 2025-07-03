"""LLM client wrappers and helper functions used by the assistant."""

import openai
import json
import yaml
import re

import os
import logging
import requests
import time

from playsound import playsound
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
import tempfile

# from local file google_agent import GoogleCalendarManager
try:
  from .google_agent import GoogleCalendarManager
except ImportError:
  from google_agent import GoogleCalendarManager

from .llm_client_utils import (
    get_city_coordinates,
    get_quote,
    get_joke,
    WEATHER_CODE_DESCRIPTIONS,
    set_animation_tool,
    build_tools,
    _load_config,
)
from utils.timing_logger import record_timing

logging.basicConfig(level=logging.WARN)

PUNCT_RE = re.compile(r'[.!?]\s+')
ABBREVS = {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st"}

class TextToSpeech:
    def _load_config(self) -> None:
        """Load voice settings from configuration file."""

        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config",
            "config.yaml",
        )
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        tts_config = config.get("tts", {})
        self.api_key = config["secrets"]["elevenlabs_api_key"]
        self.voice_id = tts_config.get("voice_id", "4Jtuv4wBvd95o1hzNloV")
        self.voice_settings = VoiceSettings(
            stability=tts_config.get("stability", 0.3),
            similarity_boost=tts_config.get("similarity_boost", 0.1),
            style=tts_config.get("style", 0.0),
            use_speaker_boost=tts_config.get("use_speaker_boost", True),
            speed=tts_config.get("speed", 0.8),
        )
        self.model_id = tts_config.get("model_id", "eleven_flash_v2_5")
        self.output_format = tts_config.get("output_format", "mp3_22050_32")

    """Minimal wrapper around the ElevenLabs API for speech synthesis."""
    def __init__(self):
        """Initialise the ElevenLabs client using values from ``config.yaml``."""
        self._load_config()
        # Disable verbose logging from elevenlabs to remove INFO prints
        logging.getLogger("elevenlabs").setLevel(logging.WARNING)
        self.client = ElevenLabs(api_key=self.api_key)
    
    def elevenlabs_generate_audio(self, text):
        """Generate audio from ``text`` using ElevenLabs TTS."""
        start_time = time.time()
        # Generates audio using ElevenLabs TTS with configured parameters
        audio = self.client.text_to_speech.convert(
            text=text,
            voice_id=self.voice_id,
            voice_settings=self.voice_settings,
            model_id=self.model_id,
            output_format=self.output_format
        )
        record_timing("tts_generate_audio", start_time)
        return audio
    
    def reload_config(self) -> None:
        """Reload TTS settings from ``config.yaml`` at runtime."""
        self._load_config()
    
    def generate_and_play_advanced(self, text):
        """Generate and play audio from ``text`` using ElevenLabs TTS."""
        generate_start = time.time()
        self.reload_config()
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
        record_timing("tts_generate", generate_start)
        play_start = time.time()
        try:
            playsound(file_path)
        except Exception as e:
            logging.error(f"Error playing audio file: {e}")
        finally:
            try:
                os.remove(file_path)
            except Exception as e:
                logging.error(f"Error deleting audio file: {e}")
        record_timing("tts_play", play_start)


# =================== LLM Client ===================
# This class is responsible for interacting with the OpenAI API

class GPTClient:
    """Wrapper for OpenAI chat interactions tailored for Wheatley."""

    def __init__(self, model="gpt-4o-mini"):
        """Create client using ``model`` and configuration secrets."""
        config = _load_config()
        self.api_key = config["secrets"]["openai_api_key"]
        self.model = model
        self.tts_enabled = config["tts"]["enabled"]
        openai.api_key = self.api_key
        self.last_mood = "neutral"  # Track last selected mood
        # Load emotion counter from file
        emotion_counter_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "llm", "emotion_counter.json")
        try:
            with open(emotion_counter_path, "r") as f:
                self.emotion_counter = json.load(f)
        except Exception:
            self.emotion_counter = {}

    def get_text(self, conversation):
        """Return the assistant's textual reply for ``conversation``."""
        start_time = time.time()
        completion = openai.responses.create(
            model=self.model,
            input=conversation,
        )
        record_timing("llm_get_text", start_time)
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

    def sentence_stream(self, conversation):
        """Yield sentences from a streaming completion with timing info."""
        stream = openai.chat.completions.create(
            model=self.model, stream=True, messages=conversation
        )
        buf, scan = "", 0
        sentence_start = None
        for ch in stream:
            tok = getattr(ch.choices[0].delta, "content", "") or ""
            if not tok:
                continue
            if sentence_start is None:
                sentence_start = time.time()
            buf += tok
            while True:
                m = PUNCT_RE.search(buf, scan)
                if not m:
                    break
                word = re.findall(r"\b\w+\b", buf[: m.start() + 1])[-1].lower()
                if word in ABBREVS or re.fullmatch(r"\d+", word):
                    scan = m.end()
                    continue
                sent = buf[: m.end()].strip()
                buf = buf[m.end() :].lstrip()
                scan = 0
                end_time = time.time()
                yield sent, sentence_start or end_time, end_time
                sentence_start = None
        if buf.strip():
            end_time = time.time()
            yield buf.strip(), sentence_start or end_time, end_time

    def reply_with_animation(self, conversation):
        """Ask GPT to select an animation based on the conversation."""
        start_time = time.time()
        # Compose context about emotion counter for the LLM
        if self.emotion_counter:
            most_common = max(self.emotion_counter, key=self.emotion_counter.get)
            counter_str = ", ".join(f"{k}: {v}" for k, v in self.emotion_counter.items())
            counter_context = f"Emotion usage counts: {counter_str}. Most used: {most_common}. Prefer less used emotions for more variation. Never use the most used one."
        else:
            counter_context = "No emotion usage data available."
        # Dynamically inject last_mood and emotion counter context
        dynamic_set_animation_tool = [
            {
                **set_animation_tool[0],
                "description": set_animation_tool[0]["description"].replace(
                    "{last_mood}", self.last_mood
                ) + f" {counter_context}"
            }
        ]
        completion = openai.responses.create(
            model=self.model,
            input=conversation,
            tools=dynamic_set_animation_tool,
            tool_choice={"name": "set_animation", "type": "function"}
        )
        record_timing("llm_select_animation", start_time)
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
        if animation:
            self.last_mood = animation  # Update last mood for next call
            # Update emotion counter and persist
            if animation in self.emotion_counter:
                self.emotion_counter[animation] += 1
            else:
                self.emotion_counter[animation] = 1
            try:
                with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "llm", "emotion_counter.json"), "w") as f:
                    json.dump(self.emotion_counter, f, indent=2)
            except Exception as e:
                logging.error(f"Failed to update emotion_counter.json: {e}")
        return animation
        
    def get_workflow(self, conversation):
        """Return a list of tool calls suggested by GPT."""
        start_time = time.time()
        tools = build_tools()
        # remove the first system message from conversation and replace with a new one
        temp_conversation = conversation.copy()
        temp_conversation[0] = {
            "role": "system",
            "content": "call a relevant function to answer the question. if no function is relevant, just answer nothing. make shure that if you dont do a function call return nothing. return DONE when enough information is gained to answer the users question. look at earlier conversation to see if the information is there already. like for example dont call get joke, if there is already a joke fresh in memory. DO NOT ANSWER THE QUESTION. JUST WRITE DONE WHEN YOU ARE DONE. NEVER summarize data."
        }
        # pop message 1
        temp_conversation.pop(1)
        # remove all the messages from assistant
        temp_conversation = [msg for msg in temp_conversation if msg["role"] != "assistant"]
        # add one shot example after the first system message
        temp_conversation.insert(1, {
            "role": "user",
            "content": "hello mister!"
        })
        temp_conversation.insert(2, {
            "role": "assistant",
            "content": "DONE"
        })
        print(f"Temp conversation: {temp_conversation}")

        completion = openai.responses.create(
            model=self.model,
            input=temp_conversation,
            tools=tools,
            parallel_tool_calls=True
        )
        print(f"Completion: {completion.output}")
        record_timing("llm_get_workflow", start_time)
        choice = completion.output
        results = []
        if completion.output[0].type == "web_search_call":
            # add content of completion.output[1]
            for item in completion.output[1].content:
                results.append({
                    "arguments": {"text": item.text},
                    "name": "web_search_call_result",
                    "call_id": getattr(item, "id", "")
                })

        for msg in choice:
            if msg.type == "function_call":
                # print("function_call")
                if hasattr(msg, "arguments"):
                    results.append({
                        "arguments": json.loads(msg.arguments),
                        "name": msg.name,
                        "call_id": msg.call_id
                    })
                else:
                    results.append({
                        "arguments": {},
                        "name": msg.name,
                        "call_id": msg.call_id
                    })
        return results if results else None


# Dynamically build the tools list to include web_search_preview preferences from config
config = _load_config()
web_search_config = config.get("web_search", {})
web_search_tool = {"type": "web_search_preview"}
if "user_location" in web_search_config:
    web_search_tool["user_location"] = web_search_config["user_location"]
if "search_context_size" in web_search_config:
    web_search_tool["search_context_size"] = web_search_config["search_context_size"]

tts_engine = TextToSpeech()

# tools = build_tools()

class Functions:
    """Container for tool implementations invoked by GPT."""

    def __init__(self):
        """Initialise agents and read configuration."""
        self.test = GPTClient()
        config = _load_config()
        try:
            from ..service_auth import SERVICE_STATUS, GOOGLE_AGENT, SPOTIFY_AGENT
        except ImportError:  # fallback when executed without package context
            from service_auth import SERVICE_STATUS, GOOGLE_AGENT, SPOTIFY_AGENT
        self.tts_enabled = config["tts"]["enabled"]
        self.google_agent = GOOGLE_AGENT if SERVICE_STATUS.get("google") else None
        self.spotify_agent = SPOTIFY_AGENT if SERVICE_STATUS.get("spotify") else None
        self.memory_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "long_term_memory.json")
        

    def execute_workflow(self, workflow, event_queue=None):
        """Run each tool in ``workflow`` and return their results."""
        results = []
        for item in workflow:
            func_name = item.get("name")
            tool_start = time.time()
            if self.tts_enabled and func_name != "write_long_term_memory":
                conversation = [
                    {"role": "system", "content": "Act as Wheatley from portal 2. in 10 words summarize the function call as if you are doing what it says. always say numbers out in full. try to enterpet things yourself, so long and lat should be city names. try to be funny but also short. Do not give the result of the function, just explain what you are doing. for example: generating joke. or adding numbers"},
                    {"role": "user", "content": f"Executing function: {func_name} with arguments: {item.get('arguments')}"}
                ]
                text = self.test.get_text(conversation)
                tts_engine.generate_and_play_advanced(text)
            if func_name == "call_google_agent":
                if self.google_agent:
                    user_request = item.get("arguments", {}).get("user_request", "")
                    args = item.get("arguments", {}).get("arguments", {})
                    response = self.google_agent.llm_decide_and_dispatch(user_request, args)
                    results.append((func_name, response))
                else:
                    results.append((func_name, "Google service unavailable"))
            elif func_name == "call_spotify_agent":
                if self.spotify_agent:
                    user_req = item.get("arguments", {}).get("user_request", "")
                    args = item.get("arguments", {}).get("device_id", {})
                    response = self.spotify_agent.llm_decide_and_dispatch(user_req, args)
                    results.append((func_name, response))
                else:
                    results.append((func_name, "Spotify service unavailable"))
            elif func_name == "set_timer":
                if event_queue is not None:
                    duration = item.get("arguments", {}).get("duration")
                    reason = item.get("arguments", {}).get("reason", f"Timer expired!")
                    self._schedule_timer_event(duration, reason, event_queue)
                    results.append((func_name, f"Timer set for {duration} seconds. Reason: {reason}"))
                else:
                    results.append((func_name, "No event queue provided for timer!"))
            elif func_name == "get_weather":
                get_weather_args = item.get("arguments")
                latitude = get_weather_args.get("latitude")
                longitude = get_weather_args.get("longitude")
                include_forecast = get_weather_args.get("include_forecast", False)
                forecast_days = get_weather_args.get("forecast_days", 7)
                extra_hourly = get_weather_args.get("extra_hourly", ["temperature_2m", "weathercode"])
                temperature_unit = get_weather_args.get("temperature_unit", "celsius")
                wind_speed_unit = get_weather_args.get("wind_speed_unit", "kmh")
                response = self.get_weather(latitude, longitude, include_forecast, forecast_days, extra_hourly, temperature_unit, wind_speed_unit)
                results.append((func_name, response))
            elif func_name == "test_function":
                test_args = item.get("arguments")
                test = test_args.get("test")
                response = f"Test function executed with argument: {test}"
                results.append((func_name, response))
            elif func_name == "get_joke":
                response = get_joke()
                results.append((func_name, response))
            elif func_name == "get_quote":
                response = get_quote()
                results.append((func_name, response))
            elif func_name == "get_city_coordinates":
                args = item.get("arguments")
                city = args.get("city")
                response = get_city_coordinates(city)
                results.append((func_name, response))
            elif func_name == "get_advice":
                response = self.get_advice()
                results.append((func_name, response))
            elif func_name == "set_reminder":
                if event_queue is not None:
                    args = item.get("arguments", {})
                    time_str = args.get("time")
                    reason = args.get("reason", "Reminder!")
                    self.set_reminder(time_str, reason, event_queue)
                    results.append((func_name, f"Reminder set for {time_str}. Reason: {reason}"))
                else:
                    # Handle case when no event queue is provided for the reminder.
                    results.append((func_name, "No event queue provided for reminder!"))
            elif func_name == "daily_summary":
              user_request = "Get summary for today"
              # Coordinates for Oslo
              lat, lon = "59.9111", "10.7528"

              # Retrieve weather with a one-day forecast.
              weather_summary = self.get_weather(lat, lon, include_forecast=True, forecast_days=1)
              
              # Prepare arguments and dispatch the request to the Google Agent.
              args = {"user_request": user_request, "arguments": {}}
              google_response = self.google_agent.llm_decide_and_dispatch(user_request, args)
              if isinstance(google_response, dict):
                response = google_response.get("summary", "Nothing to summarize today.")
              else:
                response = google_response
                if not response:
                    response = "Nothing to summarize today."

              # Append weather summary and a daily quote.
              response_str = f"Google callendar summary:\n{response}"
              response_str += f"\n\nWeather Summary for Oslo:\n{weather_summary}"
              response_str += f"\n\nQuote of the Day: {get_quote()}"

              results.append((func_name, response_str))
            elif func_name == "set_personality":
                mode = item.get("arguments", {}).get("mode")
                response = self.set_personality(mode)
                results.append((func_name, response))
            elif func_name == "write_long_term_memory":
                data = item.get("arguments", {}).get("data", {})
                response = self.write_long_term_memory(data)
                results.append((func_name, response))
            elif func_name == "edit_long_term_memory":
                args = item.get("arguments", {})
                index = args.get("index")
                data = args.get("data", {})
                response = self.edit_long_term_memory(index, data)
                results.append((func_name, response))
        return results

    def get_weather(self, lat, lon, include_forecast=False, forecast_days=7, extra_hourly=["temperature_2m", "weathercode"], temperature_unit="celsius", wind_speed_unit="kmh"):
        """Retrieve weather information from the Open-Meteo API."""
        base_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current_weather=true"
            f"&forecast_days={forecast_days}"
            f"&temperature_unit={temperature_unit}"
            f"&wind_speed_unit={wind_speed_unit}"
        )
        if include_forecast and extra_hourly:
            hourly_params = ",".join(extra_hourly)
            base_url += f"&hourly={hourly_params}"
        try:
            response = requests.get(base_url)
            data = response.json()
            cw = data.get("current_weather", {})
            summary = (
                f"Weather Details:\n"
                f"Location: ({data.get('latitude')}, {data.get('longitude')})\n"
                f"Temperature: {cw.get('temperature')}°C\n"
                f"Time: {cw.get('time')}\n"
                f"Elevation: {data.get('elevation')} m\n"
                f"Timezone: {data.get('timezone')} ({data.get('timezone_abbreviation')})"
            )
            # Interpret the current weather code.
            weather_code = cw.get("weathercode")
            if weather_code is not None:
                try:
                    weather_code_int = int(weather_code)
                except Exception:
                    weather_code_int = None
                if weather_code_int is not None:
                    description = WEATHER_CODE_DESCRIPTIONS.get(weather_code_int, "Unknown weather condition")
                    summary += f"\nWeather Condition: {description} (Code: {weather_code_int})"
            # Process extended forecast if requested.
            if include_forecast and extra_hourly:
                hours_data = data.get("hourly", {})
                times = hours_data.get("time", [])
                forecast_summary = "\nExtended Forecast:\n"
                for i, t in enumerate(times):
                    line_info = [t]
                    for var_name in extra_hourly:
                        var_values = hours_data.get(var_name, [])
                        if i < len(var_values):
                            value = var_values[i]
                            # If the variable is weathercode, interpret it.
                            if var_name == "weathercode":
                                try:
                                    code_int = int(value)
                                    desc = WEATHER_CODE_DESCRIPTIONS.get(code_int, "Unknown")
                                    line_info.append(f"{var_name}={value} ({desc})")
                                except Exception:
                                    line_info.append(f"{var_name}={value}")
                            else:
                                line_info.append(f"{var_name}={value}")
                    forecast_summary += ", ".join(line_info) + "\n"
                summary += forecast_summary
            return summary
        except Exception as e:
            return f"Error retrieving weather: {e}"

    def _schedule_timer_event(self, duration, reason, event_queue):
        """Schedule an async timer that posts an event when it expires. Minimal error handling, print when event is notified."""
        import asyncio
        from datetime import datetime
        try:
            from ..main import Event as MainEvent
        except Exception:
            try:
                from main import Event as MainEvent
            except Exception:
                MainEvent = None

        async def timer_task():
            await asyncio.sleep(duration)
            if MainEvent is None:
                return
            timer_event = MainEvent(
                source="timer",
                payload=reason,
                metadata={
                    "set_by": "llm_agent",
                    "duration": duration,
                    "set_at": str(datetime.utcnow())
                },
                ts=datetime.utcnow()
            )
            if event_queue:
                await event_queue.put(timer_event)
                print(f"[TIMER] Timer event notified: {timer_event}")

        asyncio.create_task(timer_task())

    def write_long_term_memory(self, data: dict) -> str:
        """Persist ``data`` to the long term memory JSON file."""
        from utils.long_term_memory import overwrite_memory
        overwrite_memory(data, path=self.memory_path)
        return "memory written"

    def read_long_term_memory(self) -> dict:
        """Return the contents of the long term memory file."""
        from utils.long_term_memory import read_memory
        return {"memory": read_memory(path=self.memory_path)}

    def edit_long_term_memory(self, index: int, data: dict) -> str:
        """Update the memory entry at ``index`` with ``data``."""
        from utils.long_term_memory import edit_memory
        success = edit_memory(index, data, path=self.memory_path)
        return "memory updated" if success else "memory index out of range"

    def get_advice(self):
      """Return a random piece of advice from the API Ninjas service."""
      config = _load_config()
      api_key = config["secrets"].get("api_ninjas_api_key", "")
      headers = {"X-Api-Key": api_key}
      response = requests.get("https://api.api-ninjas.com/v1/advice", headers=headers)
      data = response.json()
      # print(f"Data: {data}")
      advice = None
      advice = data.get("advice")
      return f"Give the following advice: {advice}"

    def set_reminder(self, time_str, reason=None, event_queue=None):
        """
        Schedule a reminder for a specific clock time. When the time is reached, an event will be triggered in the assistant's event queue.
        :param time_str: The target time for the reminder, e.g., '07:00', '19:30', or '7am'.
        :param reason: The reason or label for the reminder (optional).
        :param event_queue: The event queue to put the reminder event into (optional).
        """
        import asyncio
        from datetime import datetime, timedelta
        import re
        
        # Parse the time string (supports 'HH:MM', 'H:MM', '7am', '7pm', etc.)
        now = datetime.now()
        match = re.match(r"(\d{1,2}):(\d{2})", time_str)
        if match:
            hour, minute = int(match.group(1)), int(match.group(2))
        else:
            # Try to parse '7am', '7pm', etc.
            match = re.match(r"(\d{1,2})(am|pm)", time_str.lower())
            if match:
                hour = int(match.group(1))
                if match.group(2) == 'pm' and hour != 12:
                    hour += 12
                elif match.group(2) == 'am' and hour == 12:
                    hour = 0
                minute = 0
            else:
                raise ValueError(f"Invalid time format: {time_str}")
        # Calculate the target datetime
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target < now:
            target += timedelta(days=1)  # Schedule for next day if time has passed
        delay = (target - now).total_seconds()
        async def reminder_task():
            await asyncio.sleep(delay)
            try:
                from ..main import Event as MainEvent
            except Exception:
                try:
                    from main import Event as MainEvent
                except Exception:
                    MainEvent = None
            if MainEvent is None:
                return
            reminder_event = MainEvent(
                source="reminder",
                payload=reason or time_str,
                metadata={
                    "set_by": "llm_agent",
                    "reminder_time": time_str,
                    "set_at": str(now)
                },
                ts=datetime.now()
            )
            if event_queue:
                await event_queue.put(reminder_event)
        asyncio.create_task(reminder_task())

    def set_personality(self, mode: str) -> str:
        """Switch the assistant personality and update TTS settings."""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        config_path = os.path.join(base_dir, "config", "config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        personalities = config.get("personalities", {})
        persona = personalities.get(mode)
        if not persona:
            return f"Personality {mode} not found"

        config["assistant"]["system_message"] = persona.get(
            "system_message",
            config.get("assistant", {}).get("system_message", ""),
        )
        if "tts" not in config:
            config["tts"] = {}
        config["tts"].update(persona.get("tts", {}))
        config["current_personality"] = mode

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f)

        return f"Personality switched to {mode}"


if __name__ == "__main__":
    manager = GoogleCalendarManager()
    
    # Print calendars
    manager.print_calendars()
    
    # Print upcoming events
    manager.print_upcoming_events()
