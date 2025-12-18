# core/priority_audio.py
import threading

class AudioPriority:
    DETECTION = 0     # Safety-critical
    NAVIGATION = 1
    GEMINI = 2
    SYSTEM = 3

class PriorityAudioManager:
    def __init__(self, tts_player):
        self.tts = tts_player
        self._lock = threading.Lock()
        self.current_priority = None

    def request_play(self, audio_path, priority):
        """
        Decide whether this audio request is allowed to play.
        """
        if not audio_path:
            return False

        with self._lock:
            # Nothing playing → allow
            if not self.tts.is_playing():
                self.current_priority = priority
                self.tts.play(audio_path)
                return True

            # Higher priority → interrupt (play() already stops internally)
            if priority < self.current_priority:
                self.current_priority = priority
                self.tts.play(audio_path)
                return True

            # Lower or equal priority → reject
            return False

    def notify_idle(self):
        """
        Reset priority when playback finishes.
        Call periodically from main loop.
        """
        if not self.tts.is_playing():
            self.current_priority = None
