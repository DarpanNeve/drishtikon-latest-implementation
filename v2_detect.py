# Member Amruta Kothawade, Do NOT paste your code here
import os
import sys
import subprocess
import cv2
import time
import datetime
import threading
import tkinter as tk
from tkinter import filedialog
from PIL import Image
import io
from dotenv import load_dotenv
import google.generativeai as genai
from ultralytics import YOLO

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.utils import absolute_path, ensure_dir, load_credential_path
from core.tts import speak, speak_cached
from core.tts_player import tts_main
from core.logger import log
from core.playback_controls import play, non_blocking_play, read_key_nonblocking
from core.prompts import *

load_dotenv()

# ================================================================
#  CREDENTIALS & MODELS
# ================================================================
CRED_PATH = load_credential_path("yolo", "yolo-key.json")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

yolo_model = YOLO("yolov8n.pt")

# Global flag to prevent clashing inferences
gemini_active = False

# ================================================================
# HELPERS
# ================================================================
def ensure_results_dir():
    ensure_dir(absolute_path("results"))
    ensure_dir(absolute_path("results", "yolo_outputs"))
    ensure_dir(absolute_path("results", "prompt_cache"))

def optimize_image(image_path):
    """Resize + compress image for faster Gemini processing."""
    img = Image.open(image_path)
    if img.mode == "RGBA":
        img = img.convert("RGB")
    img.thumbnail((1800, 1800))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()

# ================================================================
# DETECTION LOGIC
# ================================================================
def run_yolo(image_path):
    """Run YOLOv8 and return verbal description."""
    img = cv2.imread(image_path)
    results = yolo_model.predict(img, verbose=False)
    
    boxes = results[0].boxes
    names = results[0].names
    
    if not boxes:
        return "No objects detected."

    counts = {}
    for box in boxes:
        label = names[int(box.cls[0])]
        counts[label] = counts.get(label, 0) + 1

    parts = [f"{c} {l}{'' if c==1 else 's'}" for l, c in counts.items()]
    return "I can see " + ", ".join(parts) + "."

def gemini_summary_task(image_path):
    """Handles Gemini inference and interruptible playback."""
    global gemini_active
    gemini_active = True
    
    play(tts_main, processing_p)
    
    refinement_prompt = "Describe this scene for a visually impaired user in 30 words. Focus on obstacles."
    
    try:
        optimized_bytes = optimize_image(image_path)
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        start = time.time()
        response = model.generate_content([
            {"mime_type": "image/jpeg", "data": optimized_bytes},
            refinement_prompt,
        ])
        
        text = getattr(response, "text", "")
        duration = round(time.time() - start, 2)
        log("DETECTION-GEMINI", image_path, f"{len(text)} chars", duration)
        
        # Non-blocking play allows user to press 's' to stop summary
        audio_path = speak(text)
        non_blocking_play(
            tts_main, 
            audio_path, 
            "Press 's' to stop summary", 
            stopping_summary_p
        )
        
    finally:
        gemini_active = False

# ================================================================
# FILE PICKER
# ================================================================
def choose_file():
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    fp = filedialog.askopenfilename(
        title="Select an image file",
        filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp *.webp")]
    )
    root.destroy()
    return fp

# ================================================================
# MAIN
# ================================================================
def main():
    ensure_results_dir()
    
    play(tts_main, select_file_p)
    img_path = choose_file()
    
    cam = None
    if not img_path:
        play(tts_main, cap_intro_p)
        cam = cv2.VideoCapture(0)
    
    last_yolo_time = time.time()
    print("\n[CONTROLS]: Y: YOLO | G: Gemini | Q: Quit | S: Stop Speech\n")
    
    while True:
        # Image Source Logic
        if cam and cam.isOpened():
            ret, frame = cam.read()
            if ret:
                cv2.imshow("Detection Feed", frame)
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                current_img = absolute_path("results", "yolo_outputs", f"live.jpg")
                cv2.imwrite(current_img, frame)
            else:
                continue
        else:
            current_img = img_path
            frame = cv2.imread(current_img)
            cv2.imshow("Detection Feed", frame)

        key = cv2.waitKey(1) & 0xFF
        
        # 1. AUTO-YOLO (Every 10 seconds)
        # Does not run if Gemini is currently active
        if time.time() - last_yolo_time > 10:
            if not gemini_active and not tts_main.is_playing():
                print("[AUTO-YOLO] Triggering routine scan...")
                desc = run_yolo(current_img)
                audio = speak(desc)
                tts_main.play(audio)
                last_yolo_time = time.time()

        # 2. MANUAL YOLO (y)
        if key == ord('y') and not gemini_active:
            description = run_yolo(current_img)
            print(f"[YOLO]: {description}")
            audio = speak(description)
            tts_main.play(audio)
            last_yolo_time = time.time() # Reset timer on manual trigger

        # 3. GEMINI SUMMARY (g)
        elif key == ord('g') and not gemini_active:
            threading.Thread(target=gemini_summary_task, args=(current_img,), daemon=True).start()

        # 4. QUIT (q)
        elif key == ord('q'):
            play(tts_main, exiting_detection_module_p)
            break

    if cam:
        cam.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()