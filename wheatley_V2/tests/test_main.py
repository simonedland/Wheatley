from unittest.mock import MagicMock, patch, AsyncMock
from wheatley_V2 import main


async def test_main_loop():
    # Mock config
    mock_config = {
        "secrets": {"openai_api_key": "fake_key", "elevenlabs_api_key": "fake_xi"},
        "llm": {"model": "gpt-4o"},
        "tts": {"voice_id": "v1", "model_id": "m1", "enabled": True},
    }

    with patch("wheatley_V2.main.load_config", return_value=mock_config):
        with patch("wheatley_V2.main.Tool") as MockTool:
            # Mock Tool context manager
            mock_tool_instance = AsyncMock()
            MockTool.return_value.__aenter__.return_value = mock_tool_instance

            with patch("wheatley_V2.main.ChatAgent") as MockAgent:
                # Mock Agent context manager
                mock_agent_instance = MagicMock()
                MockAgent.return_value.__aenter__.return_value = mock_agent_instance

                # Mock run_stream
                async def mock_stream(*args, **kwargs):
                    yield MagicMock(text="Hello")
                    yield MagicMock(text=" world")

                # run_stream is called without await, so it should return the async generator directly
                mock_agent_instance.run_stream.side_effect = mock_stream

                with patch("wheatley_V2.main.TTSHandler") as MockTTS:
                    mock_tts_instance = MagicMock()
                    MockTTS.return_value = mock_tts_instance
                    mock_tts_instance.flush_pending = AsyncMock()
                    mock_tts_instance.wait_idle = AsyncMock()

                    # Mock input to run once then raise KeyboardInterrupt to exit loop
                    with patch(
                        "asyncio.to_thread", side_effect=["Hi", KeyboardInterrupt]
                    ):
                        try:
                            await main.main()
                        except KeyboardInterrupt:
                            pass
                        except SystemExit:
                            pass

                        # Verify interactions
                        MockTTS.assert_called_once()
                        mock_tts_instance.start.assert_called_once()
                        mock_tts_instance.process_text.assert_any_call("Hello")
                        mock_tts_instance.process_text.assert_any_call(" world")
                        mock_tts_instance.flush_pending.assert_called()
                        mock_tts_instance.wait_idle.assert_called()


async def test_main_no_tts():
    # Mock config with TTS disabled
    mock_config = {
        "secrets": {"openai_api_key": "fake_key", "elevenlabs_api_key": "fake_xi"},
        "llm": {"model": "gpt-4o"},
        "tts": {"voice_id": "v1", "model_id": "m1", "enabled": False},
    }

    with patch("wheatley_V2.main.load_config", return_value=mock_config):
        with patch("wheatley_V2.main.Tool") as MockTool:
            MockTool.return_value.__aenter__.return_value = AsyncMock()

            with patch("wheatley_V2.main.ChatAgent") as MockAgent:
                mock_agent_instance = MagicMock()
                MockAgent.return_value.__aenter__.return_value = mock_agent_instance

                async def mock_stream(*args, **kwargs):
                    yield MagicMock(text="Hello")

                mock_agent_instance.run_stream.side_effect = mock_stream

                with patch("wheatley_V2.main.TTSHandler") as MockTTS:
                    # Mock input
                    with patch(
                        "asyncio.to_thread", side_effect=["Hi", KeyboardInterrupt]
                    ):
                        try:
                            await main.main()
                        except KeyboardInterrupt:
                            pass
                        except SystemExit:
                            pass

                        # Verify TTS not initialized
                        MockTTS.assert_not_called()
