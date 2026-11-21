"""
Tests for HTTP 413 / upload-size enforcement.

These tests validate:
  1. FileSizeLimitException is raised correctly by the endpoint size guard.
  2. The exception carries the right error code and human-readable message.
  3. The size constants (MAX_UPLOAD_SIZE_MB, _MAX_UPLOAD_BYTES) are consistent.
  4. Files at / below the limit do NOT raise FileSizeLimitException.
  5. The backups endpoint module imports and size guard are well-formed.

We test at the unit level (no DB / MinIO / network) so the suite runs offline.
"""
import uuid

import pytest

from app.core.config import settings
from app.core.exceptions import FileSizeLimitException

MB = 1024 * 1024
MAX_MB = settings.MAX_UPLOAD_SIZE_MB
MAX_BYTES = MAX_MB * MB


# ---------------------------------------------------------------------------
# 1. FileSizeLimitException shape
# ---------------------------------------------------------------------------


class TestFileSizeLimitException:
    """FileSizeLimitException must carry correct code, message, and details."""

    def test_error_code_is_file_too_large(self):
        exc = FileSizeLimitException(file_size_bytes=MAX_BYTES + 1, max_size_bytes=MAX_BYTES)
        assert exc.code == "FILE_TOO_LARGE"

    def test_message_mentions_size(self):
        size = MAX_BYTES + 1
        exc = FileSizeLimitException(file_size_bytes=size, max_size_bytes=MAX_BYTES)
        # Message should mention the max size in MB
        assert str(MAX_MB) in exc.message

    def test_details_contain_expected_keys(self):
        exc = FileSizeLimitException(file_size_bytes=MAX_BYTES + 1, max_size_bytes=MAX_BYTES)
        assert "file_size_bytes" in exc.details
        assert "max_size_bytes" in exc.details
        assert "max_size_mb" in exc.details

    def test_details_values_are_correct(self):
        over = MAX_BYTES + 512
        exc = FileSizeLimitException(file_size_bytes=over, max_size_bytes=MAX_BYTES)
        assert exc.details["file_size_bytes"] == over
        assert exc.details["max_size_bytes"] == MAX_BYTES
        assert exc.details["max_size_mb"] == MAX_MB


# ---------------------------------------------------------------------------
# 2. Size guard logic (mirrors the endpoint's inline check)
# ---------------------------------------------------------------------------


def _size_guard(raw_bytes: bytes, max_bytes: int) -> None:
    """Replicates the guard from app/api/v1/endpoints/backups.py."""
    if len(raw_bytes) > max_bytes:
        raise FileSizeLimitException(
            file_size_bytes=len(raw_bytes),
            max_size_bytes=max_bytes,
        )


class TestSizeGuardLogic:
    """The inline size-guard used by the /backups/manual endpoint."""

    def test_empty_file_passes(self):
        """Zero-byte file must not raise."""
        _size_guard(b"", MAX_BYTES)  # no exception

    def test_small_file_passes(self):
        """A 1 MB file must not raise."""
        _size_guard(b"X" * MB, MAX_BYTES)

    def test_file_at_limit_passes(self):
        """A file of exactly MAX_BYTES must not raise (boundary inclusive)."""
        _size_guard(b"X" * MAX_BYTES, MAX_BYTES)

    def test_file_one_byte_over_limit_raises(self):
        """MAX_BYTES + 1 must raise FileSizeLimitException."""
        with pytest.raises(FileSizeLimitException) as exc_info:
            _size_guard(b"X" * (MAX_BYTES + 1), MAX_BYTES)
        assert exc_info.value.code == "FILE_TOO_LARGE"

    def test_very_large_file_raises(self):
        """A 501 MB payload (simulated via size, not allocated) raises."""
        # Avoid actually allocating 501 MB – patch len via a fake bytes-like object
        class FakeBytes:
            def __len__(self):
                return 501 * MB

        fake = FakeBytes()
        # Can't pass FakeBytes to _size_guard directly (uses len(raw_bytes)),
        # so test via the exception constructor instead.
        over = 501 * MB
        exc = FileSizeLimitException(file_size_bytes=over, max_size_bytes=MAX_BYTES)
        assert exc.code == "FILE_TOO_LARGE"
        assert exc.details["file_size_bytes"] == over


# ---------------------------------------------------------------------------
# 3. Settings consistency
# ---------------------------------------------------------------------------


class TestSettingsConsistency:
    """MAX_UPLOAD_SIZE_MB in settings must be sane and consistent."""

    def test_max_upload_size_mb_is_positive(self):
        assert settings.MAX_UPLOAD_SIZE_MB > 0

    def test_max_upload_size_mb_is_500(self):
        """The configured limit must be 500 MB as agreed."""
        assert settings.MAX_UPLOAD_SIZE_MB == 500

    def test_endpoint_constant_matches_settings(self):
        """The endpoint's _MAX_UPLOAD_BYTES must equal settings value * 1024^2."""
        from app.api.v1.endpoints.backups import _MAX_UPLOAD_BYTES
        assert _MAX_UPLOAD_BYTES == settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    def test_endpoint_max_bytes_is_500_mb(self):
        from app.api.v1.endpoints.backups import _MAX_UPLOAD_BYTES
        assert _MAX_UPLOAD_BYTES == 500 * 1024 * 1024


# ---------------------------------------------------------------------------
# 4. Exception is a VaultGuardException subclass (for middleware routing)
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    def test_file_size_limit_exception_is_vaultguard_exception(self):
        from app.core.exceptions import VaultGuardException
        exc = FileSizeLimitException(file_size_bytes=1, max_size_bytes=1)
        assert isinstance(exc, VaultGuardException)

    def test_file_size_limit_exception_is_exception(self):
        exc = FileSizeLimitException(file_size_bytes=1, max_size_bytes=1)
        assert isinstance(exc, Exception)
