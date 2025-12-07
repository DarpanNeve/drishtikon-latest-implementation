# core/prompts_main_controller.py
# ================================================================
# PRE‑CACHED TTS PROMPTS FOR MAIN CONTROLLER
# ================================================================

from core.tts import speak_cached
from core.utils import absolute_path, ensure_dir

# Ensure prompt cache directory exists
PROMPT_CACHE_DIR = absolute_path("results", "prompt_cache")
ensure_dir(PROMPT_CACHE_DIR)

# ================================================================
# MAIN CONTROLLER PROMPTS (WAV Cached)
# ================================================================

system_ready_p = speak_cached(
    "System ready. Say read, detect, or exit.",
    "system_ready.wav"
)

opening_reading_p = speak_cached(
    "Opening reading module.",
    "opening_reading.wav"
)

opening_detection_p = speak_cached(
    "Opening object detection module.",
    "opening_detection.wav"
)

goodbye_p = speak_cached(
    "Goodbye.",
    "goodbye.wav"
)

did_not_understand_p = speak_cached(
    "I did not understand.",
    "did_not_understand.wav"
)

emergency_stop_p = speak_cached(
    "Emergency stop activated.",
    "emergency_stop.wav"
)

module_not_found_p = speak_cached(
    "Module not found.",
    "module_not_found.wav"
)

launch_error_p = speak_cached(
    "Unable to launch module.",
    "launch_error.wav"
)
