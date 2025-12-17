import asyncio
import sys
import types
import importlib
from unittest.mock import MagicMock, patch
from wheatley_V2.helper import tts_helper

# Ensure we are working with a clean module
importlib.reload(tts_helper)

# Mock pydub if not already mocked
if "pydub" not in sys.modules:
    pydub_module = types.ModuleType("pydub")

    class DummyAudioSegment:
        @staticmethod
        def from_file(*args, **kwargs):
            return MagicMock()

    pydub_module.AudioSegment = DummyAudioSegment  # type: ignore
    sys.modules["pydub"] = pydub_module

if "pydub.playback" not in sys.modules:
    playback_module = types.ModuleType("pydub.playback")
    playback_module.play = MagicMock()  # type: ignore
    sys.modules["pydub.playback"] = playback_module


async def test_api_call_success():
    handler = tts_helper.TTSHandler("fake_key")
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.content = b"audio_data"
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = handler._api_call("Hello world")
        assert result == b"audio_data"
        mock_post.assert_called_once()

        # Check payload
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["text"] == "Hello world"


async def test_api_call_failure():
    handler = tts_helper.TTSHandler("fake_key")
    with patch("requests.post") as mock_post:
        mock_post.side_effect = Exception("API Error")

        # Should catch exception and print error, returning None implicitly
        result = handler._api_call("Hello world")
        assert result is None


async def test_play_success():
    handler = tts_helper.TTSHandler("fake_key")
    with patch("wheatley_V2.helper.tts_helper.play") as mock_play:
        with patch("wheatley_V2.helper.tts_helper.AudioSegment") as MockAudioSegment:
            handler._play(b"audio_data")
            MockAudioSegment.from_file.assert_called_once()
            mock_play.assert_called_once()


async def test_play_failure():
    handler = tts_helper.TTSHandler("fake_key")
    with patch("wheatley_V2.helper.tts_helper.play") as mock_play:
        with patch("wheatley_V2.helper.tts_helper.AudioSegment"):
            mock_play.side_effect = Exception("Playback Error")
            # Should catch exception and print error
            handler._play(b"audio_data")
            mock_play.assert_called_once()


async def test_full_pipeline():
    handler = tts_helper.TTSHandler("fake_key")

    # Mock API call to return dummy audio
    with patch.object(handler, "_api_call", return_value=b"dummy_audio") as mock_api:
        # Mock play to do nothing
        with patch.object(handler, "_play") as mock_play:
            handler.start()

            handler.process_text("Hello world. This is a test.")
            await handler.flush_pending()

            # Signal end of stream
            await handler.text_queue.put(None)

            # Wait for tasks to finish
            await asyncio.gather(*handler.tasks)

            assert mock_api.call_count == 2
            assert mock_play.call_count == 2


async def test_context_aware_pipeline():
    # Enable context aware temporarily
    original_setting = tts_helper.ENABLE_CONTEXT_AWARE_TTS
    tts_helper.ENABLE_CONTEXT_AWARE_TTS = True

    try:
        handler = tts_helper.TTSHandler("fake_key")

        with patch.object(
            handler, "_api_call", return_value=b"dummy_audio"
        ) as mock_api:
            with patch.object(handler, "_play"):
                handler.start()

                handler.process_text("First sentence. Second sentence.")
                await handler.flush_pending()

                # Signal end of stream
                await handler.text_queue.put(None)

                await asyncio.gather(*handler.tasks)

                assert mock_api.call_count == 2
                # Check context in calls
                calls = mock_api.call_args_list
                # First call: text="First sentence.", prev=None, next="Second sentence."
                assert calls[0][0][0] == "First sentence."
                assert calls[0][0][2] == "Second sentence."

                # Second call: text="Second sentence.", prev="First sentence.", next=None
                assert calls[1][0][0] == "Second sentence."
                assert calls[1][0][1] == "First sentence."

    finally:
        tts_helper.ENABLE_CONTEXT_AWARE_TTS = original_setting


async def test_process_text_splits_sentences_respects_abbreviations():
    handler = tts_helper.TTSHandler("key", voice_id="v", model_id="m")

    handler.process_text("Hi there. Mr. Smith arrived. Bye.")
    await handler.flush_pending()

    items = [await handler.text_queue.get() for _ in range(handler.text_queue.qsize())]
    texts = [item[1] for item in items]

    assert texts == [
        "Hi there.",
        "Mr. Smith arrived.",
        "Bye.",
    ]
