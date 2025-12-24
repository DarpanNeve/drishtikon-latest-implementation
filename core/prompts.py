# core/prompts.py
# ================================================================
# CENTRALIZED PROMPT AUDIO (WAV CACHED)
# - All system prompts are generated once via speak_cached()
# - Ensures stable Pi playback (no MP3 decoding)
# ================================================================

from core.tts import speak_cached
from core.utils import absolute_path

# ---------------------------
# MAIN CONTROLLER PROMPTS
# ---------------------------

system_ready_p = speak_cached(
    "System ready. Say read, search, detect, navigate or exit.",
    "system_ready.wav"
)

opening_reading_p = speak_cached(
    "Opening reading module.",
    "opening_reading.wav"
)

opening_search_p = speak_cached(
    "Opening search module.",
    "opening_search.wav"
)

opening_detection_p = speak_cached(
    "Opening object detection module.",
    "opening_detection.wav"
)

navigation_p = speak_cached(
    "Opening navigation module.",
    "opening_navigation.wav"
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

# ---------------------------
# CAMERA PROMPTS
# ---------------------------
cap_intro_p = speak_cached(
    "Press SPACE to capture, ESC to exit.", 
    "capture_image_intro.wav"
)

switch_to_rasp_p = speak_cached(
    "Switching to Raspberry Pi camera mode.", 
    "switch_to_rasp.wav"
)

# ---------------------------
# READING AND SYSTEM PROMPTS
# ---------------------------
resume_previous_task_p = speak_cached(
    "Shall I continue with the previous reading task?",
    "resume_previous_task.wav"
)


select_file_p = speak_cached(
    "Select an image file. If you cancel, I will open the camera.",
    "select_file.wav"
)

no_file_p = speak_cached(
    "No file selected. Opening camera.",
    "no_file_open_camera.wav"
)

no_image_exit_p = speak_cached(
    "No image captured. Exiting.",
    "no_image_exit.wav"
)

processing_p = speak_cached(
    "Processing the image. Please wait.",
    "processing_wait.wav"
)

empty_page_p = speak_cached(
    "The page appears empty or unreadable.",
    "empty_page.wav"
)

no_sentences_p = speak_cached(
    "I could not extract readable sentences from this page.",
    "no_sentences.wav"
)

all_done_p = speak_cached(
    "Completed all sentences.",
    "all_sentences_done.wav"
)

exiting_module_p = speak_cached(
    "Exiting reading module.",
    "exiting_module.wav"
)

return_to_reading_p = speak_cached(
    "Returning to reading.",
    "return_to_reading.wav"
)

# -------------------------
# ASK QUERY PROMPTS
# -------------------------
ask_query_intro_p = speak_cached(
    "Please ask a question.",
    "please_ask_a_question.wav"
)

generating_answer_p = speak_cached(
    "Finding answer",
    "finding_answer.wav"
)

stopping_response_p = speak_cached(
    "Stopping response",
    "stopping_response.wav"
)

# ---------------------------
# PAUSE MENU PROMPTS
# ---------------------------
no_content_yet_p = speak_cached(
    "No content has been read yet.",
    "no_content_yet.wav"
)

generating_summary_p = speak_cached(
    "Generating summary.",
    "generating_summary.wav"
)

stopping_summary_p = speak_cached(
    "Stopping summary.",
    "stopping_summary.wav"
)

back_pause_menu_p = speak_cached(
    "Back to pause menu.",
    "back_pause_menu.wav"
)

# ---------------------------
# VOICE CONTROL PROMPTS
# ---------------------------
vc_intro_p = speak_cached(
    "Voice control. Say summary, resume, doubt, search or quit.",
    "voice_intro.wav"
)

vc_retry_p = speak_cached(
    "I did not catch that. Please try again.",
    "retry_voice.wav"
)

vc_unknown_p = speak_cached(
    "Unknown command. Please say summary, resume, or quit.",
    "unknown_command.wav"
)

vc_back_p = speak_cached(
    "Back to voice control.",
    "back_voice.wav"
)

# ---------------------------
# RAG SEARCH PROMPTS
# ---------------------------
enter_rag_mode_p = speak_cached(
    "This is RAG search. Ask your query",
    "rag_intro.wav"
)
generating_rag_answer_p = speak_cached(
    "Searching...",
    "generating_rag_answer.wav"
)

# ---------------------------
# DETECT PROMPTS
# ---------------------------
exiting_detection_module_p = speak_cached(
    "Exiting detection module.",
    "exiting_detection_module.wav"
)

# ---------------------------
# NAVIGATE PROMPTS
# ---------------------------
navigation_src_p = speak_cached(
    "Please tell me your current location.",
    "source_prompt.wav"
)

navigation_dest_p = speak_cached(
    "Please tell me your destination.",
    "destination_prompt.wav"
)

navigation_src_err_p = speak_cached(
    "I did not hear the current location.",
    "source_error.wav"
)

navigation_dest_err_p = speak_cached(
    "I did not hear the destination.",
    "destination_error.wav"
)

navigation_stop_p = speak_cached(
    "Navigation stopped.",
    "nav_stopped.wav"
)

# ---------------------------
# BEEPS (non‑TTS files)
# ---------------------------
pause_beep = absolute_path("sounds", "pause_beep.wav")
resume_beep = absolute_path("sounds", "resume_beep.wav")

# ---------------------------
# FILLER MUSIC
# ---------------------------
filler_music = absolute_path("test", "reading", "grants_opus.wav")
filler_music_summary = absolute_path("test", "reading", "grants_new_etude.wav")
fractals = absolute_path("test", "reading", "fractals.wav")
