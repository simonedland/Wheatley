import os
import wave
import numpy as np
import pyaudio
import openai
import yaml
import struct
import pvporcupine
import time
import asyncio
import websockets
import json
import base64
import threading
from queue import Queue
import sys
import requests
import tempfile
from threading import Thread, Event
import io

# Fix for websockets+asyncio on Windows
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class SpeechToTextEngine:
    def __init__(self):
        # Load STT settings from the config file
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml")
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        stt_config = config.get("stt", {})
        self.CHUNK = stt_config.get("chunk", 1024)
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = stt_config.get("channels", 1)
        self.RATE = stt_config.get("rate", 16000)  # 16kHz is optimal for Whisper
        self.THRESHOLD = stt_config.get("threshold", 1000)
        self.SILENCE_LIMIT = stt_config.get("silence_limit", 3)
        self._audio = None
        self._stream = None
        self._porcupine = None
        self._websocket = None
        self._audio_queue = Queue()
        self._transcription_callback = None
        self._is_streaming = False
        self._recording_buffer = []
        self._last_transcription_time = 0
        self._transcription_interval = 2.0  # Process every 2 seconds
        self._stop_event = Event()
        self._pause_event = Event()
        self._listening = False
        
        # Set OpenAI API key from config
        openai_api_key = config.get("secrets", {}).get("openai_api_key")
        if not openai_api_key:
            openai_api_key = config.get("openai_api_key")
        if openai_api_key:
            openai.api_key = openai_api_key
            self.api_key = openai_api_key
        else:
            raise ValueError("OpenAI API key not found in config")

    def dry_run(self, filename):
        # Recognize speech using Whisper model deployed in Azure (dry run)
        return "Dry run: recognized text from Whisper model on Azure (simulated)"

    # ------------------------------------------------------------------
    # Listening control helpers
    # ------------------------------------------------------------------
    def pause_listening(self):
        """Pause any ongoing listening/transcription."""
        if not self._pause_event.is_set():
            self._pause_event.set()
            self._stop_event.set()
            self._is_streaming = False  # Stop the audio stream
            if self._listening:  # If the system is currently listening, update the state
                self._listening = False
                print("[STT] Not listening")
            print("[STT] Listening paused.")

    def resume_listening(self):
        """Resume listening after being paused."""
        if self._pause_event.is_set():
            self._pause_event.clear()
            print("[STT] Listening resumed.")

    def is_paused(self):
        return self._pause_event.is_set()


    async def connect_realtime_api(self, transcription_callback=None):
        """
        Connect to OpenAI Realtime API for live transcription using conversation mode
        """
        self._transcription_callback = transcription_callback
        
        # Debug: Print websockets version
        print(f"[DEBUG] websockets version: {getattr(websockets, '__version__', 'unknown')}")
        
        # WebSocket URL for Realtime API
        url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
        
        # Headers for websockets 15.x compatibility
        additional_headers = [
            ("Authorization", f"Bearer {self.api_key}"),
            ("OpenAI-Beta", "realtime=v1")
        ]
        
        try:
            self._websocket = await websockets.connect(url, additional_headers=additional_headers)
            
            # Send session configuration - using correct Realtime API parameters
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": "You are a transcription assistant. Please only transcribe what the user says without adding any responses or commentary. Just provide the exact transcription of their speech.",
                    "voice": "alloy",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 1000
                    },
                    "tools": [],
                    "tool_choice": "auto",
                    "temperature": 0.1,  # Lower temperature for more accurate transcription
                    "max_response_output_tokens": 1
                }
            }
            
            await self._websocket.send(json.dumps(session_config))
            print("Connected to OpenAI Realtime API")
            return True
            
        except Exception as e:
            print(f"Failed to connect to Realtime API: {e}")
            return False

    async def handle_websocket_messages(self):
        """
        Handle incoming messages from the WebSocket
        """
        try:
            async for message in self._websocket:
                data = json.loads(message)
                event_type = data.get("type")
                
                # Handle different event types
                if event_type == "session.created":
                    print("Session created successfully")
                    
                elif event_type == "session.updated":
                    print("Session updated successfully")
                    
                elif event_type == "input_audio_buffer.speech_started":
                    print("Speech detected...")
                    
                elif event_type == "input_audio_buffer.speech_stopped":
                    print("Speech ended, processing...")
                    
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    # This is where we get the transcribed text
                    transcript = data.get("transcript", "")
                    if self._transcription_callback and transcript:
                        await self._transcription_callback(transcript, is_final=True)
                        
                elif event_type == "conversation.item.input_audio_transcription.failed":
                    print(f"Transcription failed: {data.get('error', {})}")
                    
                elif event_type == "response.created":
                    # Immediately cancel the response since we only want transcription
                    if self._websocket:
                        cancel_event = {
                            "type": "response.cancel"
                        }
                        await self._websocket.send(json.dumps(cancel_event))
                    
                elif event_type == "error":
                    print(f"WebSocket error: {data}")
                    
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")
        except Exception as e:
            print(f"Error handling WebSocket messages: {e}")

    def start_audio_stream(self):
        """
        Start the audio input stream for live transcription
        """
        self._audio = pyaudio.PyAudio()
        try:
            self._stream = self._audio.open(
                format=self.FORMAT, 
                channels=self.CHANNELS, 
                rate=self.RATE, 
                input=True, 
                frames_per_buffer=self.CHUNK, 
                input_device_index=2,  # Try device 2 first
                stream_callback=self._audio_callback
            )
        except:
            try:
                self._stream = self._audio.open(
                    format=self.FORMAT, 
                    channels=self.CHANNELS, 
                    rate=self.RATE, 
                    input=True, 
                    frames_per_buffer=self.CHUNK, 
                    input_device_index=1,  # Fallback to device 1
                    stream_callback=self._audio_callback
                )
            except:
                # Use default device
                self._stream = self._audio.open(
                    format=self.FORMAT, 
                    channels=self.CHANNELS, 
                    rate=self.RATE, 
                    input=True, 
                    frames_per_buffer=self.CHUNK, 
                    stream_callback=self._audio_callback
                )
        
        self._stream.start_stream()
        self._is_streaming = True
        self._listening = True
        print("[STT] Listening")
        print("Audio stream started for live transcription")

    def calibrate_noise_floor(self, calibration_time=2.0):
        """
        Calibrate the noise floor by sampling ambient noise for a short period.
        Sets a dynamic threshold for speech detection.
        """
        print("Calibrating ambient noise floor...")
        self._audio = pyaudio.PyAudio()
        stream = self._audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        amplitudes = []
        start_time = time.time()
        while time.time() - start_time < calibration_time:
            data = stream.read(self.CHUNK, exception_on_overflow=False)
            data_int = np.frombuffer(data, dtype=np.int16)
            amplitudes.append(np.max(np.abs(data_int)))
        stream.stop_stream()
        stream.close()
        self._audio.terminate()
        self._audio = None
        noise_floor = np.median(amplitudes)
        # Set threshold a bit above the noise floor
        self.THRESHOLD = int(noise_floor * 2.5)
        print(f"[Calibration] Ambient noise floor: {noise_floor:.1f}, threshold set to: {self.THRESHOLD}")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """
        Callback for audio stream - adds audio data to queue and buffer if above noise threshold
        """
        if self._is_streaming and not self._pause_event.is_set():
            # Noise gate: only queue audio if above threshold
            data_int = np.frombuffer(in_data, dtype=np.int16)
            amplitude = np.max(np.abs(data_int))
            if amplitude > self.THRESHOLD:
                self._audio_queue.put(in_data)
                self._recording_buffer.append(in_data)
        return (None, pyaudio.paContinue)

    async def send_audio_data(self):
        """
        Send audio data from queue to WebSocket (for Realtime API)
        """
        while self._is_streaming and self._websocket:
            try:
                # Get audio data from queue (non-blocking)
                if not self._audio_queue.empty():
                    audio_data = self._audio_queue.get_nowait()
                    
                    # Convert to base64 for WebSocket transmission
                    audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                    
                    # Send audio buffer append event
                    audio_event = {
                        "type": "input_audio_buffer.append",
                        "audio": audio_b64
                    }
                    
                    await self._websocket.send(json.dumps(audio_event))
                
                # Small delay to prevent overwhelming the API
                await asyncio.sleep(0.01)
                
            except Exception as e:
                print(f"Error sending audio data: {e}")
                break

    def chunked_transcription_worker(self):
        """
        Worker thread for chunked Whisper transcription
        """
        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                time.sleep(0.1)
                continue
            current_time = time.time()
            
            # Check if it's time to transcribe
            if (current_time - self._last_transcription_time >= self._transcription_interval 
                and len(self._recording_buffer) > 0):
                
                try:
                    # Create a temporary audio file from the buffer
                    audio_data = b''.join(self._recording_buffer)
                    
                    # Clear the buffer for next chunk
                    self._recording_buffer = []
                    self._last_transcription_time = current_time
                    
                    # Skip if audio is too short
                    if len(audio_data) < self.CHUNK * 10:  # At least 10 chunks
                        continue
                    
                    # Create temporary WAV file
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                        wav_file = tmp_file.name
                        
                        # Write WAV file
                        with wave.open(wav_file, 'wb') as wf:
                            wf.setnchannels(self.CHANNELS)
                            wf.setsampwidth(2)  # 16-bit
                            wf.setframerate(self.RATE)
                            wf.writeframes(audio_data)
                    
                    # Transcribe using Whisper
                    with open(wav_file, "rb") as audio_file:
                        transcription_result = openai.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            response_format="text"
                        )
                    
                    # Clean up temporary file
                    os.unlink(wav_file)
                    
                    # Call the callback with the transcription
                    if self._transcription_callback and transcription_result.strip():
                        # Run the async callback in the event loop
                        if asyncio.iscoroutinefunction(self._transcription_callback):
                            # If we're in an async context, we need to schedule this
                            try:
                                loop = asyncio.get_event_loop()
                                loop.create_task(self._transcription_callback(transcription_result, is_final=True))
                            except RuntimeError:
                                # If no event loop is running, just print
                                print(f"[CHUNKED TRANSCRIPTION] {transcription_result}")
                        else:
                            self._transcription_callback(transcription_result, is_final=True)
                    
                except Exception as e:
                    print(f"Error in chunked transcription: {e}")
            
            # Sleep briefly to avoid busy waiting
            time.sleep(0.1)

    async def start_chunked_transcription(self, transcription_callback=None):
        """
        Start chunked transcription using standard Whisper API
        """
        print("Starting chunked live transcription...")
        self._transcription_callback = transcription_callback
        self._stop_event.clear()
        
        # Start audio stream
        self.start_audio_stream()
        
        # Start transcription worker thread
        transcription_thread = Thread(target=self.chunked_transcription_worker)
        transcription_thread.daemon = True
        transcription_thread.start()
        
        try:
            # Keep running until interrupted
            while self._is_streaming:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Chunked transcription interrupted by user")
        finally:
            pass

    async def start_live_transcription(self, transcription_callback=None, model="whisper-1", use_chunked=True):
        """
        Start live transcription session
        """
        if use_chunked:
            # Use chunked transcription with standard Whisper API (more accurate)
            await self.start_chunked_transcription(transcription_callback)
        else:
            # Use Realtime API (less accurate for pure transcription)
            await self.start_realtime_transcription(transcription_callback)

    async def start_realtime_transcription(self, transcription_callback=None):
        """
        Start live transcription using Realtime API
        """
        print("Starting Realtime API transcription...")
        
        # Connect to Realtime API
        if not await self.connect_realtime_api(transcription_callback):
            return False
        
        # Start audio stream
        self.start_audio_stream()
        
        # Create tasks for handling WebSocket messages and sending audio
        message_task = asyncio.create_task(self.handle_websocket_messages())
        audio_task = asyncio.create_task(self.send_audio_data())
        
        try:
            # Run both tasks concurrently
            await asyncio.gather(message_task, audio_task)
        except KeyboardInterrupt:
            print("Live transcription interrupted by user")
        except Exception as e:
            print(f"Error during live transcription: {e}")
        finally:
            await self.stop_live_transcription()
        
        return True

    async def stop_live_transcription(self):
        """
        Stop live transcription and cleanup resources
        """
        print("Stopping live transcription...")
        self._is_streaming = False
        self._stop_event.set()
        if self._listening:
            self._listening = False
            print("[STT] Not listening")

        # Stop audio stream
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        
        if self._audio:
            self._audio.terminate()
            self._audio = None
        
        # Close WebSocket
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
        
        # Clear audio queue and buffer
        while not self._audio_queue.empty():
            self._audio_queue.get_nowait()
        self._recording_buffer.clear()

    # Legacy methods for backward compatibility
    def record_until_silent(self, start_timeout=10):
        """Record audio until silence is detected or timeout occurs."""
        self._audio = pyaudio.PyAudio()
        try:
            self._stream = self._audio.open(format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE, input=True, frames_per_buffer=self.CHUNK, input_device_index=2)
        except:
            try:
                self._stream = self._audio.open(format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE, input=True, frames_per_buffer=self.CHUNK, input_device_index=1)
            except:
                self._stream = self._audio.open(format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE, input=True, frames_per_buffer=self.CHUNK)
        
        frames = []
        silent_frames = 0
        recording = False
        print("Monitoring...")
        start_time = time.time()

        min_amplitude = float('inf')
        max_amplitude = float('-inf')

        while True:
            data = self._stream.read(self.CHUNK, exception_on_overflow=False)
            data_int = np.frombuffer(data, dtype=np.int16)
            amplitude = np.max(np.abs(data_int))
            min_amplitude = min(min_amplitude, amplitude)
            max_amplitude = max(max_amplitude, amplitude)
            if amplitude > self.THRESHOLD:
                if not recording:
                    print("Sound detected, recording...")
                    recording = True
                frames.append(data)
                silent_frames = 0
            else:
                if not recording:
                    if time.time() - start_time > start_timeout:
                        print("No speech detected, stopping...")
                        break
                else:
                    silent_frames += 1
                    frames.append(data)
                    if silent_frames > (self.RATE / self.CHUNK * self.SILENCE_LIMIT):
                        print("Silence detected, stopping...")
                        break

        print(f"Minimum amplitude: {min_amplitude}")
        print(f"Maximum amplitude: {max_amplitude}")

        self._stream.stop_stream()
        self._stream.close()
        self._stream = None
        self._audio.terminate()
        self._audio = None
        wav_filename = "temp_recording.wav"
        wf = wave.open(wav_filename, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        return wav_filename

    def transcribe(self, filename):
        """Transcribe audio file using OpenAI Whisper"""
        with open(filename, "rb") as audio_file:
            transcription_result = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcription_result.text

    def record_and_transcribe(self, start_timeout=10):
        """Record audio and transcribe using traditional Whisper API"""
        wav_file = self.record_until_silent(start_timeout=start_timeout)
        text = self.transcribe(wav_file)
        os.remove(wav_file)
        return text

    def listen_for_hotword(self, access_key=None, keywords=None, sensitivities=None):
        """
        Listens for a predefined hotword using Porcupine.
        Returns the index of the detected keyword, or None if interrupted.
        """
        if access_key is None:
            # Try to load from config
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml")
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            access_key = config.get("stt", {}).get("porcupine_api_key")
        if not access_key:
            print("Porcupine API key not found in config. Hotword detection disabled.")
            return None
        if keywords is None:
            keywords = ["computer", "jarvis"]
        if sensitivities is None:
            sensitivities = [0.5] * len(keywords)
        
        self._porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=keywords,
            sensitivities=sensitivities
        )
        pa = pyaudio.PyAudio()
        self._audio = pa
        stream = pa.open(
            rate=self._porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self._porcupine.frame_length
        )
        self._stream = stream
        print(f"[Hotword] Listening for hotword(s): {keywords}")
        self._listening = True
        print("[STT] Listening")
        try:
            while True:
                if self._pause_event.is_set():
                    break
                pcm = stream.read(self._porcupine.frame_length, exception_on_overflow=False)
                pcm_unpacked = struct.unpack_from("h" * self._porcupine.frame_length, pcm)
                keyword_index = self._porcupine.process(pcm_unpacked)
                if keyword_index >= 0:
                    print(f"[Hotword] Detected: {keywords[keyword_index]}")
                    return keyword_index
                # Status update every 10 seconds
                if time.time() % 10 < 0.03:
                    print("[Hotword] Still listening...")

        except KeyboardInterrupt:
            print("[Hotword] Listener interrupted.")
        finally:
            stream.stop_stream()
            stream.close()
            self._stream = None
            pa.terminate()
            self._audio = None
            self._porcupine.delete()
            self._porcupine = None
            if self._listening:
                self._listening = False
                print("[STT] Not listening")

        return None

    async def get_live_voice_input(self, duration_seconds=30, use_chunked=True, require_hotword=True):
        """
        Waits for hotword (unless ``require_hotword`` is False), then starts
        live transcription for ``duration_seconds``. Returns the final
        transcribed text.
        """
        if require_hotword:
            idx = self.listen_for_hotword()
            if idx is None:
                return ""
        else:
            print(f"[STT] Listening for speech for {duration_seconds} seconds...")
        
        print(f"Starting live transcription for {duration_seconds} seconds...")
        
        # Store transcription results
        transcription_results = []
        
        def transcription_handler(text, is_final):
            if is_final and text.strip():
                transcription_results.append(text.strip())
                print(f"[TRANSCRIBED] {text.strip()}")
        
        # Create async version of the callback
        async def async_transcription_handler(text, is_final):
            transcription_handler(text, is_final)
        
        # Start live transcription
        transcription_task = asyncio.create_task(
            self.start_live_transcription(async_transcription_handler, use_chunked=use_chunked)
        )
        
        # Run for specified duration
        try:
            await asyncio.wait_for(transcription_task, timeout=duration_seconds)
        except asyncio.TimeoutError:
            print(f"\nTranscription timeout after {duration_seconds} seconds")
        except KeyboardInterrupt:
            print("\nTranscription interrupted by user")
        
        # Stop transcription
        await self.stop_live_transcription()
        
        # Return combined results
        return " ".join(transcription_results)

    def get_live_voice_input_blocking(self, duration_seconds=30, use_chunked=True, require_hotword=True, start_timeout=10):
        """Record and transcribe speech until silence or timeout."""

        if require_hotword:
            idx = self.listen_for_hotword()
            if idx is None:
                return ""
        else:
            print("[STT] Listening for speech...")

        return self.record_and_transcribe(start_timeout=start_timeout)

    def get_voice_input(self):
        """
        Waits for hotword, then records and transcribes speech.
        Returns the transcribed text, or empty string if nothing detected.
        """
        idx = self.listen_for_hotword()
        if idx is None:
            return ""
        wav_file = self.record_until_silent()
        if not wav_file:
            print("No audio detected.")
            return ""
        text = self.transcribe(wav_file)
        os.remove(wav_file)
        return text

    def cleanup(self):
        """
        Cleanup any open audio streams, PyAudio instances, and Porcupine resources.
        """
        self._stop_event.set()
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._audio is not None:
            try:
                self._audio.terminate()
            except Exception:
                pass
            self._audio = None
        if self._porcupine is not None:
            try:
                self._porcupine.delete()
            except Exception:
                pass
            self._porcupine = None

# Example usage functions
async def example_chunked_transcription():
    """Example of chunked transcription (recommended for accuracy)"""
    stt_engine = SpeechToTextEngine()
    
    def transcription_callback(text, is_final):
        if is_final and text.strip():
            print(f"[TRANSCRIBED] {text.strip()}")
    
    async def async_callback(text, is_final):
        transcription_callback(text, is_final)
    
    try:
        await stt_engine.start_live_transcription(async_callback, use_chunked=True)
    except KeyboardInterrupt:
        print("\nStopping chunked transcription...")
    finally:
        await stt_engine.stop_live_transcription()
        stt_engine.cleanup()

async def example_realtime_transcription():
    """Example of Realtime API transcription (less accurate)"""
    stt_engine = SpeechToTextEngine()
    
    async def transcription_callback(text, is_final):
        if is_final and text.strip():
            print(f"[REALTIME TRANSCRIBED] {text.strip()}")
    
    try:
        await stt_engine.start_live_transcription(transcription_callback, use_chunked=False)
    except KeyboardInterrupt:
        print("\nStopping realtime transcription...")
    finally:
        await stt_engine.stop_live_transcription()
        stt_engine.cleanup()

async def example_hotword_then_live():
    """Example of hotword detection followed by live transcription"""
    stt_engine = SpeechToTextEngine()
    
    try:
        # Use chunked transcription for better accuracy
        result = await stt_engine.get_live_voice_input(duration_seconds=30, use_chunked=True)
        print(f"Final transcribed text: {result}")
    except Exception as e:
        print(f"Error during live transcription: {e}")
    finally:
        stt_engine.cleanup()

def example_traditional_transcription():
    """Example using traditional record-then-transcribe approach"""
    stt_engine = SpeechToTextEngine()
    try:
        text = stt_engine.get_voice_input()
        print(f"Transcribed text: {text}")
    except Exception as e:
        print(f"Error during transcription: {e}")
    finally:
        stt_engine.cleanup()

if __name__ == "__main__":
    print("Starting Live SpeechToTextEngine test...")
    
    # Choose which example to run:
    # 1. Chunked transcription (recommended for accuracy)
    asyncio.run(example_chunked_transcription())
    
    # 2. Realtime API transcription (less accurate)
    # asyncio.run(example_realtime_transcription())
    
    # 3. Hotword detection + live transcription
    # asyncio.run(example_hotword_then_live())
    
    # 4. Traditional record-then-transcribe
    # example_traditional_transcription()