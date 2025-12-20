from core.utils import absolute_path

# core.logger
LOG_DIR = absolute_path("results")
LOG_FILE = absolute_path("results", "app.log")
MAX_MSG_LENGTH = 300 # Max characters to display from the message in the log file

# core.state
STATE_DIR = absolute_path("results", "state")
STATE_FILE = absolute_path(STATE_DIR, "reading_state.pkl") # State file for reading module
SENTENCE_CACHE_DIR = absolute_path("results", "prompt_cache", "sentences")
SUMMARY_CACHE_DIR = absolute_path("results", "prompt_cache", "summaries")

# core.tts
AUDIO_DIR = absolute_path("results", "audio_outputs")
PROMPT_CACHE_DIR = absolute_path("results", "prompt_cache")

# core.stt
# MICROPHONE SETTINGS (Google recommended)
SAMPLE_RATE = 16000
CHANNELS = 1

# reading.read
RESULTS_DIR = absolute_path("results")
READING_INPUTS_DIR = absolute_path("results", "reading_inputs")

# reading.rag
# We use a constant display name for persistence across runs.
STORE_DISPLAY_NAME = "reading-store-display"
