import requests
import time
import random

URL = "http://127.0.0.1:5000/detect"

while True:
    motion = random.choice([True, False])

    data = {"motion": motion}

    res = requests.post(URL, json=data)
    
    print("Sent:", data)
    print("Response:", res.json())
    print("-" * 40)

    time.sleep(3)