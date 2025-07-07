"""
google_agent.py

Google Calendar helpers + LLM-powered agent.
Python ≥ 3.10 • google-api-python-client ≥ 2.116.0 • openai ≥ 1.15.0
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import openai  # pip install --upgrade openai
import yaml
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ────────────────────────────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
TOKEN_FILE = CONFIG_DIR / "token.json"
SECRET_FILE = CONFIG_DIR / "client_secret.json"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

# ────────────────────────────────────────────────────────────────────────────
class GoogleCalendarManager:
    """Thin wrapper around Google Calendar REST v3."""

    @staticmethod
    def _interactive_oauth_flow() -> Credentials:
        """Run the OAuth flow to get credentials interactively."""
        if not SECRET_FILE.exists():
            raise FileNotFoundError(f"OAuth client secret missing: {SECRET_FILE}")
        flow = InstalledAppFlow.from_client_secrets_file(SECRET_FILE, SCOPES)
        # For headless servers use flow.run_console()
        return flow.run_local_server(port=0, prompt="consent")

    @staticmethod
    def _store_token(creds: Credentials) -> None:
        """Store the OAuth token to disk."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(creds.to_json())

    def _get_google_credentials(self) -> Credentials:
        """Get or refresh Google credentials."""
        creds: Credentials | None = None

        # 1 · Load previously saved token
        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        # 2 · Refresh if possible
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("✅ Token refreshed.")
            except (RefreshError, Exception) as err:
                print(f"🔄 Refresh failed ({err}); re-authenticating.")
                creds = None

        # 3 · Fall back to OAuth browser flow
        if creds is None:
            creds = self._interactive_oauth_flow()
            print("✅ Obtained new credentials via OAuth.")

        # 4 · Persist
        self._store_token(creds)
        return creds

    def __init__(self) -> None:
        """Initialize GoogleCalendarManager and load config."""
        self.creds = self._get_google_credentials()
        self.service = build("calendar", "v3", credentials=self.creds, cache_discovery=False)

        with CONFIG_FILE.open() as f:
            cfg = yaml.safe_load(f)
        self.skip_calendars: set[str] = set(cfg.get("skip_calendars", []))

    def list_calendars(self) -> list[dict[str, str]]:
        """List available calendars, skipping those in config."""
        try:
            items = self.service.calendarList().list().execute().get("items", [])
            return [
                {"id": cal["id"], "summary": cal.get("summary", "")}
                for cal in items
                if cal["id"] not in self.skip_calendars
            ]
        except HttpError as e:
            print(f"Failed to fetch calendars: {e}")
            return []

    def get_upcoming_events(self, days: int = 7) -> dict[str, list[dict[str, str]]]:
        """Get upcoming events for all calendars in the next `days` days."""
        now = datetime.utcnow().isoformat() + "Z"
        future = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"
        out: dict[str, list[dict[str, str]]] = {}

        for cal in self.list_calendars():
            try:
                events = (
                    self.service.events()
                    .list(
                        calendarId=cal["id"],
                        timeMin=now,
                        timeMax=future,
                        singleEvents=True,
                        orderBy="startTime",
                    )
                    .execute()
                    .get("items", [])
                )
                if events:
                    out[cal["summary"]] = [
                        {
                            "start": ev.get("start", {}).get("dateTime")
                            or ev.get("start", {}).get("date"),
                            "summary": ev.get("summary", "(no title)"),
                        }
                        for ev in events
                    ]
            except HttpError as e:
                print(f"Failed for {cal['id']}: {e}")
        return out

    def print_calendars(self) -> None:
        """Print all available calendars."""
        for c in self.list_calendars():
            print(f"- {c['summary']}  (ID: {c['id']})")

    def print_upcoming_events(self, days: int = 7) -> None:
        """Print upcoming events for the next `days` days."""
        evs = self.get_upcoming_events(days)
        if not evs:
            print("No upcoming events.")
            return
        print(f"\nUpcoming events (next {days} days):")
        for cal, items in evs.items():
            print(f"\n📅 {cal}")
            for ev in items:
                print(f" • {ev['start']} — {ev['summary']}")

# ────────────────────────────────────────────────────────────────────────────
# OpenAI tool schema – NEW nested "function" structure
GOOGLE_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_google_calendar_events",
            "description": "Get upcoming events from Google Calendar.",
            "parameters": {
                "type": "object",
                "properties": {"days": {"type": "integer"}},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_google_calendar_event",
            "description": "Create a new Google Calendar event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["summary", "start_time", "end_time"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_google_calendar_event",
            "description": "Delete an event from Google Calendar.",
            "parameters": {
                "type": "object",
                "properties": {"event_id": {"type": "string"}},
                "required": ["event_id"],
                "additionalProperties": False,
            },
        },
    },
]

# ────────────────────────────────────────────────────────────────────────────
class GoogleAgent:
    """LLM-powered router that decides which Google-tool to call."""

    def __init__(self) -> None:
        """Initialize GoogleAgent and load config."""
        with CONFIG_FILE.open() as f:
            cfg = yaml.safe_load(f)

        openai.api_key = cfg["secrets"]["openai_api_key"]
        self.model = cfg["llm"]["model"]
        self.tools = GOOGLE_TOOLS
        self.calendar_manager = GoogleCalendarManager()

    def _call_llm(self, user_request: str):
        """Ask LLM which tool + arguments to use."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a Google-workflow assistant. "
                    "Pick exactly one tool and output only a tool call."
                ),
            },
            {"role": "user", "content": user_request},
        ]

        resp = openai.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tools,
            tool_choice="required",
        )
        return resp.choices[0].message

    def llm_decide_and_dispatch(
        self,
        user_request: str,
        arguments: dict | None = None,  # legacy param (ignored)
    ):
        """Decide via LLM which Google tool to run, then execute it."""
        msg = self._call_llm(user_request)

        if not getattr(msg, "tool_calls", None):
            raise ValueError("LLM response lacked a tool call.")

        call = msg.tool_calls[0]
        func_name = call.function.name
        call_args = json.loads(call.function.arguments or "{}")
        return self.dispatch(func_name, call_args)

    def dispatch(self, func_name: str, arguments: dict[str, Any]):
        """Dispatch the tool call to the appropriate handler."""
        if func_name == "get_google_calendar_events":
            return self.calendar_manager.get_upcoming_events(arguments.get("days", 7))

        elif func_name == "create_google_calendar_event":
            return "create_google_calendar_event – not yet implemented"

        elif func_name == "delete_google_calendar_event":
            return "delete_google_calendar_event – not yet implemented"

        raise NotImplementedError(f"Unknown tool: {func_name}")

    def print_calendars(self) -> None:
        """Print all available calendars."""
        self.calendar_manager.print_calendars()

    def print_upcoming_events(self, days: int = 7) -> None:
        """Print upcoming events for the next `days` days."""
        self.calendar_manager.print_upcoming_events(days)

# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    agent = GoogleAgent()
    result = agent.llm_decide_and_dispatch("What’s on my calendar in the next 7 days?")
    print(json.dumps(result, indent=2, ensure_ascii=False))
