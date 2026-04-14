def detect_intrusion(data):
    motion = data.get("motion", False)

    if motion:
        return {
            "intrusion": True,
            "message": "Motion detected! Possible intrusion."
        }
    
    return {
        "intrusion": False,
        "message": "No activity."
    }