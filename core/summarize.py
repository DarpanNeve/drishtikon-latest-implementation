import os
import sys
import time
from dotenv import load_dotenv
import google.generativeai as genai
from core.config import init_gemini
from core.tts import speak
from core.logger import log
from core.tts_player import tts_main
from core.prompts import filler_music_summary
from core.logger import log

# ================================================================
# GEMINI CONFIG
# ================================================================
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
init_gemini()

# ================================================================
# SUMMARY FUNCTION
# ================================================================
def summarize(text: str) -> str:
    """
    Summarizes a block of text using Gemini.
    Returns summary string.
    """

    if not text or len(text.strip()) == 0:
        return "No text provided."
    
    tts_main.play(filler_music_summary)
    prompt = f"""
    You are an AI summarizer. Summarize the following text clearly and concisely
    without changing the meaning ({int(len(text) / 4)} words max):

    TEXT:
    \"\"\"{text}\"\"\"
    """

    t0 = time.time()
    model = genai.GenerativeModel(GEMINI_MODEL)

    try:
        response = model.generate_content(prompt)
        tts_main.stop()
    except Exception as e:
        log("SUMMARY", "-", f"Gemini error: {e}")
        speak(f"Gemini error: {e}")
        return f"Gemini error: {e}"

    summary_text = getattr(response, "text", "")

    duration = round(time.time() - t0, 2)
    log("SUMMARY", "-", f"{len(summary_text)} chars in {duration}s")

    return summary_text


# ================================================================
# CLI MODE (python summarize.py "text here")
# ================================================================
if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("\nUsage:")
        print("   python -m core.summarize \"your text here\"")
        print("Or import summarize() inside another script.\n")
        sys.exit(0)

    input_text = " ".join(sys.argv[1:])
    output = summarize(input_text)

    print("\n===== SUMMARY =====\n")
    print(output)
    print("\n===================\n")
