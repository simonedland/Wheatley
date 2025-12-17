import sys
import types
from pathlib import Path

# Ensure wheatley_V2 root is importable so `helper` resolves.
ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _stub_pydub():
    pydub_module = sys.modules.get("pydub", types.ModuleType("pydub"))
    pydub_module.__path__ = []  # mark as package

    class DummyAudioSegment:
        @staticmethod
        def from_file(*args, **kwargs):
            return b"audio"

    playback_module = sys.modules.get(
        "pydub.playback", types.ModuleType("pydub.playback")
    )

    def dummy_play(segment):
        return None

    pydub_module.AudioSegment = getattr(pydub_module, "AudioSegment", DummyAudioSegment)
    playback_module.play = getattr(playback_module, "play", dummy_play)
    pydub_module.playback = playback_module

    sys.modules.setdefault("pydub", pydub_module)
    sys.modules.setdefault("pydub.playback", playback_module)


def _stub_requests():
    requests_module = sys.modules.get("requests", types.ModuleType("requests"))

    class DummyResponse:
        def __init__(self):
            self.text = ""

        def raise_for_status(self):
            return None

        @property
        def content(self):
            return b""

    def dummy_post(*args, **kwargs):
        return DummyResponse()

    requests_module.post = getattr(requests_module, "post", dummy_post)
    requests_module.exceptions = getattr(
        requests_module, "exceptions", types.SimpleNamespace(HTTPError=Exception)
    )

    sys.modules.setdefault("requests", requests_module)


def _stub_agent_framework():
    agent_framework = sys.modules.get(
        "agent_framework", types.ModuleType("agent_framework")
    )
    agent_framework.__path__ = []

    class DummyTool:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummyAgent:
        def __init__(self, *args, **kwargs):
            pass

        def get_new_thread(self):
            return object()

        def run_stream(self, *args, **kwargs):
            async def _gen():
                if False:
                    yield None

            return _gen()

        def run(self, *args, **kwargs):
            class Resp:
                text = ""

            return Resp()

        def create_agent(self, *args, **kwargs):
            return DummyAgent()

    class DummyStore:
        pass

    agent_framework.ChatAgent = getattr(agent_framework, "ChatAgent", DummyAgent)
    agent_framework.ChatMessageStore = getattr(
        agent_framework, "ChatMessageStore", DummyStore
    )
    agent_framework.MCPStreamableHTTPTool = getattr(
        agent_framework, "MCPStreamableHTTPTool", DummyTool
    )

    openai_module = sys.modules.get(
        "agent_framework.openai", types.ModuleType("agent_framework.openai")
    )
    openai_module.__path__ = []

    class DummyResponsesClient:
        def __init__(self, *args, **kwargs):
            pass

        def create_agent(self, *args, **kwargs):
            return DummyAgent()

    class DummyAssistantsClient:
        def __init__(self, *args, **kwargs):
            pass

        def create_agent(self, *args, **kwargs):
            class DummyContext:
                async def __aenter__(self_inner):
                    return DummyAgent()

                async def __aexit__(self_inner, exc_type, exc, tb):
                    return False

            return DummyContext()

    openai_module.OpenAIResponsesClient = getattr(
        openai_module, "OpenAIResponsesClient", DummyResponsesClient
    )
    openai_module.OpenAIAssistantsClient = getattr(
        openai_module, "OpenAIAssistantsClient", DummyAssistantsClient
    )

    sys.modules.setdefault("agent_framework", agent_framework)
    sys.modules.setdefault("agent_framework.openai", openai_module)


def _stub_fastmcp():
    fastmcp_module = sys.modules.get("fastmcp", types.ModuleType("fastmcp"))

    class DummyMCP:
        def __init__(self, *args, **kwargs):
            pass

        def tool(self, *args, **kwargs):
            def decorator(fn):
                return fn

            return decorator

        def http_app(self, *args, **kwargs):
            return object()

    fastmcp_module.FastMCP = getattr(fastmcp_module, "FastMCP", DummyMCP)
    sys.modules.setdefault("fastmcp", fastmcp_module)


def _stub_uvicorn():
    uvicorn_module = sys.modules.get("uvicorn", types.ModuleType("uvicorn"))

    def dummy_run(*args, **kwargs):
        return None

    uvicorn_module.run = getattr(uvicorn_module, "run", dummy_run)
    sys.modules.setdefault("uvicorn", uvicorn_module)


def _stub_yaml():
    """Provide a minimal yaml module using json for CI environments without PyYAML."""
    try:
        import yaml  # noqa: F401

        return
    except ImportError:
        pass

    import json

    yaml_module = sys.modules.get("yaml", types.ModuleType("yaml"))

    def safe_dump(data, *args, **kwargs):
        return json.dumps(data)

    def safe_load(stream, *args, **kwargs):
        if hasattr(stream, "read"):
            stream = stream.read()
        return json.loads(stream) if stream else None

    yaml_module.safe_dump = getattr(yaml_module, "safe_dump", safe_dump)
    yaml_module.safe_load = getattr(yaml_module, "safe_load", safe_load)
    sys.modules.setdefault("yaml", yaml_module)


_stub_pydub()
_stub_requests()
_stub_agent_framework()
_stub_fastmcp()
_stub_uvicorn()
_stub_yaml()
