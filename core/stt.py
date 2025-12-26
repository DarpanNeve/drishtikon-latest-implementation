# stt.py — Raspberry Pi version

import os
import queue
import threading
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
        language_code="en-IN",
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

SILENCE_THRESHOLD = 3          # seconds
SILENCE_RMS_THRESHOLD = 100    # tune per mic/environment

# Shared state
audio_queue = queue.Queue()
stop_event = threading.Event()
last_speech_time = time.time()

# ------------------------------------------------------------
# Audio callback (runs in sounddevice thread)
# ------------------------------------------------------------
def audio_callback(indata, frames, time_info, status):
    global last_speech_time

    if status:
        print(status)

    # Push raw audio for Google
    audio_queue.put(bytes(indata))

    # ---- LOCAL SILENCE / VOICE DETECTION ----
    rms = np.sqrt(np.mean(indata.astype(np.float32) ** 2))
    if rms > SILENCE_RMS_THRESHOLD:
        last_speech_time = time.time()


# ------------------------------------------------------------
# Main listening function
# ------------------------------------------------------------
def listen_continuous():
    global last_speech_time

    stop_event.clear()
    last_speech_time = time.time()
    full_transcript = []

    # --------------------------------------------------------
    # Generator feeding Google (MUST terminate on stop_event)
    # --------------------------------------------------------
    def request_generator():
        while True:
            if stop_event.is_set():
                return  # HARD STOP: closes gRPC stream

            try:
                chunk = audio_queue.get(timeout=0.1)
                yield speech.StreamingRecognizeRequest(
                    audio_content=chunk
                )
            except queue.Empty:
                continue

    # --------------------------------------------------------
    # Google response processing thread
    # --------------------------------------------------------
    def response_loop(responses):
        try:
            for response in responses:
                if stop_event.is_set():
                    break

                if not response.results:
                    continue

                result = response.results[0]
                transcript = result.alternatives[0].transcript

                if not result.is_final:
                    print(f"[STT] Live: {transcript}", end="\r")
                else:
                    print(f"\n[STT] Confirmed: {transcript}")
                    full_transcript.append(transcript)

        except Exception as e:
            if not stop_event.is_set():
                print(f"[STT] Response Error: {e}")

    # --------------------------------------------------------
    # Start microphone stream
    # --------------------------------------------------------
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        callback=audio_callback,
    ):
        print(f"[STT] Listening... (auto-stop after {SILENCE_THRESHOLD}s silence)")

        # Google config
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=SAMPLE_RATE,
            language_code="en-IN",
            enable_automatic_punctuation=True,
        )

        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True,
            single_utterance=True,  # optional but recommended
        )

        responses = speech_client.streaming_recognize(
            config=streaming_config,
            requests=request_generator(),
        )

        # Run Google response loop in background
        t = threading.Thread(target=response_loop, args=(responses,), daemon=True)
        t.start()

        # ----------------------------------------------------
        # MONITOR LOOP (controls silence timeout)
        # ----------------------------------------------------
        while not stop_event.is_set():
            time.sleep(0.1)
            if time.time() - last_speech_time > SILENCE_THRESHOLD:
                print(f"\n[STT] {SILENCE_THRESHOLD}s silence detected. Closing...")
                stop_event.set()

        # Give response thread time to exit cleanly
        t.join(timeout=1.0)

    return " ".join(full_transcript)