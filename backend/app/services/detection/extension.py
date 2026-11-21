import os
from typing import Set, Tuple


class ExtensionDetector:
    """Detects ransomware extensions, suspicious double extensions, and bulk renaming patterns."""

    KNOWN_RANSOMWARE_EXTENSIONS: Set[str] = {
        ".locked", ".crypto", ".crypt", ".enc", ".wncry", ".locky", ".cerber",
        ".ryuk", ".phobos", ".dharma", ".makop", ".blackcat", ".alphv", ".hive",
        ".conti", ".sodinokibi", ".revil", ".mallox", ".stop", ".djvu", ".medusa",
        ".babuk", ".akira", ".ransom", ".crypted", ".cryptolocker", ".zepto",
        ".odin", ".thor", ".aesir", ".zzzzz", ".lockbit", ".royal", ".play",
        ".vice", ".snatch", ".cuba", ".bianlian", ".rhysida", ".clop",
    }

    SUSPICIOUS_DOUBLE_EXTENSIONS: Set[str] = {
        ".pdf.enc", ".docx.enc", ".xlsx.enc", ".pptx.enc", ".jpg.enc",
        ".pdf.locked", ".docx.locked", ".xlsx.locked", ".jpg.locked",
        ".pdf.crypto", ".docx.crypto", ".xlsx.crypto",
    }

    @classmethod
    def evaluate_path(cls, file_path: str, old_path: str = "") -> Tuple[bool, str, str]:
        """
        Inspect file path for ransomware indicators.
        Returns: (is_suspicious, matched_extension_or_pattern, rationale)
        """
        lower_path = file_path.lower()
        base_name = os.path.basename(lower_path)
        _, ext = os.path.splitext(lower_path)

        # 1. Check for suspicious double extensions (e.g. document.docx.locked)
        for double_ext in cls.SUSPICIOUS_DOUBLE_EXTENSIONS:
            if base_name.endswith(double_ext):
                return True, double_ext, f"Suspicious double extension detected: '{double_ext}'"

        # 2. Exact match against known ransomware extensions
        if ext in cls.KNOWN_RANSOMWARE_EXTENSIONS:
            return True, ext, f"File has known ransomware extension: '{ext}'"

        # 3. Check for rename event indicating extension mutation
        if old_path:
            old_lower = old_path.lower()
            _, old_ext = os.path.splitext(old_lower)
            if old_ext and ext and old_ext != ext:
                # If old was a document/image and new is random or high-entropy
                common_docs = {".pdf", ".docx", ".xlsx", ".pptx", ".jpg", ".png", ".txt", ".sql", ".db"}
                if old_ext in common_docs and ext in cls.KNOWN_RANSOMWARE_EXTENSIONS:
                    return True, f"{old_ext}->{ext}", f"Ransomware renaming pattern: changed from {old_ext} to {ext}"

        return False, ext, "Extension appears normal."


extension_detector = ExtensionDetector()
