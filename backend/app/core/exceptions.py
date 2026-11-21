from typing import Any, Optional


class VaultGuardException(Exception):
    """Base exception for all domain and application errors."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR", details: Optional[Any] = None):
        self.message = message
        self.code = code
        self.details = details
        super().__init__(self.message)


class EntityNotFoundException(VaultGuardException):
    def __init__(self, entity_name: str, identifier: Any):
        super().__init__(
            message=f"{entity_name} with identifier '{identifier}' was not found.",
            code="NOT_FOUND",
            details={"entity": entity_name, "identifier": str(identifier)},
        )


class DuplicateEntityException(VaultGuardException):
    def __init__(self, entity_name: str, field: str, value: Any):
        super().__init__(
            message=f"{entity_name} with {field} '{value}' already exists.",
            code="DUPLICATE_ENTITY",
            details={"entity": entity_name, "field": field, "value": str(value)},
        )


class AuthenticationException(VaultGuardException):
    def __init__(self, message: str = "Invalid authentication credentials"):
        super().__init__(message=message, code="AUTHENTICATION_FAILED")


class AuthorizationException(VaultGuardException):
    def __init__(self, message: str = "Insufficient permissions to perform this action"):
        super().__init__(message=message, code="FORBIDDEN")


class InactiveUserException(VaultGuardException):
    def __init__(self, message: str = "User account is disabled or deactivated"):
        super().__init__(message=message, code="USER_INACTIVE")


class InactiveOrganizationException(VaultGuardException):
    def __init__(self, message: str = "Associated organization is suspended or inactive"):
        super().__init__(message=message, code="ORGANIZATION_INACTIVE")


class TokenValidationException(VaultGuardException):
    def __init__(self, message: str = "Token is invalid, expired, or revoked"):
        super().__init__(message=message, code="INVALID_TOKEN")


class FileSizeLimitException(VaultGuardException):
    """Raised when an uploaded file exceeds the configured maximum size."""

    def __init__(self, file_size_bytes: int, max_size_bytes: int) -> None:
        max_mb = max_size_bytes // (1024 * 1024)
        actual_mb = file_size_bytes / (1024 * 1024)
        super().__init__(
            message=(
                f"File size {actual_mb:.1f} MB exceeds the maximum allowed "
                f"upload size of {max_mb} MB. Please reduce the file size and try again."
            ),
            code="FILE_TOO_LARGE",
            details={
                "file_size_bytes": file_size_bytes,
                "max_size_bytes": max_size_bytes,
                "max_size_mb": max_mb,
            },
        )


class MalwareDetectedException(VaultGuardException):
    """Raised when malware scanning blocks a file from entering backup storage."""

    def __init__(self, scan_result: "ScanResult") -> None:  # noqa: F821
        self.scan_result = scan_result
        scan_status = scan_result.status.value
        if scan_status in ("INFECTED", "SUSPICIOUS"):
            code = "MALWARE_DETECTED"
            message = f"Backup blocked: malware detected [{scan_status}]"
            if scan_result.detection_name:
                message += f" {scan_result.detection_name}"
        elif scan_status == "SCANNER_UNAVAILABLE":
            code = "SCANNER_UNAVAILABLE"
            message = "Backup blocked: ClamAV scanner is unavailable."
        elif scan_status == "SCAN_TIMEOUT":
            code = "SCANNER_TIMEOUT"
            message = "Backup blocked: ClamAV scan timed out."
        else:
            code = "SCANNER_ERROR"
            message = f"Backup blocked: ClamAV scan failed [{scan_status}]."

        details = {
            "scan_status": scan_status,
            "detection_name": scan_result.detection_name,
            "detection_category": scan_result.detection_category,
            "is_ransomware_related": scan_result.is_ransomware_related,
            "sha256": scan_result.sha256,
            "file_size": scan_result.file_size,
        }
        super().__init__(
            message=message,
            code=code,
            details=details,
        )

