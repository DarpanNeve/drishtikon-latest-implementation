# core/state.py
# ================================================================
# READING MODULE PERSISTENCE (Commit 1)
# - Handles saving, loading, clearing reading progress
# - Stores: sentences + current_index
# ================================================================

import os
import pickle
from core.utils import absolute_path, ensure_dir

# Directories for internal persistence
STATE_DIR = absolute_path("results", "state")
ensure_dir(STATE_DIR)
SENTENCE_CACHE_DIR = absolute_path("results", "prompt_cache", "sentences")
ensure_dir(SENTENCE_CACHE_DIR)
SUMMARY_CACHE_DIR = absolute_path("results", "prompt_cache", "summaries")
ensure_dir(SUMMARY_CACHE_DIR)

# Single state file for reading module
STATE_FILE = os.path.join(STATE_DIR, "reading_state.pkl")

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
def clear_state():
    """Remove saved reading progress."""
    ensure_dir(SENTENCE_CACHE_DIR)
    ensure_dir(SUMMARY_CACHE_DIR)
    try:
        for file in os.listdir(SENTENCE_CACHE_DIR):
            os.remove(absolute_path(SENTENCE_CACHE_DIR, file))
    except:
            print("[SENTENCE CACHE] ERROR: Could not delete sentence cache.")
    try:
        for file in os.listdir(SUMMARY_CACHE_DIR):
            os.remove(absolute_path(SUMMARY_CACHE_DIR, file))
    except:
            print("[SUMMARY CACHE] ERROR: Could not delete summary cache.")
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
            print("[STATE] Cleared saved reading progress.")
        except:
            print("[STATE] ERROR: Could not delete state file.")
