# core/llm_runner.py
import time
from core.playback_controls import read_key_nonblocking
from core.tts_player import tts_main
from core.llm_task import LLMTask


def run_llm_task(
    task: LLMTask,
    cancel_keys=("p", "q", "s"),
    poll_interval=0.05,
):
    task.start()

    while not task.done():
        key = read_key_nonblocking()
        if key in cancel_keys:
            task.cancel()
            tts_main.stop()
            return None
        time.sleep(poll_interval)

    if task.cancelled():
        return None

    if task.error:
        raise task.error

    return task.result
