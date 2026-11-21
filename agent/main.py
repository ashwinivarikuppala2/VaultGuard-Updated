import logging
import signal
import sys
import time
from agent.backup_agent.agent import VaultGuardAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vaultguard.agent")


def main():
    agent = VaultGuardAgent()

    def signal_handler(sig, frame):
        logger.info("Shutdown signal received.")
        agent.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        agent.start()
        while agent.is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()


if __name__ == "__main__":
    main()

