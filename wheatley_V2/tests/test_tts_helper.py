import asyncio
import importlib
import sys
import types

import pytest  # type: ignore[import-not-found]


def _import_tts(monkeypatch):
    """Import tts_helper with stubbed pydub modules to avoid external deps."""
    pydub_module = types.ModuleType("pydub")

    class DummyAudioSegment:
        @staticmethod
        def from_file(*args, **kwargs):
            return b"audio"

    playback_module = types.ModuleType("pydub.playback")

    def dummy_play(segment):
        return None

    pydub_module.AudioSegment = DummyAudioSegment
    playback_module.play = dummy_play
    pydub_module.playback = playback_module

    monkeypatch.setitem(sys.modules, "pydub", pydub_module)
    monkeypatch.setitem(sys.modules, "pydub.playback", playback_module)

    sys.modules.pop("wheatley_V2.helper.tts_helper", None)
    return importlib.import_module("wheatley_V2.helper.tts_helper")


def test_process_text_splits_sentences_respects_abbreviations(monkeypatch):
    async def _run():
        tts_helper = _import_tts(monkeypatch)
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

    asyncio.run(_run())


def test_flush_pending_pushes_buffered_text(monkeypatch):
    async def _run():
        tts_helper = _import_tts(monkeypatch)
        handler = tts_helper.TTSHandler("key")

        handler.text_buffer = "Trailing text"
        await handler.flush_pending()
        first = await handler.text_queue.get()
        assert first[1] == "Trailing text"

        handler.buffered_item = (5, "Buffered sentence")
        await handler.flush_pending()
        second = await handler.text_queue.get()
        assert second[0] == 5
        assert second[1] == "Buffered sentence"

    asyncio.run(_run())
