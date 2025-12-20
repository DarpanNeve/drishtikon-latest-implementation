# core/logger.py
import datetime
import sys
from core.utils import ensure_dir 
from core.constants import LOG_FILE, LOG_DIR, MAX_MSG_LENGTH

# ================================================================
#  CONFIG AND SETUP
# ================================================================
try:
    ensure_dir(LOG_DIR)
except Exception as e:
    # If path setup fails, log to stderr and use a default file
    print(f"[LOGGER SETUP ERROR] Could not initialize paths: {e}", file=sys.stderr)
    LOG_FILE = "fallback_app.log"

# ================================================================
#  LOGGER FUNCTION
# ================================================================
def log(service: str = "MAIN", image_path: str = "-", message: str = "", time_taken: float | None = None):
    """
    Standardized logging function. Writes to LOG_FILE and prints to console (stdout/stderr).

    Args:
        service (str): The name of the service/module logging the event (e.g., 'TTS', 'RAG').
        image_path (str): Relevant file path (e.g., image file, audio file, or '-').
        message (str): The main log message.
        time_taken (float | None): Optional time duration for the operation.
    """

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Clean and truncate message
    msg_preview = message.replace("\n", " ").strip()
    if len(msg_preview) > MAX_MSG_LENGTH:
        msg_preview = msg_preview[:MAX_MSG_LENGTH] + "..."

    # 2. Format time string
    time_str = f"(Time: {time_taken:.3f}s)" if time_taken is not None else ""

    # 3. Construct log entry
    # Using f-string for clarity, tab-separated for easy reading/parsing
    entry = (
        f"[{timestamp}]\t"
        f"SERVICE:{service:<10}\t"  # Padded service name for alignment
        f"PATH:{image_path:<25}\t"
        f"MSG:{msg_preview}\t"
        f"{time_str}\n"
    )

    # 4. Write to file
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
        
        # Optional: Print to console for immediate visibility during development
        # sys.stdout.write(entry)
        
    except Exception as e:
        # Critical failure: log to standard error output
        print(f"[LOGGER CRITICAL ERROR] Failed to write to {LOG_FILE}: {e}", file=sys.stderr)


if __name__ == "__main__":
    print("The [LOG FILE] is located at:", LOG_FILE)
    log(service="TEST", message="Logger initialized and ready.")
    log(service="TTS", image_path="tts_001.wav", message="Audio generation successful.", time_taken=0.456)
    log(service="YOLO", image_path="image.jpg", message="Detection completed with 5 objects.", time_taken=1.87)