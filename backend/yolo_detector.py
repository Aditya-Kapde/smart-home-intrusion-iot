from ultralytics import YOLO
import cv2

# Load model (first time will auto-download)
model = YOLO("yolov8n.pt")

def detect_person(frame):
    results = model(frame)

    detected = False

    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            if cls == 0:  # class 0 = person
                detected = True

    return detected