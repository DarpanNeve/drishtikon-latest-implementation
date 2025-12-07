# core/state.py
# ================================================================
# READING MODULE PERSISTENCE (Commit 1)
# - Handles saving, loading, clearing reading progress
# - Stores: sentences + current_index
# ================================================================

import os
import pickle
from core.utils import absolute_path, ensure_dir

# Directory for internal persistence
STATE_DIR = absolute_path("results", "state")
ensure_dir(STATE_DIR)

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
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
            print("[STATE] Cleared saved reading progress.")
        except:
            print("[STATE] ERROR: Could not delete state file.")
