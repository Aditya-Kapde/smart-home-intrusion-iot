import json
from datetime import datetime

def save_event(event):
    event["timestamp"] = str(datetime.now())

    try:
        with open("events.json", "r") as f:
            data = json.load(f)
    except:
        data = []

    data.append(event)

    with open("events.json", "w") as f:
        json.dump(data, f, indent=4)