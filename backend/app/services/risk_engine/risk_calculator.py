from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from app.models.threat import ThreatLevel


@dataclass
class RiskEvaluationResult:
    score: float
    risk_level: str
    confidence_score: float
    action: str  # "CONTINUE", "ALERT", "QUARANTINE"
    threat_name: str
    reasons: List[str] = field(default_factory=list)
    factors: Dict[str, Any] = field(default_factory=dict)


class MultiSignalRiskEngine:
    """Calculates weighted 0-100 risk score from filesystem, cryptographic, and behavioral signals."""

    def evaluate(
        self,
        entropy_score: float = 0.0,
        write_rate: float = 0.0,
        rename_rate: float = 0.0,
        delete_rate: float = 0.0,
        extension_match: bool = False,
        extension_name: str = "",
        canary_hit: bool = False,
        process_suspicious: bool = False,
        process_details: str = "",
        yara_matches: Optional[List[str]] = None,
    ) -> RiskEvaluationResult:
        score = 0.0
        reasons: List[str] = []
        factors: Dict[str, Any] = {
            "entropy": {"score": entropy_score, "weight": 0.0},
            "write_rate": {"rate": write_rate, "weight": 0.0},
            "rename_rate": {"rate": rename_rate, "weight": 0.0},
            "delete_rate": {"rate": delete_rate, "weight": 0.0},
            "extension": {"matched": extension_match, "ext": extension_name, "weight": 0.0},
            "canary": {"hit": canary_hit, "weight": 0.0},
            "process": {"suspicious": process_suspicious, "details": process_details, "weight": 0.0},
            "yara": {"matches": yara_matches or [], "weight": 0.0},
        }

        # 1. Canary tripwire (Instant Critical)
        if canary_hit:
            score += 85.0
            factors["canary"]["weight"] = 85.0
            reasons.append("Canary decoy file integrity failure (Tripwire activated)")

        # 2. Entropy Signal
        if entropy_score >= 7.85:
            score += 35.0
            factors["entropy"]["weight"] = 35.0
            reasons.append(f"Military-grade high entropy ({entropy_score:.2f}/8.0)")
        elif entropy_score >= 7.3:
            score += 20.0
            factors["entropy"]["weight"] = 20.0
            reasons.append(f"Elevated ciphertext entropy ({entropy_score:.2f}/8.0)")

        # 3. Rename Rate Signal
        if rename_rate >= 25.0:
            score += 30.0
            factors["rename_rate"]["weight"] = 30.0
            reasons.append(f"Mass file renaming burst ({rename_rate:.1f}/min)")
        elif rename_rate >= 10.0:
            score += 15.0
            factors["rename_rate"]["weight"] = 15.0
            reasons.append(f"Elevated rename rate ({rename_rate:.1f}/min)")

        # 4. Write Rate Signal
        if write_rate >= 60.0:
            score += 25.0
            factors["write_rate"]["weight"] = 25.0
            reasons.append(f"Rapid mass file modifications ({write_rate:.1f}/min)")
        elif write_rate >= 30.0:
            score += 15.0
            factors["write_rate"]["weight"] = 15.0
            reasons.append(f"Elevated write frequency ({write_rate:.1f}/min)")

        # 5. Delete Rate Signal
        if delete_rate >= 40.0:
            score += 20.0
            factors["delete_rate"]["weight"] = 20.0
            reasons.append(f"High-frequency file deletions ({delete_rate:.1f}/min)")
        elif delete_rate >= 15.0:
            score += 10.0
            factors["delete_rate"]["weight"] = 10.0
            reasons.append(f"Elevated deletion activity ({delete_rate:.1f}/min)")

        # 6. Ransomware Extension Pattern
        if extension_match:
            score += 35.0
            factors["extension"]["weight"] = 35.0
            reasons.append(f"Known ransomware extension pattern: '{extension_name}'")

        # 7. Process Anomalies
        if process_suspicious:
            score += 40.0
            factors["process"]["weight"] = 40.0
            reasons.append(f"Hostile/suspicious process activity: {process_details}")

        # 8. YARA / Ransom Note Indicators
        if yara_matches:
            score += 40.0
            factors["yara"]["weight"] = 40.0
            reasons.append(f"Ransom note signatures: {', '.join(yara_matches)}")

        # Clamp composite score to [0.0, 100.0]
        final_score = min(100.0, max(0.0, round(score, 1)))

        # Determine Risk Level and Recommended Action
        if final_score >= 90.0:
            risk_level = ThreatLevel.CRITICAL.value
            action = "QUARANTINE"
            confidence = 0.98
            threat_name = "Ransomware.Active.EncryptionOutbreak"
        elif final_score >= 70.0:
            risk_level = ThreatLevel.HIGH.value
            action = "QUARANTINE"
            confidence = 0.88
            threat_name = "Ransomware.Generic.Heuristic"
        elif final_score >= 40.0:
            risk_level = ThreatLevel.MEDIUM.value
            action = "ALERT"
            confidence = 0.65
            threat_name = "Suspicious.FileActivity.Anomaly"
        else:
            risk_level = ThreatLevel.LOW.value
            action = "CONTINUE"
            confidence = 0.25
            threat_name = "Benign.Activity"

        return RiskEvaluationResult(
            score=final_score,
            risk_level=risk_level,
            confidence_score=confidence,
            action=action,
            threat_name=threat_name,
            reasons=reasons,
            factors=factors,
        )


risk_engine = MultiSignalRiskEngine()

