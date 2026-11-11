"""Logging utilities for GDPR-compliant logging and email throttling."""

import ipaddress
import logging
import time
from collections import defaultdict


def mask_ip(value: str) -> str:
    """Mask one IP address: IPv4 keeps /24, IPv6 keeps /48.

    Raises ValueError if the value is not an IP address.
    """
    ip = ipaddress.ip_address(value.strip())
    prefix = 24 if isinstance(ip, ipaddress.IPv4Address) else 48
    return str(ipaddress.ip_network(f"{ip}/{prefix}", strict=False).network_address)


def anonymize_ip_processor(logger, method_name, event_dict):
    """Anonymize IP addresses for GDPR compliance.

    IPv4: Masks last octet (192.168.1.100 -> 192.168.1.0).
    IPv6: Masks last 80 bits (keeps /48 prefix).
    No hash of the full IP is logged: with the prefix known, an unsalted hash is
    trivially reversible (256 candidates for IPv4). Correlate via request_id.
    """
    if "ip" not in event_dict:
        return event_dict

    try:
        event_dict["ip"] = mask_ip(event_dict["ip"])
    except ValueError:
        event_dict["ip"] = "invalid"

    return event_dict


class ThrottledAdminEmailFilter(logging.Filter):
    """Throttle admin error emails to prevent inbox flooding.

    Groups errors by signature (exception type + module + function).
    Allows max 1 email per signature per throttle_seconds window.
    When an email is sent after suppression, includes a count of
    how many similar errors were suppressed.
    """

    def __init__(self, throttle_seconds=600):
        super().__init__()
        self.throttle_seconds = throttle_seconds
        self._timestamps: dict[str, float] = {}
        self._suppressed_counts: dict[str, int] = defaultdict(int)

    def _get_signature(self, record):
        exc_type = "NoException"
        if record.exc_info and record.exc_info[0]:
            exc_type = record.exc_info[0].__name__
        return f"{exc_type}:{record.module}:{record.funcName}"

    def filter(self, record):
        signature = self._get_signature(record)
        now = time.monotonic()
        # None = never sent. Not 0: monotonic() counts from boot, so a default of 0
        # would swallow every error in the first throttle_seconds after a reboot.
        last_sent = self._timestamps.get(signature)

        if last_sent is not None and now - last_sent < self.throttle_seconds:
            self._suppressed_counts[signature] += 1
            return False

        suppressed = self._suppressed_counts.pop(signature, 0)
        if suppressed > 0:
            record.msg = (
                f"[{suppressed} similar error(s) suppressed in the last "
                f"{self.throttle_seconds}s]\n{record.msg}"
            )
            record.args = ()

        self._timestamps[signature] = now
        return True
