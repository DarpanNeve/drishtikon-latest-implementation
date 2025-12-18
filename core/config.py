import os
from dotenv import load_dotenv
import google.generativeai as genai
from google.oauth2 import service_account
from google.cloud import speech
from google.cloud import texttospeech

from core.utils import load_credential_path

load_dotenv()
# ================================================================
# GEMINI CONFIG
# ================================================================
def init_gemini():
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise ValueError("Gemini API key missing. Set GEMINI_API_KEY in .env")

    genai.configure(api_key=GEMINI_API_KEY)

# ================================================================
# GOOGLE STT CONFIG
# ================================================================
def init_stt(CRED_PATH):
    if not os.path.exists(CRED_PATH):
        print(f"[STT] ERROR: Credential file does not exist: {CRED_PATH}")
        return

    try:
        creds = service_account.Credentials.from_service_account_file(CRED_PATH)
        speech_client = speech.SpeechClient(credentials=creds)
        print("[STT] Google Speech client initialized.")

    except Exception as e:
        print(f"[STT] ERROR loading STT credentials: {e}")
        speech_client = None
    
    return speech_client

# ================================================================
# GOOGLE TTSCONFIG
# ================================================================
def init_tts(CRED_PATH):
    """Initialize Google Cloud TTS client."""
    global tts_client
    try:
        creds = service_account.Credentials.from_service_account_file(CRED_PATH)
        tts_client = texttospeech.TextToSpeechClient(credentials=creds)
        print("[TTS] Google TTS initialized.")
    except Exception as e:
        print(f"[TTS] ERROR loading credentials: {e}")
        tts_client = None

    return tts_client
