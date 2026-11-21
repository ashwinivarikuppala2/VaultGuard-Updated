import hashlib
import logging
import uuid
from typing import Optional, Tuple

from app.core.compression import compression_service
from app.core.encryption import encryption_service
from app.models.future_placeholders import FileVersion
from app.storage.minio_client import minio_storage

logger = logging.getLogger("vaultguard.recovery.integrity")


class IntegrityVerificationError(Exception):
    """Raised when cryptographic decryption or pre-encryption SHA-256 verification fails."""
    pass


class RecoveryIntegrityService:
    """
    Downloads, decrypts (AES-256-GCM), decompresses (zlib), and cryptographically
    validates backup versions against stored SHA-256 pre-encryption digest.
    """

    def restore_and_verify_payload(
        self,
        version: FileVersion,
        organization_id: uuid.UUID,
        associated_data: Optional[bytes] = None,
    ) -> Tuple[bytes, str]:
        """
        Executes the reverse pipeline of backup creation:
        1. Fetch ciphertext from MinIO / local fallback storage.
        2. Decrypt with tenant AES-256-GCM key and stored nonce/auth_tag.
        3. Decompress zlib payload.
        4. Validate computed SHA-256 of plaintext against version.file_hash_sha256.

        Returns: (verified_plaintext_bytes, verified_sha256)
        Raises: IntegrityVerificationError on any mismatch or decryption failure.
        """
        logger.info(
            f"Restoring file version {version.version_number} (ID: {version.id}) from '{version.storage_path}'"
        )

        # 1. Download ciphertext
        try:
            stored_bytes = minio_storage.download_bytes(version.storage_path)
        except Exception as e:
            logger.exception(f"MinIO Object Missing: Failed to retrieve stored object for version {version.id} at path '{version.storage_path}'")
            raise IntegrityVerificationError(f"MinIO Object Missing: '{version.storage_path}' not found in storage ({str(e)})")

        # 2. Decrypt if encrypted
        decrypted_bytes: bytes
        if version.is_encrypted:
            if not version.nonce_hex:
                raise IntegrityVerificationError("Encryption key mismatch: Missing AES-256-GCM initialization vector (nonce_hex).")
            try:
                decrypted_bytes = encryption_service.decrypt(
                    encrypted_payload=stored_bytes,
                    nonce_hex=version.nonce_hex,
                    organization_id=str(organization_id),
                    associated_data=associated_data,
                )
            except Exception as e:
                logger.exception(f"AES-256-GCM Decryption Failed for version {version.id}: {str(e)}")
                raise IntegrityVerificationError(
                    f"AES Decryption Failed: Cryptographic decryption failed ({str(e)})"
                )
        else:
            decrypted_bytes = stored_bytes

        # 3. Decompress
        plaintext: bytes
        if version.compression_algorithm == "zlib":
            try:
                plaintext = compression_service.decompress(decrypted_bytes)
            except Exception as e:
                logger.exception(f"Decompression Failed for version {version.id}: {str(e)}")
                raise IntegrityVerificationError(f"File decompression failed: {str(e)}")
        else:
            plaintext = decrypted_bytes

        # 4. SHA-256 Integrity Verification
        computed_hash = hashlib.sha256(plaintext).hexdigest()
        if version.file_hash_sha256 and computed_hash.lower() != version.file_hash_sha256.lower():
            logger.critical(
                f"[INTEGRITY VIOLATION] SHA Verification Failed for Version {version.id}: "
                f"Expected SHA-256: {version.file_hash_sha256}, Computed SHA-256: {computed_hash}"
            )
            raise IntegrityVerificationError(
                f"SHA Verification Failed: Expected SHA-256 '{version.file_hash_sha256}', calculated '{computed_hash}'"
            )

        logger.info(f"Integrity verified for version {version.id} (SHA-256: {computed_hash})")
        return plaintext, computed_hash


integrity_service = RecoveryIntegrityService()
