# core/utils.py (Raspberry Pi compatible)
import os
import sys
import time

# ================================================================
#  CUSTOM EXCEPTIONS
# ================================================================
class CredentialError(Exception):
    """Custom exception raised when a required credential file is not found."""
    pass

# ================================================================
#  BASE DIRECTORY (project root)
#  This assumes that the project root is two levels up.
# ================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def absolute_path(*paths) -> str:
    """
    Returns an absolute path by joining the project root directory with the given paths.
    """
    return os.path.join(BASE_DIR, *paths)


# ================================================================
#  CREDENTIAL LOADING HELPER (Enhanced)
# ================================================================
def load_credential_path(module_folder: str, filename: str, check_exists: bool = True) -> str:
    """
    Returns full path to: <module_folder>/cred/<filename>.

    Args:
        module_folder (str): The folder containing the 'cred' directory (e.g., 'core').
        filename (str): The name of the credential file (e.g., 'stt-key.json').
        check_exists (bool): If True, raises CredentialError if the file is not found.

    Raises:
        CredentialError: If the file is required but not found.
    """
    full_path = absolute_path(module_folder, "cred", filename)
    
    if check_exists and not os.path.exists(full_path):
        raise CredentialError(
            f"Credential file not found: {full_path}. "
            f"Please ensure it is located in the '{module_folder}/cred/' directory."
        )

    return full_path


# ================================================================
#  DIRECTORY ENSURER
# ================================================================
def ensure_dir(path: str):
    """
    Creates a folder safely on all OS.
    """
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        print(f"[UTIL] Could not create directory {path}: {e}", file=sys.stderr)


# ================================================================
#  DECORATOR TO TIME FUNCTIONS
# ================================================================
def timeit(label="function"):
    def decorator(fn):
        def inner(*args, **kwargs):
            start = time.time()
            result = fn(*args, **kwargs)
            end = time.time()
            print(f"{label} ran for {round(end - start, 2)} s...")
            return result
        return inner
    return decorator

# =================================================================
#  DECORATOR TO RETRY FUNCTION EXECUTION
# =================================================================
def retry(n):
    def decorator(fn):
        def inner(*args, **kwargs):
            last_error = None
            for i in range(1, n + 1):
                print(f"[ATTEMPT {i}]")
                try:
                    result = fn(*args, **kwargs)
                    return result
                except Exception as e:
                    last_error = e
            raise last_error
        return inner
    return decorator

# ================================================================

if __name__ == "__main__":
    try:
        print("[UTIL] BASE_DIR =", BASE_DIR)
    except CredentialError as e:
        print(f"[UTIL TEST ERROR] {e}")