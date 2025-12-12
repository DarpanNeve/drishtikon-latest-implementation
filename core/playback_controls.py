import time
from core.tts_player import tts_main
from core.prompts import goodbye_p

# RESUME OR PLAY AUDIO
def play(tts=tts_main, audio_file_name=goodbye_p):
    tts.play(audio_file_name)
    tts.wait()

