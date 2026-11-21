import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("vaultguard.network_monitor")


class NetworkMonitorService:
    """Monitors suspicious network callbacks, C2 connections, and simulates network isolation."""

    KNOWN_C2_DOMAINS = {
        "pastebin.com", "iplogger.org", "ngrok.io", "discordapp.com/api/webhooks",
        "api.telegram.org/bot", "transfer.sh", "tempfile.ai",
    }

    KNOWN_TOR_RELAYS = {
        "185.220.101.", "185.220.102.", "198.98.51.", "192.42.116.",
    }

    def evaluate_connection(self, remote_ip: str, remote_port: int, domain: str = "") -> Tuple[bool, str]:
        """Check if an outbound endpoint connection matches known ransomware C2 or Tor proxies."""
        lower_domain = domain.lower()
        for c2 in self.KNOWN_C2_DOMAINS:
            if c2 in lower_domain:
                return True, f"Outbound connection to known C2 staging domain: '{domain}'"

        for tor_prefix in self.KNOWN_TOR_RELAYS:
            if remote_ip.startswith(tor_prefix):
                return True, f"Outbound connection to known Tor exit relay: '{remote_ip}'"

        # Check suspicious ports commonly used for raw encrypted C2 communication
        if remote_port in {4444, 5555, 6666, 1337, 31337}:
            return True, f"Connection to suspicious high-entropy port: {remote_port}"

        return False, "Connection appears benign."

    def isolate_network(self, device_id: str) -> Dict[str, Any]:
        """Trigger simulated network isolation for a quarantined endpoint."""
        logger.warning(f"[NETWORK ISOLATION] Endpoint {device_id} isolated from local subnet. Only VaultGuard cloud control channel allowed.")
        return {
            "device_id": device_id,
            "isolation_active": True,
            "allowed_destinations": ["vaultguard.internal", "localhost"],
            "blocked_destinations": ["* (All local and internet outbound dropped)"],
        }


network_monitor = NetworkMonitorService()

