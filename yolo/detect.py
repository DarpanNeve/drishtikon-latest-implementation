import os
import sys
import subprocess
import cv2
import time
import threading
import tkinter as tk
from tkinter import filedialog
from PIL import Image
import io
from dotenv import load_dotenv
import google.generativeai as genai
from ultralytics import YOLO
from core.navigation.state import DETECTIONS, state_lock

from core.priority_audio import AudioPriority, PriorityAudioManager
from core.utils import absolute_path, ensure_dir, load_credential_path
from core.tts import speak
from core.tts_player import tts_main
from core.logger import log
from core.playback_controls import play, non_blocking_play
from core.prompts import *

load_dotenv()

# ================================================================
#  INSTANTIATE PRIORITY AUDIO MANAGER
# ================================================================
priority_audio = PriorityAudioManager(tts_main)
# ================================================================
#  CONFIG & CONSTANTS (New Features)
# ================================================================
FOCAL_LENGTH = 80  # Calibration constant for distance
DISTANCE_THRESHOLD = 0.8 # Meters of movement before re-announcing
KNOWN_HEIGHTS = {
    "person": 1.7, "car": 1.5, "bus": 3.0, "truck": 3.0,
    "bicycle": 1.0, "chair": 1.0, "dog": 0.5, "bottle": 0.2
}

# State Tracking
last_announced = {} # Format: {label: (position, distance)}
gemini_active = False

# ================================================================
#  CREDENTIALS & MODELS
# ================================================================
load_credential_path("yolo", "yolo-key.json")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

yolo_model = YOLO("yolov8n.pt")

# ================================================================
#  NEW FEATURE HELPERS (Spatial & Distance)
# ================================================================
def estimate_distance(label, box_height):
    real_height = KNOWN_HEIGHTS.get(label, 1.5) # Default 1.5m
    if box_height <= 0: return None
    return round((real_height * FOCAL_LENGTH) / box_height, 2)

def get_position(x_center, frame_width):
    ratio = x_center / frame_width
    if ratio < 0.35: return "left"
    if ratio > 0.65: return "right"
    return "center"

def should_announce(label, position, distance):
    """Smart Throttling: Only speak if significant change."""
    prev = last_announced.get(label)
    if not prev:
        last_announced[label] = (position, distance)
        return True
    
    prev_pos, prev_dist = prev
    # Announce if position changed OR distance changed significantly
    if prev_pos != position or abs(prev_dist - distance) >= DISTANCE_THRESHOLD:
        last_announced[label] = (position, distance)
        return True
    return False

# ================================================================
#  DETECTION LOGIC
# ================================================================
def run_smart_yolo(frame):
    with state_lock:
        DETECTIONS.append({
            "label": label,
            "position": pos,
            "distance": dist,
            "timestamp": time.time()
        })

    """Refined YOLO with distance and position awareness."""
    h, w, _ = frame.shape
    results = yolo_model.predict(frame, verbose=False)[0]
    
    announcements = []
    
    for box in results.boxes:
        label = results.names[int(box.cls[0])]
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        
        dist = estimate_distance(label, y2 - y1)
        pos = get_position((x1 + x2) / 2, w)
        
        if should_announce(label, pos, dist):
            announcements.append(f"{label} on your {pos}, {dist} meters away.")
            
        # Draw on frame for visual debug
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"{label} {dist}m", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

    return ". ".join(announcements) if announcements else None

def gemini_summary_task(image_path):
    global gemini_active
    priority_audio.request_play(processing_p, AudioPriority.SYSTEM)

    try:
        img = Image.open(image_path)
        if img.mode == "RGBA":
            img = img.convert("RGB")

        img.thumbnail((1600, 1600))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)

        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content([
            {"mime_type": "image/jpeg", "data": buf.getvalue()},
            "Describe this scene for a visually impaired user in 2 sentences. Focus on obstacles."
        ])

        text = getattr(response, "text", "Unable to describe scene.")
        audio_path = speak(text)
        priority_audio.request_play(audio_path, AudioPriority.GEMINI)

    finally:
        gemini_active = False
# ================================================================
#  MAIN LOOP
# ================================================================
def main():
    ensure_dir(absolute_path("results", "yolo_outputs"))
    # "Select file or press Enter for camera"
    priority_audio.request_play(select_file_p, AudioPriority.SYSTEM)
    
    # Simple logic: If user doesn't pick file, use Camera
    root = tk.Tk(); root.withdraw()
    img_path = filedialog.askopenfilename()
    root.destroy()

    cam = cv2.VideoCapture(0) if not img_path else None
    last_yolo_time = 0

    while True:
        priority_audio.notify_idle()
        if cam:
            ret, frame = cam.read()
            if not ret: break
            current_img_path = absolute_path("results", "yolo_outputs", "live_cache.jpg")
            cv2.imwrite(current_img_path, frame)
        else:
            frame = cv2.imread(img_path)
            current_img_path = img_path

        cv2.imshow("Detection Feed", frame)
        key = cv2.waitKey(1) & 0xFF

        # AUTO-YOLO with Spatial Awareness (Every 8 seconds)
        YOLO_FAST = 0.6     # moving / dynamic
        YOLO_SLOW = 2.0     # static scene
        current_yolo_interval = YOLO_FAST

        if time.time() - last_yolo_time > current_yolo_interval:
            if not gemini_active and not tts_main.is_playing():
                desc = run_smart_yolo(frame)

                if desc:
                    audio_path = speak(desc, is_detection=True)
                    priority_audio.request_play(audio_path, AudioPriority.DETECTION)
                    current_yolo_interval = YOLO_FAST   # scene changing
                else:
                    current_yolo_interval = YOLO_SLOW   # scene stable

                last_yolo_time = time.time()

        # MANUAL GEMINI (G)
        if key == ord('g') and not gemini_active:
            threading.Thread(target=gemini_summary_task, args=(current_img_path,), daemon=True).start()

        # QUIT (Q)
        elif key == ord('q'):
            priority_audio.play_exit(exiting_detection_module_p)
            break

    if cam: cam.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()