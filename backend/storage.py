import json
import os
import threading
from datetime import datetime

EVENTS_FILE = os.path.join(os.path.dirname(__file__), "events.json")
_EVENTS_LOCK = threading.Lock()

def save_event(event):
    payload = dict(event)
    payload["timestamp"] = payload.get("timestamp") or datetime.now().isoformat(timespec="seconds")

    with _EVENTS_LOCK:
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    data = []
        except (FileNotFoundError, json.JSONDecodeError):
            data = []

        data.append(payload)

        with open(EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)