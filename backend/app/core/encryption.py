import hashlib
import os
from dataclasses import dataclass
from typing import Optional, Tuple
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from app.core.config import settings


@dataclass
class EncryptionResult:
    ciphertext: bytes
    nonce_hex: str
    auth_tag_hex: str
    sha256_hash: str
    encrypted_size: int


class EncryptionService:
    """Military-grade AES-256-GCM authenticated encryption service."""

    def __init__(self, master_secret: Optional[str] = None):
        self.master_secret = (master_secret or settings.SECRET_KEY).encode("utf-8")

    def derive_key(self, organization_id: str, salt: bytes = b"vaultguard_salt_m2") -> bytes:
        """Derive an isolated 256-bit AES key for a specific tenant organization."""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=salt,
            info=organization_id.encode("utf-8"),
        )
        return hkdf.derive(self.master_secret)

    def encrypt(
        self,
        plaintext: bytes,
        organization_id: str,
        associated_data: Optional[bytes] = None,
    ) -> EncryptionResult:
        """Encrypt payload with AES-256-GCM and compute SHA-256 integrity digest."""
        key = self.derive_key(organization_id)
        aesgcm = AESGCM(key)

        # 96-bit (12 bytes) standard GCM nonce
        nonce = os.urandom(12)
        encrypted_with_tag = aesgcm.encrypt(nonce, plaintext, associated_data)

        # Standard AESGCM in cryptography appends the 16-byte tag to the ciphertext
        tag = encrypted_with_tag[-16:]
        raw_ciphertext = encrypted_with_tag[:-16]

        # Compute SHA-256 digest of the encrypted payload (ciphertext) for storage-layer
        # integrity. NOTE: file_hash_sha256 stored in FileVersion is overridden by
        # backup_service to hold the hash of the original raw plaintext instead,
        # so the recovery integrity check can verify the decrypted+decompressed content.
        sha256_hash = hashlib.sha256(encrypted_with_tag).hexdigest()

        return EncryptionResult(
            ciphertext=encrypted_with_tag,
            nonce_hex=nonce.hex(),
            auth_tag_hex=tag.hex(),
            sha256_hash=sha256_hash,
            encrypted_size=len(encrypted_with_tag),
        )

    def decrypt(
        self,
        encrypted_payload: bytes,
        nonce_hex: str,
        organization_id: str,
        associated_data: Optional[bytes] = None,
    ) -> bytes:
        """Decrypt AES-256-GCM payload and verify authentication tag."""
        key = self.derive_key(organization_id)
        aesgcm = AESGCM(key)
        nonce = bytes.fromhex(nonce_hex)
        return aesgcm.decrypt(nonce, encrypted_payload, associated_data)


encryption_service = EncryptionService()

