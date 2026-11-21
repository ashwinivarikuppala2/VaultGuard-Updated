import logging
import threading
from typing import Callable, Dict

logger = logging.getLogger("vaultguard.agent.debouncer")


class DebounceManager:
    """Thread-safe event debouncer to coalesce rapid file writes before backup."""

    def __init__(self, debounce_seconds: float = 2.0):
        self.debounce_seconds = debounce_seconds
        self.timers: Dict[str, threading.Timer] = {}
        self.lock = threading.Lock()

    def debounce(self, key: str, callback: Callable[[str], None]) -> None:
        """Schedules callback after `debounce_seconds` of inactivity for `key`."""
        with self.lock:
            # Cancel existing timer if file is still being modified
            if key in self.timers:
                self.timers[key].cancel()

            def fire():
                with self.lock:
                    self.timers.pop(key, None)
                try:
                    callback(key)
                except Exception as e:
                    logger.error(f"Error executing debounced callback for {key}: {str(e)}", exc_info=True)

            timer = threading.Timer(self.debounce_seconds, fire)
            self.timers[key] = timer
            timer.daemon = True
            timer.start()

    def cancel_all(self) -> None:
        with self.lock:
            for timer in self.timers.values():
                timer.cancel()
            self.timers.clear()

