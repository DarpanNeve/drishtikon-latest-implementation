# core/state.py
# ================================================================
# READING MODULE PERSISTENCE (Commit 1)
# - Handles saving, loading, clearing reading progress
# - Stores: sentences + current_index
# ================================================================

import os
import pickle
from core.utils import absolute_path, ensure_dir
from core.constants import STATE_DIR, STATE_FILE, SENTENCE_CACHE_DIR, SUMMARY_CACHE_DIR

# Directories for internal persistence
ensure_dir(STATE_DIR)
ensure_dir(SENTENCE_CACHE_DIR)
ensure_dir(SUMMARY_CACHE_DIR)

# ------------------------------------------------------------
# Save state to disk
# ------------------------------------------------------------
def save_state(task_state):
    """
    task_state = {
        'sentences': [...],
        'current_index': int
    }
    """
    try:
        with open(STATE_FILE, "wb") as f:
            pickle.dump(task_state, f)
        print("[STATE] Saved reading progress.")
    except Exception as e:
        print(f"[STATE] ERROR saving state: {e}")


# ------------------------------------------------------------
# Load state from disk
# ------------------------------------------------------------
def load_state():
    """
    Returns:
      dict with keys 'sentences' and 'current_index'
      OR None if no state exists.
    """
    if not os.path.exists(STATE_FILE):
        return None

    try:
        with open(STATE_FILE, "rb") as f:
            state = pickle.load(f)
        print("[STATE] Loaded existing reading progress.")
        return state
    except Exception as e:
        print(f"[STATE] ERROR loading state: {e}")
        return None


# ------------------------------------------------------------
# Delete save file when task is finished
# ------------------------------------------------------------
def _clear_dir(dir_path: str, label: str):
    if not os.path.exists(dir_path):
        return

    try:
        for name in os.listdir(dir_path):
            path = absolute_path(dir_path, name)
            if os.path.isfile(path):
                os.remove(path)
    except OSError as e:
        print(f"[{label}] ERROR: Could not clear cache ({e}).")


def clear_state():
    """Remove saved reading progress."""

    _clear_dir(SENTENCE_CACHE_DIR, "SENTENCE CACHE")
    _clear_dir(SUMMARY_CACHE_DIR, "SUMMARY CACHE")

    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
            print("[STATE] Cleared saved reading progress.")
        except OSError as e:
            print(f"[STATE] ERROR: Could not delete state file ({e}).")

