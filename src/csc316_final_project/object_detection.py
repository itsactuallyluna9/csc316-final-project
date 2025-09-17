import numpy as np
from ultralytics import YOLO
import cv2
from importlib import resources
from PIL import Image

def detect_flash(crop, white_thresh=220, flash_pixel_ratio=0.05):
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    white_mask = (v >= white_thresh) & (s <= 60)
    white_pixels = np.sum(white_mask)
    white_ratio = white_pixels / (crop.shape[0] * crop.shape[1])

    return white_ratio

def find_false_knight(frame, model):
    results = model.predict(frame, stream=True, verbose=False)
    for r in results:
        for box in r.boxes:
            conf = box.conf[0].item()
            if conf > 0.5:  # confidence threshold
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                return (x1, y1, x2 - x1, y2 - y1)  # (x, y, w, h)
    return None

def detect_fk_hit(frame, model):
    if isinstance(frame, Image.Image):
        frame = np.array(frame)
    bbox = find_false_knight(frame, model)
    if not bbox:
        return False
    x, y, w, h = bbox
    crop = frame[y:y+h, x:x+w]
    if crop.size == 0 or crop.shape[0] == 0 or crop.shape[1] == 0:
        return False
    white_ratio = detect_flash(crop)
    return white_ratio > 0.05  # threshold for hit detection

def load_yolo_model():
    # simply so we don't have to complicate things!
    with resources.path('csc316_final_project', 'best.pt') as path_to_model:
        model = YOLO(path_to_model)
        return model

def test_model(path_to_model, gameplay_source): #path_to_model should be the best.pt file and the gameplay source can be an obs virtual camera

    model = YOLO(path_to_model)

    tracker = None
    tracking_box = None
    missed_frames = 0
    MAX_MISSED_FRAMES = 10

    cap = cv2.VideoCapture(gameplay_source)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        use_tracking = False
        results = model.predict(frame, stream=True, verbose=False)

        detection_found = False
        for r in results:
            for box in r.boxes:
                conf = box.conf[0].item()
                if conf > 0.5:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    bbox = (x1, y1, x2 - x1, y2 - y1)  
                    detection_found = True

                    tracker = cv2.TrackerCSRT_create()
                    tracker.init(frame, bbox)
                    tracking_box = bbox
                    missed_frames = 0
                    break

        if not detection_found and tracker:
            success, bbox = tracker.update(frame)
            if success:
                tracking_box = bbox
                missed_frames += 1
                use_tracking = True
            else:
                tracker = None
                tracking_box = None

        if tracking_box:
            x, y, w, h = map(int, tracking_box)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            crop = frame[y:y+h, x:x+w]
            if crop.size == 0 or crop.shape[0] == 0 or crop.shape[1] == 0:
                print("Empty crop detected, skipping...")
                continue
            white_ratio = detect_flash(crop)
            if white_ratio > 0.05:
                print("White flash detected!") #detects both armour hits and actual hits on the false knight with like 80% accuracy, should ignore the wave attacks

        if missed_frames > MAX_MISSED_FRAMES:
            tracker = None
            tracking_box = None
            missed_frames = 0

        cv2.imshow("Smooth Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
