import hashlib
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.threat import CanaryFile


class CanaryService:
    """Manages decoy tripwire files seeded into protected folders to trap early ransomware."""

    CANARY_TEMPLATES = [
        ("Confidential_Q4_Payroll.xlsx", b"VAULTGUARD_CANARY_PAYROLL_DATA_BLOCK_v1\x00\x01\x02" * 64),
        ("Board_Meeting_Minutes_2026.docx", b"VAULTGUARD_CANARY_BOARD_MINUTES_CONFIDENTIAL\xfe\xff" * 64),
        ("Corporate_Tax_Returns_2025.pdf", b"%PDF-1.7\n1 0 obj\n<< /Title (VaultGuard Canary Tax Decoy) >>\nendobj\n" * 32),
    ]

    @staticmethod
    def generate_token() -> str:
        """Create a cryptographically unique tripwire token."""
        return f"VG-CANARY-{uuid.uuid4().hex[:16].upper()}"

    @classmethod
    def create_canary_payload(cls, template_name: str, canary_token: str) -> Tuple[str, bytes, str]:
        """Produce file contents for a canary file including embedded token."""
        base_content = b""
        for fname, payload in cls.CANARY_TEMPLATES:
            if fname.lower() == template_name.lower():
                base_content = payload
                break

        if not base_content:
            base_content = b"VAULTGUARD_GENERIC_CANARY_PAYLOAD_SECTION_" * 32

        full_content = base_content + f"\n[CANARY_ID:{canary_token}]\n".encode("utf-8")
        sha256 = hashlib.sha256(full_content).hexdigest()
        return template_name, full_content, sha256

    async def register_canary_file(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        device_id: uuid.UUID,
        folder_path: str,
        template_name: Optional[str] = None,
    ) -> CanaryFile:
        """Register and persist a new canary record in a target directory."""
        if not template_name:
            template_name = self.CANARY_TEMPLATES[0][0]

        token = self.generate_token()
        fname, content, sha256 = self.create_canary_payload(template_name, token)
        file_path = os.path.join(folder_path, f".~${fname}")

        canary = CanaryFile(
            organization_id=organization_id,
            device_id=device_id,
            file_path=file_path,
            filename=f".~${fname}",
            expected_hash_sha256=sha256,
            canary_token=token,
            is_tampered=False,
            last_checked_at=datetime.now(timezone.utc),
        )
        db.add(canary)
        await db.commit()
        await db.refresh(canary)
        return canary

    async def evaluate_file_tamper(
        self,
        db: AsyncSession,
        device_id: uuid.UUID,
        file_path: str,
        current_content: Optional[bytes] = None,
    ) -> Tuple[bool, Optional[CanaryFile], str]:
        """
        Check if an updated or deleted file matches a known canary file.
        Returns: (is_canary_tampered, canary_record, rationale)
        """
        norm_path = os.path.normpath(file_path).lower()
        stmt = select(CanaryFile).where(
            CanaryFile.device_id == device_id,
            CanaryFile.is_tampered == False,
        )
        result = await db.execute(stmt)
        canaries = result.scalars().all()

        for c in canaries:
            if os.path.normpath(c.file_path).lower() == norm_path:
                # File path matches a designated canary!
                if current_content is not None:
                    current_hash = hashlib.sha256(current_content).hexdigest()
                    if current_hash != c.expected_hash_sha256:
                        c.is_tampered = True
                        c.tampered_at = datetime.now(timezone.utc)
                        await db.commit()
                        return True, c, f"CANARY TRIPWIRE TRIPPED: Hash mutation detected on decoy '{c.filename}'."
                else:
                    # Deletion or rename event on canary file
                    c.is_tampered = True
                    c.tampered_at = datetime.now(timezone.utc)
                    await db.commit()
                    return True, c, f"CANARY TRIPWIRE TRIPPED: Decoy file '{c.filename}' was modified/deleted/renamed."

        return False, None, "File is not an active canary decoy."


canary_service = CanaryService()

