"""Error reports (the 500 mails to ADMINS) without full client IPs.

Django's error mail lists request.META. Behind Caddy that includes the visitor's
full IP in X-Forwarded-For. This filter masks it like the logs do (IPv4 /24,
IPv6 /48), on top of Django's own redaction of passwords, tokens and keys.
"""

from django.views.debug import SafeExceptionReporterFilter

from config.logging_utils import mask_ip

# Headers (as META keys) that carry client addresses. Forwarded has a structured
# format (for=...;proto=...), so it is replaced as a whole.
IP_LIST_KEYS = (
    "REMOTE_ADDR",
    "HTTP_X_FORWARDED_FOR",
    "HTTP_X_REAL_IP",
    "HTTP_CF_CONNECTING_IP",
    "HTTP_TRUE_CLIENT_IP",
)
REDACT_KEYS = ("HTTP_FORWARDED",)


def _mask_ip_list(value: str) -> str:
    masked = []
    for part in str(value).split(","):
        try:
            masked.append(mask_ip(part))
        except ValueError:
            masked.append(SafeExceptionReporterFilter.cleansed_substitute)
    return ", ".join(masked)


class IPMaskingExceptionReporterFilter(SafeExceptionReporterFilter):
    def get_safe_request_meta(self, request):
        meta = super().get_safe_request_meta(request)
        for key in IP_LIST_KEYS:
            if key in meta:
                meta[key] = _mask_ip_list(meta[key])
        for key in REDACT_KEYS:
            if key in meta:
                meta[key] = self.cleansed_substitute
        return meta
