# stt.py — Raspberry Pi version

import os
import queue
import time
import numpy as np
import sounddevice as sd
from google.cloud import speech

from core.config import init_stt
from core.constants import CHANNELS, SAMPLE_RATE
from core.utils import load_credential_path
from core.logger import log

# ================================================================
#  GOOGLE CREDENTIALS
# ================================================================
CRED_PATH = load_credential_path("core", "stt-key.json")
speech_client = init_stt(CRED_PATH)

# ================================================================
#  AUDIO RECORDING (Raspberry Pi Safe)
# ================================================================
def record_audio(duration=5):
    """
    Records audio using ALSA (sounddevice).
    Returns raw PCM bytes.
    """

    print(f"[STT] Recording {duration}s...")

    try:
        audio = sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16"
        )
        sd.wait()

    except Exception as e:
        log("STT", "-", f"Microphone error: {e}")
        print(f"[STT] Microphone error: {e}")
        return None

    print("[STT] Recording complete.")
    return audio.tobytes()

# ================================================================
#  GOOGLE SPEECH-TO-TEXT
# ================================================================
def speech_to_text(audio_bytes):
    """
    Sends audio to Google STT → returns transcript.
    """

    if not speech_client:
        print("[STT] Client not initialized.")
        return None

    audio = speech.RecognitionAudio(content=audio_bytes)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=SAMPLE_RATE,
        language_code="en-US",
        enable_automatic_punctuation=True
    )

    try:
        response = speech_client.recognize(config=config, audio=audio)

    except Exception as e:
        log("STT", "-", f"Google STT error: {e}")
        print(f"[STT] Google STT error: {e}")
        return None

    if not response.results:
        return None

    return response.results[0].alternatives[0].transcript

# ================================================================
#  PUBLIC LISTEN FUNCTION
# ================================================================
def listen(duration=5):
    """
    High-level function:
    - Records audio
    - Sends to Google STT
    - Logs time taken
    """

    t0 = time.time()

    audio_bytes = record_audio(duration)
    if not audio_bytes:
        return None

    text = speech_to_text(audio_bytes)

    t1 = time.time()

    log("STT", "-", f"Heard '{text}'" if text else "No speech detected", round(t1 - t0, 2))

    if text:
        print("[STT] Heard:", text)
    else:
        print("[STT] No speech detected.")

    return text

# ================================================================
#  GOOGLE SPEECH-TO-TEXT (STREAMING)
# ================================================================
import time
import queue
import threading
import sounddevice as sd
from google.cloud import speech

SILENCE_THRESHOLD = 3

# Shared state
audio_queue = queue.Queue()
stop_event = threading.Event()
last_speech_time = time.time()

def audio_callback(indata, frames, time_info, status):
    if status:
        print(status)
    audio_queue.put(bytes(indata))

def listen_continuous():
    global last_speech_time
    stop_event.clear()
    last_speech_time = time.time()
    full_transcript = []

    def request_generator():
        # This keeps feeding Google until we set the stop_event
        while not stop_event.is_set():
            try:
                chunk = audio_queue.get(timeout=0.1)
                yield speech.StreamingRecognizeRequest(audio_content=chunk)
            except queue.Empty:
                continue

    def response_loop(responses):
        global last_speech_time
        try:
            for response in responses:
                if stop_event.is_set():
                    break
                if not response.results:
                    continue

                result = response.results[0]
                transcript = result.alternatives[0].transcript
                
                # HEARTBEAT: Update timer whenever Google says anything
                last_speech_time = time.time()

                if not result.is_final:
                    print(f"[STT] Live: {transcript}", end="\r")
                else:
                    print(f"\n[STT] Confirmed: {transcript}")
                    full_transcript.append(transcript)
        except Exception as e:
            if not stop_event.is_set():
                print(f"[STT] Response Error: {e}")

    # 1. Start Microphone
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, 
                        dtype='int16', callback=audio_callback):
        
        print(f"[STT] Listening... (Auto-stop after {SILENCE_THRESHOLD}s)")

        # 2. Setup Google Stream
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=SAMPLE_RATE,
            language_code="en-US",
            enable_automatic_punctuation=True
        )
        streaming_config = speech.StreamingRecognitionConfig(
            config=config, interim_results=True, single_utterance=False
        )

        responses = speech_client.streaming_recognize(
            config=streaming_config, 
            requests=request_generator()
        )

        # 3. Run the response processor in a background thread
        t = threading.Thread(target=response_loop, args=(responses,))
        t.daemon = True
        t.start()

        # 4. MONITOR LOOP (Main Thread)
        # This runs constantly and doesn't wait for Google
        while not stop_event.is_set():
            time.sleep(0.1) 
            if time.time() - last_speech_time > SILENCE_THRESHOLD:
                print(f"\n[STT] {SILENCE_THRESHOLD}s silence. Closing...")
                stop_event.set() # Tells the generator and response loop to exit

        # Wait for thread to clean up
        t.join(timeout=1.0)

    return " ".join(full_transcript)