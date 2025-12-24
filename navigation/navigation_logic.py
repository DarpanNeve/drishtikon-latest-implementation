import re
from core.logger import log


def clean_instruction(text):
    """
    Remove HTML tags and make instruction TTS-friendly
    """
    text = re.sub("<[^<]+?>", "", text)
    text = text.replace("Head", "Start")
    text = text.replace("Continue", "Keep going")
    return text


def extract_navigation_steps(route):
    """
    Converts Google Maps route to simplified navigation steps
    """
    steps_out = []

    try:
        legs = route.get("legs", [])
        if not legs:
            return steps_out

        for step in legs[0]["steps"]:
            instruction = clean_instruction(step["html_instructions"])
            distance = step["distance"]["text"]

            steps_out.append({
                "instruction": f"{instruction}. Walk for {distance}."
            })

        log("NAV", "-", f"{len(steps_out)} navigation steps generated")
        return steps_out

    except Exception as e:
        log("NAV", "-", f"Navigation parse error: {e}")
        return []