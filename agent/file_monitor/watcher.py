import logging
import os
from typing import Callable, List
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from agent.file_monitor.debouncer import DebounceManager

logger = logging.getLogger("vaultguard.agent.watcher")


class BackupFileEventHandler(FileSystemEventHandler):
    def __init__(self, on_file_changed: Callable[[str], None], debounce_seconds: float = 2.0):
        super().__init__()
        self.on_file_changed = on_file_changed
        self.debouncer = DebounceManager(debounce_seconds=debounce_seconds)

    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory:
            self._handle_change(event.src_path)

    def on_created(self, event: FileSystemEvent):
        if not event.is_directory:
            self._handle_change(event.src_path)

    def on_moved(self, event: FileSystemEvent):
        if not event.is_directory:
            self._handle_change(event.dest_path)

    def _handle_change(self, file_path: str):
        # Ignore temporary or swap files
        if file_path.endswith((".tmp", ".crdownload", ".part", ".lock", "~")):
            return
        if not os.path.exists(file_path):
            return

        logger.debug(f"File change detected: {file_path}")
        self.debouncer.debounce(file_path, self.on_file_changed)


class FolderWatcher:
    """Manages active filesystem observers across monitored folders."""

    def __init__(self, on_file_ready: Callable[[str], None], debounce_seconds: float = 2.0):
        self.handler = BackupFileEventHandler(on_file_changed=on_file_ready, debounce_seconds=debounce_seconds)
        self.observer = Observer()
        self.watched_paths: List[str] = []

    def add_folder(self, folder_path: str):
        abs_path = os.path.abspath(folder_path)
        os.makedirs(abs_path, exist_ok=True)
        self.observer.schedule(self.handler, abs_path, recursive=True)
        self.watched_paths.append(abs_path)
        logger.info(f"Watching directory for modifications: {abs_path}")

    def start(self):
        self.observer.start()
        logger.info("Filesystem watcher started.")

    def stop(self):
        self.handler.debouncer.cancel_all()
        self.observer.stop()
        self.observer.join()
        logger.info("Filesystem watcher stopped.")

