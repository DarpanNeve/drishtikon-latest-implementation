# core/llm_task.py
import threading
from typing import Callable, Any, Optional


class LLMTask:
    def __init__(self, fn: Callable, *args, **kwargs):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

        self._cancelled = threading.Event()
        self._done = threading.Event()
        self.result: Optional[Any] = None
        self.error: Optional[Exception] = None

        self._thread = threading.Thread(
            target=self._run,
            daemon=True
        )

    def _run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            if not self._cancelled.is_set():
                self.result = result
        except Exception as e:
            self.error = e
        finally:
            self._done.set()

    def start(self):
        self._thread.start()

    def cancel(self):
        self._cancelled.set()

    def done(self) -> bool:
        return self._done.is_set()

    def cancelled(self) -> bool:
        return self._cancelled.is_set()
