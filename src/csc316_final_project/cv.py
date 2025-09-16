import cv2
import numpy as np
import pyautogui

def get_frame():
    screenshot = pyautogui.screenshot()
    frame = np.array(screenshot)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    return frame

def get_health(template_path, frame):
    """
    template_path: str (path to template image)
    frame: np.ndarray (BGR image to search in)
    """
    assert isinstance(frame, np.ndarray), "frame must be a NumPy array"
    
    img_rgb = frame.copy()
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
    
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    assert template is not None, f"Template file '{template_path}' could not be read"
    w, h = template.shape[::-1]
    
    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
    threshold = 0.5
    loc = np.where(res >= threshold)
    
    rectangles = []
    for pt in zip(*loc[::-1]):
        rect = [int(pt[0]), int(pt[1]), int(w), int(h)]
        rectangles.append(rect)
        rectangles.append(rect)  # Duplicate for better NMS performance

    scores = [1.0] * len(rectangles)
    nms_threshold = 0.3
    indices = cv2.dnn.NMSBoxes(rectangles, scores, score_threshold=threshold, nms_threshold=nms_threshold)
    return len(indices)














