import os
import cv2
import time
import threading
import tkinter as tk
from tkinter import filedialog
from PIL import Image
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict
from collections import deque
import io
from functools import lru_cache
from dotenv import load_dotenv
import google.generativeai as genai
from ultralytics import YOLO

from core.priority_audio import AudioPriority, PriorityAudioManager
from core.utils import absolute_path, ensure_dir, load_credential_path
from core.tts import speak, speak_cached
from core.tts_player import tts_main
from core.logger import log
from core.stt import listen
from core.prompts import select_file_p, processing_p, exiting_detection_module_p

load_dotenv()


class DetectionMode(Enum):
    YOLO = "yolo"
    GEMINI = "gemini"


@dataclass(frozen=True)
class DetectionConfig:
    FOCAL_LENGTH: int = 80
    STEP_SIZE: float = 0.7
    DISTANCE_THRESHOLD: float = 0.8
    CONFIDENCE_THRESHOLD: float = 0.40
    DETECTION_INTERVAL: int = 8
    GEMINI_MAX_RETRIES: int = 3
    GEMINI_RETRY_DELAY: float = 1.0
    FRAME_CACHE_SIZE: int = 5
    IMAGE_MAX_SIZE: Tuple[int, int] = (1600, 1600)
    JPEG_QUALITY: int = 75


@dataclass(frozen=True)
class ObjectHeight:
    PERSON: float = 1.7
    CAR: float = 1.5
    BUS: float = 3.0
    TRUCK: float = 3.0
    BICYCLE: float = 1.0
    CHAIR: float = 1.0
    DOG: float = 0.5
    BOTTLE: float = 0.2
    DEFAULT: float = 1.5


CONFIG = DetectionConfig()
HEIGHTS = ObjectHeight()

KNOWN_HEIGHTS: Dict[str, float] = {
    "person": HEIGHTS.PERSON,
    "car": HEIGHTS.CAR,
    "bus": HEIGHTS.BUS,
    "truck": HEIGHTS.TRUCK,
    "bicycle": HEIGHTS.BICYCLE,
    "chair": HEIGHTS.CHAIR,
    "dog": HEIGHTS.DOG,
    "bottle": HEIGHTS.BOTTLE
}

PRIORITY_OBJECTS = frozenset({"person", "car", "bus", "truck", "bicycle", "motorcycle", "dog"})

GEMINI_PROMPT = """You are a navigation assistant for a blind person. Analyze this image and provide ACTIONABLE guidance in 2-3 short sentences.

RULES:
- Use clock positions (12 o'clock = straight ahead, 3 = right, 9 = left)
- Mention SPECIFIC obstacles: "Chair at 2 o'clock, about 3 steps away"
- Warn about hazards: stairs, curbs, wet floors, uneven surfaces
- Suggest safe path: "Clear path at 11 o'clock"
- Mention people and their movement: "Person approaching from 3 o'clock"
- Be concise but specific. No poetic language.

Example: "Person standing at 12 o'clock, 5 steps ahead. Table with chairs blocking 2 to 4 o'clock. Clear path on your left at 9 o'clock."
"""

VOICE_COMMANDS = {
    "gemini": ["gemini", "jimmy", "jemini", "ai", "scene", "describe", "german"],
    "yolo": ["yolo", "yellow", "object", "detect", "euro", "you low"],
    "exit": ["exit", "quit", "stop", "close", "end", "bye"]
}


class DetectionState:
    __slots__ = ('_lock', '_announced', '_gemini_active', '_mode', '_last_detection')
    
    def __init__(self):
        self._lock = threading.RLock()
        self._announced: Dict[str, Tuple[str, float]] = {}
        self._gemini_active = False
        self._mode = DetectionMode.YOLO
        self._last_detection = 0.0
    
    @property
    def gemini_active(self) -> bool:
        with self._lock:
            return self._gemini_active
    
    @gemini_active.setter
    def gemini_active(self, value: bool):
        with self._lock:
            self._gemini_active = value
    
    @property
    def mode(self) -> DetectionMode:
        with self._lock:
            return self._mode
    
    @mode.setter
    def mode(self, value: DetectionMode):
        with self._lock:
            self._mode = value
    
    @property
    def last_detection(self) -> float:
        with self._lock:
            return self._last_detection
    
    @last_detection.setter
    def last_detection(self, value: float):
        with self._lock:
            self._last_detection = value
    
    def should_announce(self, label: str, position: str, distance: float) -> bool:
        with self._lock:
            prev = self._announced.get(label)
            if not prev:
                self._announced[label] = (position, distance)
                return True
            prev_pos, prev_dist = prev
            if prev_pos != position or abs(prev_dist - distance) >= CONFIG.DISTANCE_THRESHOLD:
                self._announced[label] = (position, distance)
                return True
            return False
    
    def clear_announced(self):
        with self._lock:
            self._announced.clear()


class ModelManager:
    _yolo_model = None
    _gemini_model = None
    _lock = threading.Lock()
    
    @classmethod
    def get_yolo(cls) -> YOLO:
        if cls._yolo_model is None:
            with cls._lock:
                if cls._yolo_model is None:
                    cls._yolo_model = YOLO("yolov8m.pt")
        return cls._yolo_model
    
    @classmethod
    def get_gemini(cls):
        if cls._gemini_model is None:
            with cls._lock:
                if cls._gemini_model is None:
                    model_name = os.getenv("GEMINI_MODEL")
                    if model_name:
                        cls._gemini_model = genai.GenerativeModel(model_name)
        return cls._gemini_model


class SpatialAnalyzer:
    CLOCK_POSITIONS = (
        (0.15, "9 o'clock"),
        (0.30, "10 o'clock"),
        (0.45, "11 o'clock"),
        (0.55, "12 o'clock"),
        (0.70, "1 o'clock"),
        (0.85, "2 o'clock"),
        (1.01, "3 o'clock")
    )
    
    @staticmethod
    def estimate_distance(label: str, box_height: int) -> Optional[float]:
        if box_height <= 0:
            return None
        real_height = KNOWN_HEIGHTS.get(label, HEIGHTS.DEFAULT)
        return round((real_height * CONFIG.FOCAL_LENGTH) / box_height, 2)
    
    @staticmethod
    def meters_to_steps(meters: Optional[float]) -> Optional[int]:
        if meters is None:
            return None
        return max(1, round(meters / CONFIG.STEP_SIZE))
    
    @classmethod
    def get_clock_position(cls, x_center: float, frame_width: int) -> str:
        ratio = x_center / frame_width
        for threshold, position in cls.CLOCK_POSITIONS:
            if ratio < threshold:
                return position
        return "3 o'clock"
    
    @staticmethod
    def detect_clear_zones(boxes: List, frame_width: int) -> List[str]:
        zones = {"left": True, "center": True, "right": True}
        for box in boxes:
            x1, _, x2, _ = map(int, box.xyxy[0])
            ratio = (x1 + x2) / 2 / frame_width
            if ratio < 0.35:
                zones["left"] = False
            elif ratio > 0.65:
                zones["right"] = False
            else:
                zones["center"] = False
        result = []
        if zones["left"]:
            result.append("9 o'clock")
        if zones["center"]:
            result.append("12 o'clock")
        if zones["right"]:
            result.append("3 o'clock")
        return result


class YOLOProcessor:
    def __init__(self, state: DetectionState):
        self._state = state
        self._analyzer = SpatialAnalyzer()
    
    def process_frame(self, frame) -> Optional[str]:
        try:
            h, w = frame.shape[:2]
            model = ModelManager.get_yolo()
            results = model.predict(frame, verbose=False)[0]
            
            announcements = []
            detected_boxes = []
            priority_announcements = []
            
            for box in results.boxes:
                conf = float(box.conf[0])
                if conf < CONFIG.CONFIDENCE_THRESHOLD:
                    continue
                
                label = results.names[int(box.cls[0])]
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detected_boxes.append(box)
                
                dist_meters = self._analyzer.estimate_distance(label, y2 - y1)
                steps = self._analyzer.meters_to_steps(dist_meters)
                clock_pos = self._analyzer.get_clock_position((x1 + x2) / 2, w)
                
                if self._state.should_announce(label, clock_pos, dist_meters or 0):
                    step_text = "1 step" if steps == 1 else f"{steps} steps"
                    announcement = f"{label} at {clock_pos}, {step_text} ahead"
                    
                    if label in PRIORITY_OBJECTS:
                        priority_announcements.append(announcement)
                    else:
                        announcements.append(announcement)
                
                self._draw_detection(frame, x1, y1, x2, y2, label, steps)
            
            all_announcements = priority_announcements + announcements
            
            if all_announcements:
                clear_zones = self._analyzer.detect_clear_zones(detected_boxes, w)
                if clear_zones:
                    all_announcements.append(f"Clear path at {', '.join(clear_zones)}")
            
            return ". ".join(all_announcements) if all_announcements else None
            
        except Exception as e:
            log("YOLO", "-", f"Detection error: {e}")
            return None
    
    @staticmethod
    def _draw_detection(frame, x1: int, y1: int, x2: int, y2: int, label: str, steps: Optional[int]):
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        display_text = f"{label} {steps}st" if steps else label
        cv2.putText(frame, display_text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)


class GeminiProcessor:
    def __init__(self, state: DetectionState, audio_manager: PriorityAudioManager):
        self._state = state
        self._audio = audio_manager
    
    def process_image(self, image_path: str) -> bool:
        self._state.gemini_active = True
        self._audio.request_play(processing_p, AudioPriority.SYSTEM)
        
        try:
            image_data = self._prepare_image(image_path)
            if image_data is None:
                raise ValueError("Failed to prepare image")
            
            response_text = self._call_gemini_with_retry(image_data)
            if response_text:
                print(f"[GEMINI] {response_text}")
                audio_path = speak(response_text)
                self._audio.request_play(audio_path, AudioPriority.GEMINI)
                tts_main.wait()
                return True
            return False
            
        except Exception as e:
            log("GEMINI", "-", f"Processing error: {e}")
            print(f"[GEMINI] ERROR: {e}")
            self._handle_error()
            return False
            
        finally:
            self._state.gemini_active = False
    
    def _prepare_image(self, image_path: str) -> Optional[bytes]:
        try:
            img = Image.open(image_path)
            if img.mode == "RGBA":
                img = img.convert("RGB")
            img.thumbnail(CONFIG.IMAGE_MAX_SIZE)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=CONFIG.JPEG_QUALITY)
            return buf.getvalue()
        except Exception:
            return None
    
    def _call_gemini_with_retry(self, image_data: bytes) -> Optional[str]:
        model = ModelManager.get_gemini()
        if not model:
            return None
        
        for attempt in range(CONFIG.GEMINI_MAX_RETRIES):
            try:
                response = model.generate_content([
                    {"mime_type": "image/jpeg", "data": image_data},
                    GEMINI_PROMPT
                ])
                return getattr(response, "text", None)
            except Exception as e:
                if attempt < CONFIG.GEMINI_MAX_RETRIES - 1:
                    time.sleep(CONFIG.GEMINI_RETRY_DELAY * (attempt + 1))
                else:
                    raise e
        return None
    
    def _handle_error(self):
        error_audio = speak("Unable to process the image.")
        self._audio.request_play(error_audio, AudioPriority.SYSTEM)
        tts_main.wait()


class CameraManager:
    def __init__(self, camera_index: int = 0):
        self._camera_index = camera_index
        self._cap = None
        self._frame_buffer = deque(maxlen=CONFIG.FRAME_CACHE_SIZE)
        self._lock = threading.Lock()
    
    def open(self) -> bool:
        try:
            self._cap = cv2.VideoCapture(self._camera_index)
            return self._cap.isOpened()
        except Exception:
            return False
    
    def read(self) -> Tuple[bool, Optional[any]]:
        if not self._cap:
            return False, None
        with self._lock:
            ret, frame = self._cap.read()
            if ret:
                self._frame_buffer.append(frame.copy())
            return ret, frame
    
    def get_stable_frame(self) -> Optional[any]:
        with self._lock:
            if self._frame_buffer:
                return self._frame_buffer[-1].copy()
        return None
    
    def release(self):
        if self._cap:
            self._cap.release()
            self._cap = None


class DetectionController:
    def __init__(self):
        self._state = DetectionState()
        self._audio = PriorityAudioManager(tts_main)
        self._yolo = YOLOProcessor(self._state)
        self._gemini = GeminiProcessor(self._state, self._audio)
        self._camera: Optional[CameraManager] = None
        self._output_dir = absolute_path("results", "yolo_outputs")
        self._prompts = self._init_prompts()
    
    @staticmethod
    @lru_cache(maxsize=1)
    def _init_prompts() -> Dict[str, str]:
        return {
            "gemini": speak_cached("Switched to Gemini mode. Press Y or say YOLO to go back.", "switch_gemini.wav"),
            "yolo": speak_cached("Switched to YOLO mode. Press G or say Gemini to switch.", "switch_yolo.wav"),
            "listening": speak_cached("Listening. Say Gemini, YOLO, or Exit.", "voice_listening.wav"),
            "no_speech": speak_cached("I didn't hear anything.", "voice_no_speech.wav"),
            "unknown": speak_cached("Unknown command. Say Gemini, YOLO, or Exit.", "voice_unknown.wav")
        }
    
    def run(self):
        ensure_dir(self._output_dir)
        self._audio.request_play(select_file_p, AudioPriority.SYSTEM)
        
        img_path = self._select_input()
        use_camera = not img_path
        
        if use_camera:
            self._camera = CameraManager()
            if not self._camera.open():
                log("CAMERA", "-", "Failed to open camera")
                return
        
        self._main_loop(img_path, use_camera)
        self._cleanup()
    
    def _select_input(self) -> Optional[str]:
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename()
        root.destroy()
        return path if path else None
    
    def _main_loop(self, img_path: Optional[str], use_camera: bool):
        while True:
            self._audio.notify_idle()
            
            if self._state.mode is None:
                self._audio.play_exit(exiting_detection_module_p)
                break
            
            frame = self._get_frame(img_path, use_camera)
            if frame is None:
                break
            
            cv2.imshow("Detection Feed", frame)
            key = cv2.waitKey(1) & 0xFF
            
            if self._handle_input(key):
                break
            
            self._process_detection(frame)
    
    def _get_frame(self, img_path: Optional[str], use_camera: bool):
        if use_camera and self._camera:
            ret, frame = self._camera.read()
            if not ret:
                return None
            cv2.imwrite(absolute_path(self._output_dir, "live_cache.jpg"), frame)
            return frame
        elif img_path:
            return cv2.imread(img_path)
        return None
    
    def _handle_input(self, key: int) -> bool:
        if key == ord('g') and self._state.mode != DetectionMode.GEMINI:
            self._switch_to_gemini()
            
        elif key == ord('y') and self._state.mode != DetectionMode.YOLO:
            self._switch_to_yolo()
            
        elif key == ord('v'):
            self._handle_voice_command()
            
        elif key == ord('q'):
            self._audio.play_exit(exiting_detection_module_p)
            return True
        
        return False
    
    def _switch_to_gemini(self):
        self._state.mode = DetectionMode.GEMINI
        self._state.last_detection = 0
        print("\n[MODE] Switched to GEMINI mode")
        self._audio.request_play(self._prompts["gemini"], AudioPriority.SYSTEM)
    
    def _switch_to_yolo(self):
        self._state.mode = DetectionMode.YOLO
        self._state.last_detection = 0
        self._state.clear_announced()
        print("\n[MODE] Switched to YOLO mode")
        self._audio.request_play(self._prompts["yolo"], AudioPriority.SYSTEM)
    
    def _handle_voice_command(self):
        tts_main.stop()
        listening_prompt = self._prompts.get("listening")
        if listening_prompt:
            self._audio.request_play(listening_prompt, AudioPriority.SYSTEM)
            tts_main.wait()
        
        print("\n[VOICE] Listening for command...")
        
        try:
            text = listen(duration=4)
            if not text:
                print("[VOICE] No speech detected")
                no_speech_prompt = self._prompts.get("no_speech")
                if no_speech_prompt:
                    self._audio.request_play(no_speech_prompt, AudioPriority.SYSTEM)
                return
            
            text = text.lower().strip()
            print(f"[VOICE] Heard: {text}")
            
            command = self._parse_voice_command(text)
            
            if command == "gemini":
                self._switch_to_gemini()
            elif command == "yolo":
                self._switch_to_yolo()
            elif command == "exit":
                self._state.mode = None
            else:
                print(f"[VOICE] Unknown command: {text}")
                unknown_prompt = self._prompts.get("unknown")
                if unknown_prompt:
                    self._audio.request_play(unknown_prompt, AudioPriority.SYSTEM)
                    
        except Exception as e:
            print(f"[VOICE] Error: {e}")
    
    def _parse_voice_command(self, text: str) -> Optional[str]:
        for command, variants in VOICE_COMMANDS.items():
            for variant in variants:
                if variant in text:
                    return command
        return None
    
    def _process_detection(self, frame):
        current_time = time.time()
        if current_time - self._state.last_detection <= CONFIG.DETECTION_INTERVAL:
            return
        
        if self._state.gemini_active or tts_main.is_playing():
            return
        
        if self._state.mode == DetectionMode.YOLO:
            desc = self._yolo.process_frame(frame)
            if desc:
                print(f"[YOLO] {desc}")
                audio_path = speak(desc, is_detection=True)
                self._audio.request_play(audio_path, AudioPriority.DETECTION)
                
        elif self._state.mode == DetectionMode.GEMINI:
            print("[GEMINI] Processing image...")
            snapshot_path = absolute_path(self._output_dir, "gemini_snapshot.jpg")
            cv2.imwrite(snapshot_path, frame)
            threading.Thread(
                target=self._gemini.process_image,
                args=(snapshot_path,),
                daemon=True
            ).start()
        
        self._state.last_detection = current_time
    
    def _cleanup(self):
        if self._camera:
            self._camera.release()
        cv2.destroyAllWindows()


def _init_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)


def main():
    load_credential_path("yolo", "yolo-key.json")
    _init_gemini()
    controller = DetectionController()
    controller.run()


if __name__ == "__main__":
    main()