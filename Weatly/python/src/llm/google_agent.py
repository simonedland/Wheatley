import os
import yaml
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
    

class GoogleCalendarManager:
    def _load_config(self):
      base_dir = os.path.dirname(os.path.dirname(__file__))
      config_path = os.path.join(base_dir, "config", "config.yaml")
      with open(config_path, "r") as f:
          return yaml.safe_load(f)
    
    def __init__(self):
        self.creds = self.get_google_credentials()
        self.service = build("calendar", "v3", credentials=self.creds)
        config = self._load_config()
        self.skip_calendars = set(config.get("skip_calendars", []))

    def get_google_credentials(self):
        cfg = self._load_config()
        secs = cfg["secrets"]
        client_id = secs["google_client_id"]
        client_secret = secs["google_client_secret"]
        project_id = secs["project_id"]

        creds = None
        base_dir = os.path.dirname(os.path.dirname(__file__))
        token_path = os.path.join(base_dir, "config", "token.json")

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        #if not creds or not creds.valid:
        #    if creds and creds.expired and creds.refresh_token:
        #        try:
        #            creds.refresh(Request())
        #        except Exception as e:
        #            print(f"⚠️ Failed to refresh token: {e}")
        #            creds = None
        #        client_config = {
        #            "installed": {
        #                "client_id": client_id,
        #                "project_id": project_id,
        #                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        #                "token_uri": "https://oauth2.googleapis.com/token",
        #                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        #                "client_secret": client_secret,
        #                "redirect_uris": ["http://localhost"]
        #            }
        #        }
        #        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        #        creds = flow.run_local_server(port=0)

            with open(token_path, "w") as f:
                f.write(creds.to_json())

        return creds

    def list_calendars(self):
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
        calendars = self.list_calendars()
        print("Your calendars:")
        for cal in calendars:
            print(f"- {cal['summary']} (ID: {cal['id']})")

    def print_upcoming_events(self, days=7):
        events = self.get_upcoming_events(days)
        if not events:
            print("No upcoming events found.")
            return

        print(f"\nUpcoming events (next {days} days):")
        for cal_summary, cal_events in events.items():
            print(f"\nCalendar: {cal_summary}")
            for ev in cal_events:
                print(f"  • {ev['start']} — {ev['summary']}")

