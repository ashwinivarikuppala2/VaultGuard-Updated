import logging
import threading
import time
from typing import Callable, List

logger = logging.getLogger("vaultguard.agent.scheduler")


class BackupScheduler:
    """Interval-based scheduler triggering periodic synchronization sweeps."""

    def __init__(self, interval_seconds: int, sweep_callback: Callable[[], None]):
        self.interval_seconds = interval_seconds
        self.sweep_callback = sweep_callback
        self.running = False
        self.thread: threading.Thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info(f"Backup scheduler started (interval: {self.interval_seconds}s).")

    def _run_loop(self):
        while self.running:
            time.sleep(self.interval_seconds)
            if self.running:
                logger.info("Executing periodic scheduled backup sweep...")
                try:
                    self.sweep_callback()
                except Exception as e:
                    logger.error(f"Error during scheduled backup sweep: {str(e)}", exc_info=True)

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        logger.info("Backup scheduler stopped.")

