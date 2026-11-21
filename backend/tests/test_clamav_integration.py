"""Opt-in integration tests against the configured ClamAV daemon.

Run inside the Compose backend container with RUN_CLAMAV_INTEGRATION_TESTS=1.
"""
import os

import pytest

from app.core.exceptions import MalwareDetectedException
from app.core.config import settings
from app.services.scanning.malware_scanner import (
    MalwareScannerService,
    ScanStatus,
    malware_scanner,
)

RUN_CLAMAV_INTEGRATION_TESTS = os.getenv("RUN_CLAMAV_INTEGRATION_TESTS") == "1"
EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


@pytest.mark.skipif(
    not RUN_CLAMAV_INTEGRATION_TESTS,
    reason="set RUN_CLAMAV_INTEGRATION_TESTS=1 to test a live ClamAV daemon",
)
def test_live_clamav_scans_clean_file():
    result = malware_scanner.scan_bytes(b"VaultGuard clean scan integration test", "clean.txt")

    assert result.status == ScanStatus.CLEAN
    assert result.is_safe


@pytest.mark.skipif(
    not RUN_CLAMAV_INTEGRATION_TESTS,
    reason="set RUN_CLAMAV_INTEGRATION_TESTS=1 to test a live ClamAV daemon",
)
def test_live_clamav_detects_eicar():
    result = malware_scanner.scan_bytes(EICAR, "eicar.txt")

    assert result.status == ScanStatus.INFECTED
    assert result.should_block
    assert result.detection_name
    assert MalwareDetectedException(result).code == "MALWARE_DETECTED"


def test_unavailable_clamav_fails_closed_with_service_error():
    scanner = MalwareScannerService(
        clamav_host="scanner.invalid",
        clamav_port=1,
        timeout_seconds=2,
    )
    result = scanner.scan_bytes(b"clean-looking content", "unavailable.txt")

    assert result.status == ScanStatus.SCANNER_UNAVAILABLE
    assert result.should_block
    assert not result.is_safe
    assert MalwareDetectedException(result).code == "SCANNER_UNAVAILABLE"
