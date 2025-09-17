import cv2
import numpy as np
from importlib import resources
from functools import cache
from PIL import Image

@cache
def _get_template_path():
    with resources.path('csc316_final_project', 'hk-mask.png') as p:
        return str(p)

def get_player_health(frame):
    """
    frame: np.ndarray (BGR image to search in)
    """
    # assert isinstance(frame, np.ndarray), "frame must be a NumPy array"
    if isinstance(frame, Image.Image):
        frame = np.array(frame)  # Convert PIL Image to NumPy array
    assert isinstance(frame, np.ndarray), "frame must be a NumPy array or PIL Image"
    
    img_rgb = frame.copy()
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

    template_path = _get_template_path()
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    assert template is not None, f"Template file '{template_path}' could not be read"
    w, h = template.shape[::-1]
    
    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
    threshold = 0.7  # Higher threshold for more confident matches
    loc = np.where(res >= threshold)
    
    rectangles = []
    scores = []
    for pt in zip(*loc[::-1]):
        rect = [int(pt[0]), int(pt[1]), int(w), int(h)]
        rectangles.append(rect)
        # Get the actual confidence score for this detection
        score = res[pt[1], pt[0]]
        scores.append(float(score))

    if len(rectangles) > 0:
        # Use more aggressive NMS to reduce jitter
        nms_threshold = 0.1  # Lower threshold = more aggressive suppression
        indices = cv2.dnn.NMSBoxes(rectangles, scores, score_threshold=threshold, nms_threshold=nms_threshold)
    else:
        indices = []
    return len(indices)
