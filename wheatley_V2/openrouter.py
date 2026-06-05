"""OpenRouter client for Wheatley V2.

A thin, fast wrapper around the OpenAI-compatible OpenRouter API. It exposes
streaming chat completions (with tool-call assembly) and batch audio
transcription, optimised for low time-to-first-token.

OpenRouter is OpenAI-compatible, so chat completions reuse the ``openai`` SDK
pointed at ``https://openrouter.ai/api/v1``. Audio transcription uses a raw
HTTP POST because it is a multimodal endpoint with a base64 JSON body.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Iterator

import httpx
from openai import OpenAI

#: Convenient named model presets routed through OpenRouter.
MODEL_PRESETS: dict[str, str] = {
    "intelligent": "deepseek/deepseek-chat-v3-0324",
    "fast": "google/gemini-2.0-flash-001",
    "llama_groq": "meta-llama/llama-3.3-70b-instruct",
}

#: Default provider routing for speech-to-text (Groq is fastest for Whisper).
DEFAULT_STT_PROVIDER: dict[str, Any] = {"order": ["Groq"]}

#: Base URL for the OpenRouter API.
BASE_URL = "https://openrouter.ai/api/v1"

#: Endpoint for batch audio transcription.
TRANSCRIPTIONS_URL = f"{BASE_URL}/audio/transcriptions"


@dataclass
class ChatChunk:
    """A single streamed chunk of a chat completion.

    Attributes:
        text: The incremental text delta for this chunk. May be an empty
            string when the chunk carries only metadata (e.g. tool calls).
        tool_calls: ``None`` for every chunk except the final one. On the
            final chunk this holds the fully assembled list of tool calls,
            each a dict with keys ``id``, ``name`` and ``arguments`` (the
            latter parsed from the streamed JSON fragments into a dict).
    """

    text: str = ""
    tool_calls: list[dict[str, Any]] | None = None


@dataclass
class _ToolCallAccumulator:
    """Mutable accumulator for an in-progress streamed tool call."""

    id: str = ""
    name: str = ""
    arguments: str = ""


class OpenRouterClient:
    """Streaming chat + batch transcription client backed by OpenRouter."""

    def __init__(
        self,
        api_key: str,
        *,
        referer: str = "",
        title: str = "Wheatley",
    ) -> None:
        """Create the client.

        Args:
            api_key: OpenRouter API key (``sk-or-...``). Used both for the
                OpenAI SDK client and the raw transcription HTTP call.
            referer: Optional value for the ``HTTP-Referer`` header used by
                OpenRouter for app attribution/rankings.
            title: Value for the ``X-Title`` header (defaults to ``Wheatley``).
        """
        self.api_key = api_key

        default_headers: dict[str, str] = {}
        if referer:
            default_headers["HTTP-Referer"] = referer
        if title:
            default_headers["X-Title"] = title

        self.client = OpenAI(
            api_key=api_key,
            base_url=BASE_URL,
            default_headers=default_headers or None,
        )

    def chat_stream(
        self,
        messages: list[dict],
        *,
        model: str,
        tools: list[dict] | None = None,
        max_tokens: int = 2000,
        provider: dict | None = None,
    ) -> Iterator[ChatChunk]:
        """Stream a chat completion, yielding text deltas as they arrive.

        Text deltas are yielded immediately for minimal time-to-first-token.
        Tool-call fragments are accumulated silently and emitted as a single
        final :class:`ChatChunk` once the stream completes.

        Args:
            messages: OpenAI-style chat messages.
            model: Model id (e.g. ``google/gemini-2.0-flash-001``).
            tools: Optional OpenAI-style tool/function definitions.
            max_tokens: Maximum tokens to generate.
            provider: Optional OpenRouter provider routing dict, e.g.
                ``{"order": ["Groq"], "sort": "latency"}``.

        Yields:
            :class:`ChatChunk` objects. Each carries a text delta; the last
            one additionally carries assembled ``tool_calls`` when present.
        """
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
        if provider is not None:
            kwargs["extra_body"] = {"provider": provider}

        # Index-keyed accumulators so concurrent tool calls stay separate.
        accumulators: dict[int, _ToolCallAccumulator] = {}

        stream = self.client.chat.completions.create(**kwargs)
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            text = getattr(delta, "content", None) or ""

            delta_tool_calls = getattr(delta, "tool_calls", None)
            if delta_tool_calls:
                for tc in delta_tool_calls:
                    idx = tc.index if tc.index is not None else 0
                    acc = accumulators.setdefault(idx, _ToolCallAccumulator())
                    if tc.id:
                        acc.id = tc.id
                    func = getattr(tc, "function", None)
                    if func is not None:
                        if getattr(func, "name", None):
                            acc.name = func.name
                        if getattr(func, "arguments", None):
                            acc.arguments += func.arguments

            yield ChatChunk(text=text)

        if accumulators:
            assembled: list[dict[str, Any]] = []
            for idx in sorted(accumulators):
                acc = accumulators[idx]
                try:
                    parsed_args: Any = (
                        json.loads(acc.arguments) if acc.arguments else {}
                    )
                except json.JSONDecodeError:
                    # Preserve the raw fragment if it is not valid JSON.
                    parsed_args = acc.arguments
                assembled.append(
                    {"id": acc.id, "name": acc.name, "arguments": parsed_args}
                )
            yield ChatChunk(text="", tool_calls=assembled)

    def transcribe(
        self,
        audio: bytes,
        *,
        fmt: str = "wav",
        model: str = "openai/whisper-large-v3-turbo",
        language: str | None = "en",
        provider: dict | None = None,
    ) -> str:
        """Transcribe audio bytes to text via OpenRouter.

        Args:
            audio: Raw audio bytes.
            fmt: Audio container/format (e.g. ``wav``, ``mp3``).
            model: Transcription model id.
            language: Optional ISO language hint (``None`` to auto-detect).
            provider: Optional provider routing dict. Defaults to
                :data:`DEFAULT_STT_PROVIDER` (Groq) when not supplied.

        Returns:
            The transcribed text.

        Raises:
            RuntimeError: If the API returns a non-200 status.
        """
        if provider is None:
            provider = DEFAULT_STT_PROVIDER

        encoded = base64.b64encode(audio).decode("ascii")
        # Per OpenRouter STT docs the audio container key is ``input_audio``.
        body: dict[str, Any] = {
            "model": model,
            "input_audio": {"data": encoded, "format": fmt},
            "language": language,
            "provider": provider,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = httpx.post(
            TRANSCRIPTIONS_URL,
            headers=headers,
            json=body,
            timeout=60.0,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Transcription failed ({response.status_code}): {response.text}"
            )

        data = response.json()
        return data["text"]
