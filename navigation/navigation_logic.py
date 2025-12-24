import re

# --------------------------------------------------
# HTML + TTS SAFE CLEANER
# --------------------------------------------------
def clean_instruction_for_tts(raw_text: str) -> str:
    if not raw_text:
        return ""

    text = raw_text

    # Remove HTML tags (<b>, <div>, <wbr/>, etc.)
    text = re.sub(r"<[^>]+>", " ", text)

    # Replace HTML entities
    text = text.replace("&amp;", "and")

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Expand common abbreviations
    replacements = {
        " Rd": " Road",
        " Sta ": " Station ",
        " St ": " Street ",
        " Chowk": " Chowk",
        " Km": " kilometers",
        " km": " kilometers",
        " m.": " meters.",
        " m ": " meters ",
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    # Convert distances to spoken-friendly form
    text = re.sub(r"(\d+)\s*km", r"\1 kilometers", text)
    text = re.sub(r"(\d+)\s*m", r"\1 meters", text)

    # Improve navigation verbs
    text = text.replace("Head", "Start")
    text = text.replace("Continue", "Keep going")

    # Remove brackets but keep content
    text = re.sub(r"\((.*?)\)", r"\1", text)

    # Ensure sentence ends cleanly
    if not text.endswith("."):
        text += "."

    return text

def clean_navigation_steps(raw_steps):
    cleaned = []

    for step in raw_steps:
        instruction = step.get("instruction", "")
        clean_text = clean_instruction_for_tts(instruction)

        if clean_text:
            cleaned.append({
                "instruction": clean_text
            })

    return cleaned
