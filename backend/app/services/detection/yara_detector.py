import re
from typing import Dict, List, Optional, Tuple


class YaraHeuristicDetector:
    """Heuristic and signature detector for ransom notes and malware strings."""

    RANSOM_NOTE_FILENAMES = {
        "readme_to_decrypt.txt",
        "how_to_recover_files.txt",
        "how_to_decrypt.txt",
        "decrypt_instruction.html",
        "restore_files.txt",
        "help_recover_instructions.html",
        "read_me.txt",
        "vaultguard_decrypt.txt",
    }

    RANSOM_NOTE_REGEXES = [
        re.compile(r"all your files (have been|are) encrypted", re.IGNORECASE),
        re.compile(r"pay (a|the) ransom to get your (files|data) back", re.IGNORECASE),
        re.compile(r"your personal (id|key) is:?\s*[A-Za-z0-9+/=]{16,}", re.IGNORECASE),
        re.compile(r"download tor browser and visit", re.IGNORECASE),
        re.compile(r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b"),  # Bitcoin address
        re.compile(r"\bbc1[ac-hj-np-z02-9]{11,71}\b"),        # Bech32 Bitcoin address
        re.compile(r"http://[a-z2-7]{16,56}\.onion", re.IGNORECASE),  # Tor hidden service link
    ]

    SHADOW_COPY_PATTERNS = [
        re.compile(r"vssadmin(\.exe)?\s+delete\s+shadows", re.IGNORECASE),
        re.compile(r"wmic(\.exe)?\s+shadowcopy\s+delete", re.IGNORECASE),
        re.compile(r"wbadmin(\.exe)?\s+delete\s+catalog", re.IGNORECASE),
        re.compile(r"bcdedit(\.exe)?\s+/set\s+.*recoveryenabled\s+no", re.IGNORECASE),
    ]

    @classmethod
    def inspect_file(cls, filename: str, content: bytes) -> Tuple[bool, List[str], str]:
        """
        Inspect file name and content for ransom note patterns and malicious command strings.
        Returns: (matched, rule_names, description)
        """
        matches: List[str] = []
        lower_name = filename.lower()

        # Check for ransom note filename
        if lower_name in cls.RANSOM_NOTE_FILENAMES:
            matches.append("RANSOM_NOTE_FILENAME")

        # Decode sample content for regex analysis (first 64KB is sufficient)
        sample = content[:65536].decode("utf-8", errors="ignore")

        for regex in cls.RANSOM_NOTE_REGEXES:
            if regex.search(sample):
                matches.append(f"RANSOM_NOTE_PATTERN_{regex.pattern[:20]}")

        for shadow_regex in cls.SHADOW_COPY_PATTERNS:
            if shadow_regex.search(sample):
                matches.append("SHADOW_COPY_TAMPERING_INDICATOR")

        if matches:
            return True, matches, f"Matched {len(matches)} ransomware signature/heuristic rule(s)."
        return False, [], "No known ransomware signatures matched."


yara_detector = YaraHeuristicDetector()

