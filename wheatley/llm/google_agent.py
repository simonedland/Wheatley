"""Google Calendar integration helpers and LLM agent."""

import os
import yaml
import openai
import json
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class GoogleCalendarManager:
    """Wrapper for Google Calendar API interactions."""

    def _load_config(self):
        """Return YAML configuration dictionary."""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        config_path = os.path.join(base_dir, "config", "config.yaml")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def __init__(self):
        """Initialize Google Calendar manager with credentials and service."""
        try:
            self.creds = self.get_google_credentials()
            self.service = build("calendar", "v3", credentials=self.creds)
        except Exception:
            print("❌ ERROR: Authentication failed for Google Calendar! Please check your credentials or login again.")
            raise
        config = self._load_config()
        self.skip_calendars = set(config.get("skip_calendars", []))

    def get_google_credentials(self):
        """Load or refresh Google Calendar API credentials."""
        try:
            creds = None
            base_dir = os.path.dirname(os.path.dirname(__file__))
            token_path = os.path.join(base_dir, "config", "token.json")

            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)

            # if not creds or not creds.valid:
            #     if creds and creds.expired and creds.refresh_token:
            #         try:
            #             creds.refresh(Request())

            if creds is not None:
                with open(token_path, "w") as f:
                    f.write(creds.to_json())
            return creds
        except Exception:
            print("❌ ERROR: Authentication failed for Google Calendar! Please check your credentials or login again.")
            raise

    def list_calendars(self):
        """List all calendars, excluding those in the skip list."""
        try:
            cal_list = self.service.calendarList().list().execute().get("items", [])
            calendars = [
                {"id": cal["id"], "summary": cal.get("summary", "")}
                for cal in cal_list
                if cal["id"] not in self.skip_calendars
            ]
            return calendars
        except HttpError as e:
            print(f"Failed to fetch calendars: {e}")
            return []

    def get_upcoming_events(self, days=7):
        """Get upcoming events from all calendars for the next `days` days."""
        now = datetime.utcnow().isoformat() + "Z"
        future = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"
        all_events = {}

        calendars = self.list_calendars()
        for cal in calendars:
            try:
                events = self.service.events().list(
                    calendarId=cal["id"],
                    timeMin=now,
                    timeMax=future,
                    singleEvents=True,
                    orderBy="startTime"
                ).execute().get("items", [])
                if events:
                    all_events[cal["summary"]] = [
                        {
                            "start": ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date"),
                            "summary": ev.get("summary", "(no title)")
                        }
                        for ev in events
                    ]
            except HttpError as e:
                print(f"  Failed to fetch events for {cal['id']}: {e}")
                continue

        return all_events

    def print_calendars(self):
        """Print all calendars with their IDs."""
        calendars = self.list_calendars()
        print("Your calendars:")
        for cal in calendars:
            print(f"- {cal['summary']} (ID: {cal['id']})")

    def print_upcoming_events(self, days=7):
        """Print upcoming events from all calendars for the next `days` days."""
        events = self.get_upcoming_events(days)
        if not events:
            print("No upcoming events found.")
            return

        print(f"\nUpcoming events (next {days} days):")
        for cal_summary, cal_events in events.items():
            print(f"\nCalendar: {cal_summary}")
            for ev in cal_events:
                print(f"  • {ev['start']} — {ev['summary']}")


# implement placeholder google functions
GOOGLE_TOOLS = [
    {
        "type": "function",
        "name": "get_google_calendar_events",
        "description": "Get upcoming events from Google Calendar. Use this if user asks for schedule or calendar events.",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer"}
            },
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "create_google_calendar_event",
        "description": "Create a new event in Google Calendar. Use this if user wants to create an event.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "start_time": {"type": "string"},
                "end_time": {"type": "string"},
                "description": {"type": "string"}
            },
            "required": ["summary", "start_time", "end_time"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "delete_google_calendar_event",
        "description": "Delete an event from Google Calendar. Use this if user wants to delete an event.",
        "parameters": {
            "type": "object",
            "properties": {
                "temp": {"type": "string"}
            },
            "required": [],
            "additionalProperties": False
        }
    }
]


class GoogleAgent:
    """LLM-driven assistant for interacting with Google services."""

    def _load_config(self):
        """Load project configuration YAML."""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        config_path = os.path.join(base_dir, "config", "config.yaml")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def __init__(self):
        """Initialize Google Agent with API key and tools."""
        config = self._load_config()
        self.api_key = config["secrets"]["openai_api_key"]
        self.calendar_manager = GoogleCalendarManager()
        self.tools = GOOGLE_TOOLS
        self.model = config["llm"]["model"]
        openai.api_key = self.api_key

    def llm_decide_and_dispatch(self, user_request: str, arguments: dict = None):
        """Use LLM to decide which Google tool to use based on the user request, then execute it."""
        from datetime import datetime
        now = datetime.now()
        tool_descriptions = "\n".join([
            f"- {tool['name']}: {tool['description']}" for tool in self.tools
        ])
        system_prompt = (
            f"You are a Google Agent. Available tools are:\n{tool_descriptions}\n"
            f"Choose the best tool for the user request and return only the tool name. "
            f"current_time: {now.strftime('%Y-%m-%d %H:%M:%S')}, current_day: {now.strftime('%A')}"
        )
        prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_request}
        ]
        print(f"\n--- Google Agent Decision Trace ---")
        print(f"User: {user_request}")
        print(f"Prompt to LLM: {prompt}")
        completion = openai.responses.create(
            model=self.model,
            input=prompt,
            tools=self.tools,
            tool_choice="required",
            parallel_tool_calls=False
        )
        choice = completion.output
        print("LLM chose:")
        for msg in choice:
            if msg.type == "function_call":
                print(f"  Tool: {msg.name}")
                print(f"  Arguments: {msg.arguments}")
                print(f"  Call ID: {getattr(msg, 'call_id', None)}")
        print(f"--- End Google Agent Decision Trace ---\n")
        # Dispatch the chosen tool
        for msg in choice:
            if msg.type == "function_call":
                func_name = msg.name
                arguments = msg.arguments
                return self.dispatch(func_name, arguments)

        raise ValueError("No function call found in LLM response.")

    def dispatch(self, func_name, arguments):
        """Dispatch the function call to the appropriate Google tool."""
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except Exception:
                arguments = {}
        if func_name == "get_google_calendar_events":
            days = arguments.get("days", 7)
            return self.get_google_calendar_events(days)
        elif func_name == "create_google_calendar_event":
            return "not implemented"
        elif func_name == "delete_google_calendar_event":
            return "not implemented"
        raise NotImplementedError(f"Function {func_name} not implemented in GoogleAgent.")

    def get_google_calendar_events(self, days=7):
        """Get upcoming events from Google Calendar for the next `days` days."""
        return self.calendar_manager.get_upcoming_events(days)

    def print_calendars(self):
        """Print all Google Calendars."""
        self.calendar_manager.print_calendars()

    def print_upcoming_events(self, days=7):
        """Print upcoming events from Google Calendar for the next `days` days."""
        self.calendar_manager.print_upcoming_events(days)
