import os
import sys
import subprocess
import cv2
import time
import datetime
import threading
import tkinter as tk
from tkinter import filedialog
from PIL import Image
import io
from dotenv import load_dotenv
import google.generativeai as genai
# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from core.utils import absolute_path, ensure_dir, load_credential_path
from core.tts import speak
from core.stt_commands import listen_for_command
from core.tts_player import tts_main
from core.logger import log
from core.text_utils import split_into_sentences
from core.summarize import summarize
from core.query import answer_query
from core.prompts import *
from core.state import *
from core.playback_controls import play, non_blocking_play, read_key_nonblocking
from reading.rag import upload_text_to_store, rag_query_voice
load_dotenv()
# ================================================================
#  CREDENTIALS
# ================================================================
CRED_PATH = load_credential_path("reading", "reading-key.json")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
# ================================================================
# HELPERS
# ================================================================
def ensure_results_dir():
    ensure_dir(absolute_path("results"))
    ensure_dir(absolute_path("results", "reading_outputs"))
    ensure_dir(absolute_path("results", "prompt_cache"))
    ensure_dir(absolute_path("results", "prompt_cache", "sentences"))

PROMPT_CACHE_DIR = absolute_path("results", "prompt_cache")
AUDIO_OUTPUT_DIR = absolute_path("results", "audio_outputs")
SENTENCE_CACHE_DIR = absolute_path("results", "prompt_cache", "sentences")
# ================================================================
# IMAGE OPTIMIZATION
# ================================================================
def optimize_image(image_path):
    """
    Resize + compress image for faster Gemini processing.
    """
    img = Image.open(image_path)
    if img.mode == "RGBA":
        img = img.convert("RGB")
    img.thumbnail((1800, 1800))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()
# ================================================================
# GEMINI OCR
# ================================================================
def gemini_read(image_path, prompt):
    """
    Run Gemini OCR + prompt on the image.
    """
    if not GEMINI_API_KEY or not GEMINI_MODEL:
        return "Gemini not configured.", 0
    optimized_bytes = optimize_image(image_path)
    model = genai.GenerativeModel(GEMINI_MODEL)
    final_text = []
    start = time.time()
    response = model.generate_content(
        [
            {"mime_type": "image/jpeg", "data": optimized_bytes},
            prompt,
        ]
    )
    text = getattr(response, "text", "")
    duration = round(time.time() - start, 2)
    return text, duration
# ================================================================
# FILE PICKER
# ================================================================
def choose_file():
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    fp = filedialog.askopenfilename(
        title="Select an image file",
        filetypes=[
            ("Image Files", "*.jpg *.jpeg *.png *.bmp *.webp"),
            ("All Files", "*.*"),
        ],
    )
    root.destroy()
    if not fp:
        return None
    # Save copy to results
    img = cv2.imread(fp)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = absolute_path("results", "reading_outputs", f"capture_{ts}.jpg")
    cv2.imwrite(save_path, img)
    return save_path
# ================================================================
# CAMERA CAPTURE - Raspberry Pi compatible
# ================================================================
def capture_with_libcamera():
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = absolute_path("results", "reading_outputs", f"capture_{ts}.jpg")
    cmd = ["libcamera-still", "-o", out_path, "--immediate", "--timeout", "1"]
    try:
        subprocess.run(cmd, check=True)
        return out_path
    except Exception:
        return None
def capture_image():
    # Try OpenCV camera first (legacy mode)
    cam = cv2.VideoCapture(0)
    if cam.isOpened():
        play(tts_main, cap_intro_p)
        while True:
            ret, frame = cam.read()
            if not ret:
                continue
            cv2.imshow("Camera Capture - Press SPACE", frame)
            key = cv2.waitKey(1)
            if key == 32:  # SPACE
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                path = absolute_path("results", "reading_outputs", f"capture_{ts}.jpg")
                cv2.imwrite(path, frame)
                cam.release()
                cv2.destroyAllWindows()
                return path
            elif key == 27:  # ESC
                break
        cam.release()
        cv2.destroyAllWindows()
    # If OpenCV fails → fallback to libcamera
    play(tts_main, switch_to_rasp_p)
    return capture_with_libcamera()
# ================================================================
# MAIN
# ================================================================
def main():
    ensure_results_dir()
    for file in os.listdir(SENTENCE_CACHE_DIR):
        os.remove(absolute_path(SENTENCE_CACHE_DIR, file))

    for file in os.listdir(AUDIO_OUTPUT_DIR):
        os.remove(absolute_path(AUDIO_OUTPUT_DIR, file))
    # ---------------------------------------------------------
    # CHECK FOR EXISTING READING STATE (resume_mode)
    # ---------------------------------------------------------
    state = load_state()
    resume_mode = False
    if state:
        # Ask if want to continue the previous reading task
        play(tts_main, resume_previous_task_p)
        print("\nPrevious reading task found.")
        print("Press 'y' to continue or any other key to start a new task.")
        choice = sys.stdin.readline().strip().lower()
        if choice == "y":
            print("[STATE] Resuming saved reading task...")
            sentences = state["sentences"]
            current_index = state["current_index"]
            read_so_far = sentences[:current_index]
            resume_mode = True
        else:
            print("[STATE] Discarding saved task...")
            clear_state()
            resume_mode = False
    # ---------------------------------------------------------
    # NEW TASK FLOW (file select + OCR + chunking)
    # ---------------------------------------------------------
    if not resume_mode:
        # INTRO
        play(tts_main, select_file_p)
        # STEP 1 — Select file
        img_path = choose_file()
        if not img_path:
            play(tts_main, no_file_p)
            img_path = capture_image()
        if not img_path:
            play(tts_main, no_image_exit_p)
            return
        # OCR PROMPT
        play(tts_main, processing_p)
        refinement_prompt = f"""
        Task: Act as a better version of the Google Vision OCR.
        If the image contains text (like from a book), include the complete, UNSUMMARIZED text content.
        Summarize only contextual elements like book title, chapter, or page numbers separately from the quoted text. 
        If the content is medical, issue a clear alarm.
        If no text is found, say "NO TEXT FOUND" and SUMMARIZE the visual (25 WORDS ONLY).
        Do NOT use headers, bullet points, or lists in your final response.
        """ 
        text, duration = gemini_read(img_path, refinement_prompt)
        log("READING", img_path, f"{len(text)} chars", duration)
        # After OCR:
        def helper_upload_text_to_store(text):
            store_name = upload_text_to_store(text)
            if not store_name:
                print("\nCould not perform RAG query due to upload failure.")

        threading.Thread(target=helper_upload_text_to_store, args=(text, ), daemon=True).start()
        print("\n===== OCR RESULT =====\n")
        print(text)
        print("\n=======================\n")
        # if not text.strip():
        #     play(tts_main, empty_page_p)
        #     return
        # CHUNKING
        # sentences = ['After walking for many hours along an intricate series of paths\nand grassy trails, the two travellers came upon a lush, green\nvalley.', 'On one side of the valley, the snow-capped Himalayas\noffered their protection, like weather-beaten soldiers guarding\nthe place where their generals rested.', 'On the other, a thick forest\nof pine trees sprouted, a perfectly natural tribute to this\nenchanting fantasyland.', 'The sage looked at Julian and smiled gently.', '"Welcome to the\nNirvana of Sivana.', '"\n\nThe two then descended along another less-travelled way and\ninto the thick forest that formed the floor of the valley.', 'The smell\nof pine and sandalwood wafted through the cool, crisp mountain\nair.', 'Julian, now barefoot to ease his aching feet, felt the damp moss\nunder his toes.', 'He was surprised to see richly colored orchids and\na host of other lovely flowers dancing among the trees, as if\nrejoicing in the beauty and splendor of this tiny slice of Heaven.', 'In the distance, Julian could hear gentle voices, soft and\nsoothing to the ear.', 'He continued to follow the sage without\nmaking a sound.', 'After walking for about fifteen more minutes, the\n24\n\nCHAPTER FOUR\n\nA Magical Meeting with\nthe Sages of Sivana\n\ntwo men reached a clearing.', 'Before him was a sight that even the\nworldly wise and rarely surprised Julian Mantle could never have\nimagined — a small village made solely out of what appeared to be\nroses.', 'At the center of the village was a tiny temple, the kind\nJulian had seen on his trips to Thailand and Nepal, but this temple\nwas made of red, white and pink flowers, held together with long\nstrands of multi-colored string and twigs.', 'The little huts that\ndotted the remaining space appeared to be the austere homes of\nthe sages.', 'These were also made of roses.', 'Julian was speechless.', 'As for the monks who inhabited the village, those he could see\nlooked like Julian’s travelling companion, who now revealed that\nhis name was Yogi Raman and the leader of this group.', 'The citizens of this\nsage of Sivana and the leader of this group.', 'The citizens of this\ndreamlike colony looked astonishingly youthful and moved with\npoise and purpose.', 'None of them spoke, choosing instead to\nrespect the tranquility of this place by performing their tasks in\nsilence.', 'The men, who appeared to number only about ten, wore the\nsame red-robed uniform as Yogi Raman and smiled serenely at\nJulian as he entered their village.', 'Each of them looked calm,\nhealthy and deeply contented.', 'It was as if the tensions that plague\nso many of us in our modern world had sensed that they were not\nwelcome at this summit of serenity and moved on to more inviting\nprospects.', 'Though it had been many years since there had been a\nnew face among them, these men were controlled in their\nreception, offering a simple bow as their greeting to this visitor\nwho had travelled so far to find them.', 'The women were equally impressive.', 'In their flowing pink silk\nsaris and with white lotusess adorning their jet black hair, they\nmoved busily through the village with exceptional agility.', '25\n\nThe Monk Who Sold His Ferrari']
        sentences = split_into_sentences(text)
        sentences.append("We have reached the end!")
        # print(sentences)
        if not sentences:
            play(tts_main, no_sentences_p)
            return
        read_so_far = []
        current_index = 0
    # ---------------------------------------------------------
    # CHUNK LOOP (supports resume_mode)
    # ---------------------------------------------------------
    print("\n===== CHUNKED READING (PAUSE + SUMMARY + VOICE MODE) =====\n")
    if resume_mode:
        print(f"[RESUME] Continuing from sentence {current_index + 1} of {len(sentences)}")
    # Summary cache vars
    last_summary_audio = None
    last_summary_index = -1
    while current_index < len(sentences):
        sentence = sentences[current_index]
        print(f"[READ] {current_index + 1}/{len(sentences)} → {sentence}")
        audio_file_name = f"sentence_0{current_index}.wav" if current_index < 10 else f"sentence_{current_index}.wav"
        sentence_audio = speak_cached(sentence, absolute_path(SENTENCE_CACHE_DIR, audio_file_name))
        tts_main.play(sentence_audio)
        # -----------------------------
        # PLAYBACK MONITOR
        # -----------------------------
        while True:
            if not tts_main.is_playing():
                print("\n_________________________________\n")
                break
            if current_index + 1 == len(sentences):
                key = "p"
                current_index += 1
            # Non-blocking keypress
            else:
                key = read_key_nonblocking()
        # =====================================================
        # (p) — PAUSE
        # =====================================================
            if key == "p":
                play(tts_main, pause_beep)
                # ----- PAUSE MENU -----
                while True:
                    print("\nPaused. Options:")
                    print(" p = resume this part")
                    print(" m = summarize what has been read so far")
                    print(" q = quit reading module")
                    print(" x = ask a query")
                    sys.stdout.flush()
                    choice = sys.stdin.readline().strip().lower()
                    # RESUME → restart sentence
                    if choice == "p":
                        play(tts_main, resume_beep)
                        sentence_audio = speak_cached(sentence_audio, absolute_path(SENTENCE_CACHE_DIR, audio_file_name))
                        print("[PATH]", sentence_audio)
                        tts_main.play(sentence_audio)
                        break
                    # QUERY RESOLUTION
                    elif choice == "x":
                        # Announce query mode
                        play(tts_main, ask_query_intro_p)
                        # Listen for user's voice question
                        question = listen_for_command(is_question=True)
                        if question is None or not question.strip():
                            # No question → back to voice control
                            play(tts_main, vc_back_p)
                            # time.sleep(1)
                            continue   # <── stays inside voice mode
                        # Generate answer
                        play(tts_main, generating_answer_p)
                        answer = answer_query(" ".join(read_so_far), question)
                        print("\n========ANSWER=======\n")
                        print(answer)
                        if not answer.strip():
                            play(tts_main, back_pause_menu_p)
                            continue
                        # Speak the answer
                        answer_audio = speak(answer)
                        non_blocking_play(tts_main, answer_audio, "Press 's' to stop response", stopping_response_p)
                        # Finished answer → back to voice mode
                        play(tts_main, back_pause_menu_p)
                        continue  # <── stay inside voice mode
                    # SUMMARY
                    elif choice == "m":
                        if not read_so_far:
                            play(tts_main, no_content_yet_p)
                            play(tts_main, back_pause_menu_p)
                            continue
                        # Reuse cached summary if applicable
                        if last_summary_audio is not None and last_summary_index == current_index:
                            summary_audio = last_summary_audio
                        else:
                            play(tts_main, generating_summary_p)
                            summary_text = summarize(" ".join(read_so_far))
                            summary_audio = speak(summary_text)
                            print("\n========SUMMARY=======\n")
                            print(summary_text)
                            last_summary_audio = summary_audio
                            last_summary_index = current_index
                        non_blocking_play(tts_main, summary_audio, "Press 's' to stop summary", stopping_summary_p)
                        play(tts_main, back_pause_menu_p)
                        continue
                    # QUIT
                    elif choice == "q":
                        # SAVE STATE BEFORE EXIT
                        if sentences and 0 <= current_index < len(sentences):
                            task_state = {
                                "sentences": sentences,
                                "current_index": current_index,
                            }
                            save_state(task_state)
                        play(tts_main, exiting_module_p)
                        return
                    else:
                        print("Invalid option.")
                        continue
        # =====================================================
        # (v) — VOICE MODE
        # =====================================================
            elif key == "v":
                play(tts_main, pause_beep)
                play(tts_main, vc_intro_p)
                # ----- PAUSE MENU -----
                while True:
                    choice = listen_for_command()
                    # RESUME → restart sentence
                    if choice is None or choice == "p":
                        play(tts_main, resume_beep)
                        sentence_audio = speak_cached(sentence, absolute_path(SENTENCE_CACHE_DIR, audio_file_name))
                        print("[PATH]", sentence_audio)
                        tts_main.play(sentence_audio)
                        break
                    # RAG SEARCH
                    elif choice == "r":
                        # Announce rag mode
                        play(tts_main, ask_query_intro_p)
                        # Listen for user's voice question
                        question = listen_for_command(is_question=True)
                        if question is None or not question.strip():
                            # No question → back to voice mode
                            play(tts_main, vc_back_p)
                            # time.sleep(1)
                            continue
                        # Generate RAG answer
                        play(tts_main, generating_answer_p)
                        # --- RAG CALL ---
                        answer = rag_query_voice(question)
                        print("\n========RAG ANSWER=======\n")
                        print(answer)
                        if not answer.strip() or answer.startswith("RAG Query Error"):
                            play(tts_main, vc_back_p)
                            # time.sleep(1)
                            continue
                        # Speak the answer
                        answer_audio = speak(answer)
                        non_blocking_play(tts_main, answer_audio, "Press 's' to stop response", stopping_response_p)
                        # Finished answer → back to voice mode
                        play(tts_main, vc_back_p)
                        # time.sleep(1)
                        continue  # <── stay inside voice mode
                    # SUMMARY
                    elif choice == "m":
                        if not read_so_far:
                            play(tts_main, no_content_yet_p)
                            continue
                        # Reuse cached summary if applicable
                        if last_summary_audio is not None and last_summary_index == current_index:
                            summary_audio = last_summary_audio
                        else:
                            play(tts_main, generating_summary_p)
                            summary_text = summarize(" ".join(read_so_far))
                            summary_audio = speak(summary_text)
                            print("\n========SUMMARY=======\n")
                            print(summary_text)
                            last_summary_audio = summary_audio
                            last_summary_index = current_index
                        non_blocking_play(tts_main, summary_audio, "Press 's' to stop summary", stopping_summary_p)
                        play(tts_main, back_pause_menu_p)
                        continue
                    # QUERY RESOLUTION
                    elif choice == "x":
                        # Announce query mode
                        play(tts_main, ask_query_intro_p)
                        # Listen for user's voice question
                        question = listen_for_command(is_question=True)
                        if question is None or not question.strip():
                            # No question → back to voice control
                            play(tts_main, vc_back_p)
                            # time.sleep(1)
                            continue   # <── stays inside voice mode
                        # Generate answer
                        play(tts_main, generating_answer_p)
                        answer = answer_query(" ".join(read_so_far), question)
                        print("\n========ANSWER=======\n")
                        print(answer)
                        if not answer.strip():
                            play(tts_main, vc_back_p)
                            # time.sleep(1)
                            continue
                        # Speak the answer
                        answer_audio = speak(answer)
                        non_blocking_play(tts_main, answer_audio, "Press 's' to stop response", stopping_response_p)
                        # Finished answer → back to voice mode
                        play(tts_main, vc_back_p)
                        # time.sleep(1)
                        continue  # <── stay inside voice mode
                    # QUIT
                    elif choice == "q":
                        # SAVE STATE BEFORE EXIT
                        if sentences and 0 <= current_index < len(sentences):
                            task_state = {
                                "sentences": sentences,
                                "current_index": current_index,
                            }
                            save_state(task_state)
                        play(tts_main, exiting_module_p)
                        return
                    else:
                        print("Invalid option.")
                        continue
        # Finished this sentence
        read_so_far.append(sentence)
        current_index += 1
        # Invalidate summary cache because content changed
        last_summary_audio = None
        last_summary_index = -1
    # ---------------------------------------------------------
    # ALL SENTENCES COMPLETE
    # ---------------------------------------------------------
    clear_state()
    play(tts_main, all_done_p)
    print("\n===== COMPLETED ALL SENTENCES =====\n")
# ================================================================
if __name__ == "__main__":
    main()