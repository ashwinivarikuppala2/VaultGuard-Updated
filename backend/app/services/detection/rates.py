import threading
import time
from collections import defaultdict, deque
from typing import Dict, Tuple


class SlidingWindowRateTracker:
    """Thread-safe rate monitoring for write, rename, and delete frequencies per device."""

    def __init__(self, window_seconds: float = 60.0) -> None:
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        # device_id -> event_type -> deque of timestamps
        self._events: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(deque))

    def record_event(self, device_id: str, event_type: str) -> float:
        """
        Record a filesystem operation (e.g. 'write', 'rename', 'delete').
        Returns the current operations-per-minute rate for that event type on that device.
        """
        now = time.time()
        with self._lock:
            q = self._events[device_id][event_type]
            q.append(now)

            # Evict timestamps older than sliding window
            cutoff = now - self.window_seconds
            while q and q[0] < cutoff:
                q.popleft()

            count = len(q)
            # Scale to operations per minute
            rate = (count / self.window_seconds) * 60.0
            return round(rate, 2)

    def get_current_rates(self, device_id: str) -> Dict[str, float]:
        """Get instantaneous rates for write, rename, and delete for a given device."""
        now = time.time()
        cutoff = now - self.window_seconds
        rates = {"write_rate": 0.0, "rename_rate": 0.0, "delete_rate": 0.0}

        with self._lock:
            dev_events = self._events.get(device_id, {})
            for event_type, key in [("write", "write_rate"), ("rename", "rename_rate"), ("delete", "delete_rate")]:
                q = dev_events.get(event_type, deque())
                while q and q[0] < cutoff:
                    q.popleft()
                rates[key] = round((len(q) / self.window_seconds) * 60.0, 2)

        return rates

    def evaluate_rate_anomaly(
        self,
        device_id: str,
        write_threshold: float = 60.0,
        rename_threshold: float = 25.0,
        delete_threshold: float = 40.0,
    ) -> Tuple[bool, Dict[str, float], str]:
        """
        Evaluate if current filesystem rates indicate rapid mass file operations.
        Returns: (is_anomalous, current_rates, rationale)
        """
        rates = self.get_current_rates(device_id)
        is_anomalous = False
        reasons = []

        if rates["rename_rate"] >= rename_threshold:
            is_anomalous = True
            reasons.append(f"Abnormal rename frequency: {rates['rename_rate']:.1f}/min (threshold: {rename_threshold})")

        if rates["write_rate"] >= write_threshold:
            is_anomalous = True
            reasons.append(f"Mass file write spike: {rates['write_rate']:.1f}/min (threshold: {write_threshold})")

        if rates["delete_rate"] >= delete_threshold:
            is_anomalous = True
            reasons.append(f"Mass file deletion spike: {rates['delete_rate']:.1f}/min (threshold: {delete_threshold})")

        rationale = " | ".join(reasons) if reasons else "File operation rates within normal parameters."
        return is_anomalous, rates, rationale


rate_tracker = SlidingWindowRateTracker()

