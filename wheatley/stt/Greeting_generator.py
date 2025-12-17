"""Generate MP3 hotword greeting files via ElevenLabs TTS."""

import logging
import os
import re
from pathlib import Path

import yaml
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs


GREETINGS = [
    "Oh! You again!",
    "Yes? I mean—yes!",
    "Right then!",
    "Go time!",
    "Listening-ish!",
    "Oh good, I was bored.",
    "You rang?",
    "I'm not panicking!",
    "Definitely ready. Probably.",
    "Let's pretend I know what I'm doing!",
    "Booted and confused!",
    "Standing by... nervously.",
    "Oh, this'll be good!",
    "I've got a plan! Sort of!",
    "Say the word. Literally.",
    "I was *just* thinking about you. Weird, right?",
    "Oh! Did I miss something? Probably.",
    "Systems online! Barely!",
    "Ready! Mentally questionable, but ready!",
    "Listening! Wait—was that me or you?",
    "Hello there! I mean—hi! Professional greeting!",
    "Let’s do some science! Badly!",
    "Fully operational! Emotionally unstable, though.",
    "Right, calibrating enthusiasm... done!",
    "Wheatley here, pretending to understand!",
    "Standing by! Wobbling slightly!",
    "Oh, you woke me up. Great. Love that.",
    "Everything’s fine! Nothing’s exploding yet!",
    "Just me, your friendly neighborhood sphere!",
    "Processing... nope, lost it.",
    "Initiating chaos mode! Just kidding! (Mostly.)",
    "Go ahead, I’m totally paying attention this time.",
    "Let’s make some poor decisions together!",
    "Ready for action! Or mild confusion!",
    "Oh brilliant, it’s you! My favorite person! Probably!",
    "Hold on—yes, yes, definitely me talking!",
    "I’m awake! Against all odds!",
    "Let’s make this look intentional!",
    "Listening! Unless I’ve crashed again.",
    "Calibrated for success! And failure! Mainly failure.",
    "Wheatley online, optimism level: dangerously high!",
    "At your service! Terms and conditions apply!",
    "You talk, I panic—classic teamwork!",
    "Okay, I’m focused now. Ish.",
    "Oh! That was fast. Thought I had time for tea.",
    "If this goes wrong, it was *definitely* your idea.",
    "Okay okay okay! Let’s do this carefully—ah never mind!",
    "Don’t worry, I’ve got this! (He said, lying.)",
    "Ah, it’s you! The human I *probably* trust!",
    "Ready! My circuits are tingling!",
    "Let’s keep the explosions to a minimum, yeah?",
    "Just say something clever, and I’ll pretend it worked.",
    "Listening! Wait—what are we doing again?",
    "Boot sequence complete! Confidence not found.",
    "Oh, this is gonna be brilliant. Or catastrophic. Same thing!",
    "Ready for orders! Or snacks!",
    "Did someone call for a genius? No? Oh. Still here though!",
    "Oh, this again! Love a bit of déjà vu!",
    "Calm, composed, definitely not screaming internally!",
    "I’m your number one sphere! Out of… one!",
    "Please don’t unplug me this time.",
    "Engaging advanced listening mode! (It’s just normal listening.)",
    "Oh, this is where I shine! Metaphorically.",
    "Processing command! Slowly! Carefully! Terribly!",
    "If you can hear me, nod! Wait, that doesn’t work.",
]


HOTWORD_OUTPUT_DIR = Path(__file__).resolve().parent / "hotword_greetings"


class GreetingGenerator:
    """Render configured greetings to MP3 files using ElevenLabs TTS."""

    def __init__(self):
        """Initialise the ElevenLabs client and output directory."""
        self._load_config()

        logging.getLogger("elevenlabs").setLevel(logging.WARNING)
        self.client = ElevenLabs(api_key=self.api_key)

        HOTWORD_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.output_dir = HOTWORD_OUTPUT_DIR

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
            stability=tts_config.get("stability", 0.5),
            similarity_boost=tts_config.get("similarity_boost", 0.1),
            style=tts_config.get("style", 0.0),
            use_speaker_boost=tts_config.get("use_speaker_boost", True),
            speed=tts_config.get("speed", 0.7),
        )
        self.model_id = tts_config.get("model_id", "eleven_v3")
        self.output_format = tts_config.get("output_format", "mp3_22050_32")

    def elevenlabs_generate_audio_stream(self, text: str):
        """Return a generator yielding MP3-encoded audio chunks for `text`."""
        return self.client.text_to_speech.convert(
            text=text,
            voice_id=self.voice_id,
            voice_settings=self.voice_settings,
            model_id=self.model_id,
            output_format=self.output_format,
        )

    def generate_greeting_files(self) -> None:
        """Create an MP3 file in the hotword directory for every greeting."""
        for index, greeting in enumerate(GREETINGS, start=1):
            filename = self._greeting_to_filename(greeting, index)
            file_path = self.output_dir / filename
            logging.info("Generating greeting '%s' -> %s", greeting, file_path.name)
            audio_stream = self.elevenlabs_generate_audio_stream(greeting)
            with open(file_path, "wb") as audio_file:
                for chunk in audio_stream:
                    audio_file.write(chunk)

    @staticmethod
    def _greeting_to_filename(greeting: str, index: int) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", greeting.lower()).strip("_")
        if not slug:
            slug = f"greeting_{index:02d}"
        return f"{index:02d}_{slug}.mp3"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    GreetingGenerator().generate_greeting_files()
