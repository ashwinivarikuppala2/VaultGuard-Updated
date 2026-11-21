import math
from typing import Tuple


class EntropyDetector:
    """Shannon entropy calculator for byte buffers and anomaly detection."""

    @staticmethod
    def calculate_shannon_entropy(data: bytes) -> float:
        """Compute Shannon entropy H(X) = -sum(p * log2(p)) in range [0.0, 8.0]."""
        if not data:
            return 0.0

        length = len(data)
        byte_counts = [0] * 256
        for byte in data:
            byte_counts[byte] += 1

        entropy = 0.0
        for count in byte_counts:
            if count > 0:
                p = count / length
                entropy -= p * math.log2(p)

        return round(entropy, 4)

    @classmethod
    def evaluate_entropy_anomaly(
        cls,
        current_data: bytes,
        previous_entropy: float = 0.0,
        threshold: float = 7.3,
        delta_threshold: float = 2.0,
    ) -> Tuple[float, bool, str]:
        """
        Evaluate if data exhibits characteristics of ransomware ciphertext or compression.
        Returns: (entropy_score, is_suspicious, rationale)
        """
        score = cls.calculate_shannon_entropy(current_data)
        delta = score - previous_entropy if previous_entropy > 0 else 0.0

        if score >= 7.85:
            return score, True, f"Extremely high entropy ({score:.2f}/8.0) consistent with military-grade ciphertext."
        elif score >= threshold and delta >= delta_threshold:
            return score, True, f"Sharp entropy surge ({previous_entropy:.2f} -> {score:.2f}, delta +{delta:.2f}) indicates mass file encryption."
        elif score >= threshold:
            return score, True, f"High entropy ({score:.2f}/8.0) above threshold ({threshold})."
        
        return score, False, f"Normal entropy ({score:.2f}/8.0)."


entropy_detector = EntropyDetector()

