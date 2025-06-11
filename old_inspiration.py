import pyaudio
import yaml
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment
import io

with open("C:/GIT/Wheatly/Wheatley/Wheatly/python/src/config/config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

api_key = config["secrets"]["elevenlabs_api_key"]
elevenlabs = ElevenLabs(api_key=api_key)

audio_stream = elevenlabs.text_to_speech.convert_as_stream(
    text="This is a test. 1. 2. 3. Testing, testing, 1, 2, 3. lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    voice_id="JBFqnCBsd6RMkjVDRZzb",
    model_id="eleven_multilingual_v2"
)

SAMPLE_RATE = 22050
CHANNELS = 1
FORMAT = pyaudio.paInt16

p = pyaudio.PyAudio()
stream = p.open(format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE, frames_per_buffer=1024, output=True)

mp3_buffer = bytearray()
BUFFER_SIZE = 30

for idx, chunk in enumerate(audio_stream):
    if isinstance(chunk, bytes):
        mp3_buffer.extend(chunk)
        if (idx + 1) % BUFFER_SIZE == 0:
            audio = AudioSegment.from_file(io.BytesIO(mp3_buffer), format="mp3")
            pcm_data = audio.set_frame_rate(SAMPLE_RATE).set_channels(CHANNELS).set_sample_width(2).raw_data
            stream.write(pcm_data)
            mp3_buffer = bytearray()

if mp3_buffer:
    audio = AudioSegment.from_file(io.BytesIO(mp3_buffer), format="mp3")
    pcm_data = audio.set_frame_rate(SAMPLE_RATE).set_channels(CHANNELS).set_sample_width(2).raw_data
    stream.write(pcm_data)

stream.stop_stream()
stream.close()
p.terminate()