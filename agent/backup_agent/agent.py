import logging
import os
import time
from typing import List
from agent.config import agent_config
from agent.encryption.crypto import AgentCrypto
from agent.file_monitor.watcher import FolderWatcher
from agent.scheduler.scheduler import BackupScheduler
from agent.uploader.client import VaultGuardAPIClient

logger = logging.getLogger("vaultguard.agent.master")


class VaultGuardAgent:
    """Master Endpoint Backup Agent.
    
    Implements the standard workflow:
    Authenticate -> Watch folders -> Detect changes -> Debounce -> Compress ->
    Encrypt -> SHA-256 -> Create version -> Upload to MinIO -> Save metadata -> Update dashboard.
    """

    def __init__(self, config=agent_config):
        self.config = config
        self.client = VaultGuardAPIClient(config=config)
        self.watcher = FolderWatcher(
            on_file_ready=self.on_file_changed,
            debounce_seconds=config.debounce_seconds,
        )
        self.scheduler = BackupScheduler(
            interval_seconds=config.poll_interval_seconds,
            sweep_callback=self.run_scheduled_sweep,
        )
        self.is_running = False
        self.is_quarantined = False

    def start(self):
        logger.info("Initializing VaultGuard Secure Backup Agent...")

        # 1. Authenticate with server
        self.client.authenticate()

        # 2. Enroll or resolve device identifier
        self.client.enroll_or_get_device()

        # 3. Setup folder watchers for configured directories
        for folder in self.config.watch_folders:
            self.watcher.add_folder(folder)
        self.watcher.start()

        # 4. Start periodic scheduler
        self.scheduler.start()

        self.is_running = True
        logger.info("VaultGuard Agent is active and protecting local filesystems.")

        # Run an initial sweep across watched folders
        self.run_scheduled_sweep()

    def on_file_changed(self, file_path: str):
        """Triggered after debouncing when a file write has settled."""
        if not os.path.exists(file_path):
            return

        if self.is_quarantined:
            logger.warning(f"[QUARANTINE ENFORCED] Endpoint uploads paused. Ignoring write on: {file_path}")
            return

        try:
            file_size = os.path.getsize(file_path)
            logger.info(f"Processing backup for changed file: {file_path} ({file_size} bytes)")

            with open(file_path, "rb") as f:
                content = f.read()

            # 1. Send live telemetry to threat detection engine
            telemetry_res = self.client.send_telemetry(file_path=file_path, content_bytes=content)
            if telemetry_res and telemetry_res.get("action") == "QUARANTINE":
                self.is_quarantined = True
                logger.critical(
                    f"RANSOMWARE OUTBREAK DETECTED! Threat: '{telemetry_res.get('threat_name')}'. "
                    f"Endpoint is now QUARANTINED. Pausing backup uploads immediately."
                )
                return

            # 2. Execute backup pipeline via client uploader
            # The server applies compression, AES-256-GCM encryption, SHA-256 verification, MinIO upload, and saves metadata
            res = self.client.upload_file_version(file_path=file_path, content_bytes=content)
            logger.info(f"Successfully created backup version v{res.get('version_number')} for {file_path}")

        except Exception as e:
            logger.error(f"Failed to backup {file_path}: {str(e)}", exc_info=True)

    def run_scheduled_sweep(self):
        """Scans watched directories and uploads any files."""
        for folder in self.config.watch_folders:
            abs_folder = os.path.abspath(folder)
            if not os.path.exists(abs_folder):
                continue
            for root, _, files in os.walk(abs_folder):
                for filename in files:
                    full_path = os.path.join(root, filename)
                    self.on_file_changed(full_path)

    def stop(self):
        logger.info("Stopping VaultGuard Agent...")
        self.is_running = False
        self.watcher.stop()
        self.scheduler.stop()
        logger.info("VaultGuard Agent terminated.")

