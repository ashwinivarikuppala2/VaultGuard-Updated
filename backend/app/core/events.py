import logging
from typing import Any, Callable, Dict, List

logger = logging.getLogger("vaultguard.events")

# Registry of subscribers
_backup_completed_subscribers: List[Callable[[Dict[str, Any]], Any]] = []
_threat_detected_subscribers: List[Callable[[Dict[str, Any]], Any]] = []
_quarantine_subscribers: List[Callable[[Dict[str, Any]], Any]] = []


def register_backup_completed_hook(subscriber: Callable[[Dict[str, Any]], Any]) -> None:
    """Register an event listener for Module 3 (e.g. Entropy scoring & quarantine engine)."""
    if subscriber not in _backup_completed_subscribers:
        _backup_completed_subscribers.append(subscriber)
        logger.info(f"Registered backup-completed hook: {subscriber.__name__}")


def register_threat_detected_hook(subscriber: Callable[[Dict[str, Any]], Any]) -> None:
    """Register an event listener for threat detection."""
    if subscriber not in _threat_detected_subscribers:
        _threat_detected_subscribers.append(subscriber)
        logger.info(f"Registered threat-detected hook: {subscriber.__name__}")


def register_quarantine_hook(subscriber: Callable[[Dict[str, Any]], Any]) -> None:
    """Register an event listener for Module 4 recovery workflows upon quarantine."""
    if subscriber not in _quarantine_subscribers:
        _quarantine_subscribers.append(subscriber)
        logger.info(f"Registered quarantine hook: {subscriber.__name__}")


async def publish_backup_completed_event(payload: Dict[str, Any]) -> None:
    """Dispatches a backup-completed event to all registered extension hooks."""
    logger.info(
        f"[EVENT:BACKUP_COMPLETED] File: '{payload.get('file_path')}', "
        f"Version: {payload.get('version_number')}, "
        f"SHA-256: {payload.get('file_hash_sha256')}"
    )

    for subscriber in _backup_completed_subscribers:
        try:
            res = subscriber(payload)
            if hasattr(res, "__await__"):
                await res
        except Exception as e:
            logger.error(f"Error in backup-completed hook {subscriber.__name__}: {str(e)}", exc_info=True)


async def publish_threat_detected_event(payload: Dict[str, Any]) -> None:
    """Dispatches a threat-detected event to registered hooks."""
    logger.warning(
        f"[EVENT:THREAT_DETECTED] Type: {payload.get('detection_type')}, "
        f"Score: {payload.get('risk_score')}, "
        f"Device: {payload.get('device_id')}"
    )

    for subscriber in _threat_detected_subscribers:
        try:
            res = subscriber(payload)
            if hasattr(res, "__await__"):
                await res
        except Exception as e:
            logger.error(f"Error in threat-detected hook {subscriber.__name__}: {str(e)}", exc_info=True)


async def publish_quarantine_triggered_event(payload: Dict[str, Any]) -> None:
    """Dispatches a quarantine-triggered event for Module 4 recovery workflows."""
    logger.warning(
        f"[EVENT:QUARANTINE_TRIGGERED] Device: {payload.get('device_id')}, "
        f"Reason: {payload.get('reason')}"
    )

    for subscriber in _quarantine_subscribers:
        try:
            res = subscriber(payload)
            if hasattr(res, "__await__"):
                await res
        except Exception as e:
            logger.error(f"Error in quarantine hook {subscriber.__name__}: {str(e)}", exc_info=True)

