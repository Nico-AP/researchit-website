import logging
import sys
from unittest import mock

from django.core import mail
from django.test import Client, RequestFactory, SimpleTestCase, override_settings
from django.urls import path

from config.logging_utils import ThrottledAdminEmailFilter, anonymize_ip_processor
from researchit.core.error_reports import _mask_ip_list


def _boom(request):
    msg = "boom"
    raise RuntimeError(msg)


urlpatterns = [path("boom/", _boom)]


class AnonymizeIpProcessorTests(SimpleTestCase):
    def process(self, ip):
        return anonymize_ip_processor(None, "info", {"event": "x", "ip": ip})

    def test_ipv4_last_octet_zeroed(self):
        self.assertEqual(self.process("203.0.113.77")["ip"], "203.0.113.0")

    def test_ipv6_keeps_only_48_bit_prefix(self):
        self.assertEqual(self.process("2001:db8:1234:5678::1")["ip"], "2001:db8:1234::")

    def test_nothing_derived_from_the_full_ip_is_logged(self):
        # A hash of the full IP next to its masked prefix is reversible (256 guesses).
        event = self.process("203.0.113.77")
        self.assertEqual(set(event), {"event", "ip"})

    def test_invalid_ip(self):
        self.assertEqual(self.process("not-an-ip")["ip"], "invalid")

    def test_events_without_ip_unchanged(self):
        self.assertEqual(
            anonymize_ip_processor(None, "info", {"event": "x"}), {"event": "x"}
        )


@override_settings(ADMINS=[("researchit", "ops@example.test")], DEBUG=False)
class ErrorMailIpMaskingTests(SimpleTestCase):
    def test_error_mail_masks_client_ips(self):
        request = RequestFactory().get(
            "/boom/",
            HTTP_HOST="localhost",
            REMOTE_ADDR="172.18.0.5",
            HTTP_X_FORWARDED_FOR="198.51.100.23, 203.0.113.77",
            HTTP_X_REAL_IP="2001:db8:1234:5678::1",
            HTTP_FORWARDED="for=192.0.2.60;proto=https",
        )
        try:
            msg = "boom"
            raise RuntimeError(msg)  # noqa: TRY301
        except RuntimeError:
            logging.getLogger("django.request").exception(
                "Internal Server Error: /boom/",
                extra={"status_code": 500, "request": request},
            )

        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        for full_ip in (
            "172.18.0.5",
            "198.51.100.23",
            "203.0.113.77",
            "2001:db8:1234:5678::1",
            "192.0.2.60",
        ):
            self.assertNotIn(full_ip, body)
        self.assertIn("HTTP_X_FORWARDED_FOR = '198.51.100.0, 203.0.113.0'", body)
        self.assertIn("HTTP_X_REAL_IP = '2001:db8:1234::'", body)
        self.assertIn("REMOTE_ADDR = '172.18.0.0'", body)

    @override_settings(ROOT_URLCONF=__name__)
    def test_one_mail_per_failed_request(self):
        # django-structlog also logs the failure ("request_failed"); only Django's
        # report (with request details) should be mailed, not a second copy.
        # The throttle is bypassed so it can't hide a duplicate.
        client = Client(raise_request_exception=False)
        with mock.patch.object(ThrottledAdminEmailFilter, "filter", return_value=True):
            response = client.get("/boom/", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Internal Server Error: /boom/", mail.outbox[0].subject)

    def test_garbage_in_ip_header_is_redacted(self):
        self.assertEqual(
            _mask_ip_list("203.0.113.77, not-an-ip"),
            "203.0.113.0, ********************",
        )


class ThrottledAdminEmailFilterTests(SimpleTestCase):
    def record(self):
        try:
            msg = "boom"
            raise RuntimeError(msg)  # noqa: TRY301
        except RuntimeError:
            return logging.LogRecord(
                "django.request",
                logging.ERROR,
                __file__,
                1,
                "Error",
                (),
                sys.exc_info(),
            )

    def test_first_error_passes_right_after_boot(self):
        # monotonic() counts from boot: a fresh server or CI runner is at a few
        # seconds, which must not look like "an error was just sent".
        log_filter = ThrottledAdminEmailFilter(throttle_seconds=300)
        with mock.patch("config.logging_utils.time.monotonic", return_value=5.0):
            self.assertTrue(log_filter.filter(self.record()))

    def test_repeats_are_throttled_then_counted(self):
        log_filter = ThrottledAdminEmailFilter(throttle_seconds=300)
        clock = mock.patch("config.logging_utils.time.monotonic")
        with clock as monotonic:
            monotonic.return_value = 1000.0
            self.assertTrue(log_filter.filter(self.record()))
            monotonic.return_value = 1100.0
            self.assertFalse(log_filter.filter(self.record()))
            monotonic.return_value = 1400.0
            record = self.record()
            self.assertTrue(log_filter.filter(record))
            self.assertIn("1 similar error(s) suppressed", record.msg)
