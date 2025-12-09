import os
import sys
import time
from dotenv import load_dotenv
import google.generativeai as genai
from core.tts import speak
from core.logger import log

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.utils import absolute_path, ensure_dir
from core.logger import log

load_dotenv()

# ================================================================
# GEMINI CONFIG
# ================================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")  # fallback

if not GEMINI_API_KEY:
    raise ValueError("Gemini API key missing. Set GEMINI_API_KEY in .env")

genai.configure(api_key=GEMINI_API_KEY)


# ================================================================
# QUERY FUNCTION
# ================================================================
def answer_query(text: str, question: str) -> str:
    """
    Answers from a block of text using Gemini.
    Returns answer string.
    """

    if not text or len(text.strip()) == 0:
        return "No text provided."

    prompt = f"""
    You are a query resolver. 
    The user has asked, {question}.
    Answer the question clearly and concisely
    by referring the following text only, in less than 50 words.

    TEXT:
    \"\"\"{text}\"\"\"
    """

    t0 = time.time()
    model = genai.GenerativeModel(GEMINI_MODEL)

    try:
        response = model.generate_content(prompt)
    except Exception as e:
        log("ANSWER", "-", f"Gemini error: {e}")
        speak(f"Gemini error: {e}")
        return f"Gemini error: {e}"

    answer_text = getattr(response, "text", "")

    duration = round(time.time() - t0, 2)
    log("ANSWER", "-", f"{len(answer_text)} chars in {duration}s")

    return answer_text


# ================================================================
# CLI MODE (python query.py "text here")
# ================================================================
if __name__ == "__main__":

    if len(sys.argv) < 3:
        print("\nUsage:")
        print("   python query.py \"your question here\" \"text:\"\"your text here\"")
        print("Or import answer_query() inside another script.\n")
        sys.exit(0)

    input_question, input_text = " ".join(sys.argv[1:]).split("text:", 1)
    output = answer_query(input_text, input_question)

    print("\n===== ANSWER =====\n")
    print(output)
    print("\n===================\n")
