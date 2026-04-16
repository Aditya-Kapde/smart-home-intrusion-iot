import os

# Load model lazily
model = None
DEFAULT_PERSON_CONFIDENCE = float(os.getenv("YOLO_PERSON_CONFIDENCE", "0.35"))


def detect_person_details(frame, threshold=None):
    """Return YOLO person-detection details for the current frame."""
    global model
    if model is None:
        from ultralytics import YOLO
        model = YOLO("yolov8n.pt")

    min_conf = DEFAULT_PERSON_CONFIDENCE if threshold is None else float(threshold)
    results = model(frame, verbose=False)

    person_confidences = []
    person_boxes = 0

    for result in results:
        for box in result.boxes:
            if int(box.cls[0]) != 0:
                continue
            person_boxes += 1
            person_confidences.append(float(box.conf[0]))

    best_confidence = max(person_confidences, default=0.0)
    return {
        "detected": best_confidence >= min_conf,
        "best_confidence": round(best_confidence, 4),
        "threshold": min_conf,
        "person_boxes": person_boxes,
    }


def detect_person(frame, threshold=None):
    return detect_person_details(frame, threshold=threshold)["detected"]
