import hashlib
import os
import zlib
from typing import Tuple
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class AgentCrypto:
    """Client-side compression, AES-256-GCM encryption, and SHA-256 integrity calculation."""

    @staticmethod
    def compress(data: bytes, level: int = 6) -> bytes:
        return zlib.compress(data, level=level)

    @staticmethod
    def compute_sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def derive_key(master_secret: str, context_info: str) -> bytes:
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"vaultguard_salt_m2",
            info=context_info.encode("utf-8"),
        )
        return hkdf.derive(master_secret.encode("utf-8"))

    @staticmethod
    def encrypt(data: bytes, key: bytes, associated_data: bytes = b"") -> Tuple[bytes, str, str]:
        """Encrypts data using AES-256-GCM.
        
        Returns:
            Tuple of (ciphertext_with_tag, nonce_hex, tag_hex)
        """
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data, associated_data)
        tag = ciphertext[-16:]
        return ciphertext, nonce.hex(), tag.hex()

