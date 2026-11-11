from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from researchit.core.client_ip import get_client_ip
from researchit.core.models import User
from researchit.website.test import HttpsClient

PASSWORD = "pw-for-tests-only"


@override_settings(AXES_FAILURE_LIMIT=3, TWO_FACTOR_REQUIRED=False)
class LoginLockoutTests(TestCase):
    client_class = HttpsClient

    def setUp(self):
        User.objects.create_superuser("editor", "editor@example.com", PASSWORD)

    def login(self, password, ip="203.0.113.5"):
        return self.client.post(
            "/cms/login/",
            {"username": "editor", "password": password},
            REMOTE_ADDR=ip,
        )

    def test_correct_password_logs_in(self):
        r = self.login(PASSWORD)
        self.assertRedirects(r, "/cms/", fetch_redirect_response=False)

    def test_locked_out_after_too_many_failures(self):
        for _ in range(2):
            assert self.login("wrong").status_code == 200
        assert self.login("wrong").status_code == 429
        # Even the right password is refused while locked out.
        r = self.login(PASSWORD)
        assert r.status_code == 429
        assert "_auth_user_id" not in self.client.session

    def test_lockout_is_per_ip(self):
        for _ in range(3):
            self.login("wrong")
        r = self.login(PASSWORD, ip="198.51.100.7")
        self.assertRedirects(r, "/cms/", fetch_redirect_response=False)

    def test_django_admin_login_is_protected(self):
        for _ in range(3):
            r = self.client.post(
                "/admin/login/",
                {"username": "editor", "password": "wrong"},
                REMOTE_ADDR="203.0.113.5",
            )
        assert r.status_code == 429

    @override_settings(
        AXES_CLIENT_IP_CALLABLE="researchit.core.client_ip.get_client_ip"
    )
    def test_lockout_uses_forwarded_ip_behind_proxy(self):
        # As in production: every request comes from Caddy's REMOTE_ADDR.
        def login(password, client_ip):
            return self.client.post(
                "/cms/login/",
                {"username": "editor", "password": password},
                REMOTE_ADDR="172.18.0.3",
                headers={"x-forwarded-for": client_ip},
            )

        for _ in range(3):
            login("wrong", "203.0.113.5")
        assert login(PASSWORD, "203.0.113.5").status_code == 429
        r = login(PASSWORD, "198.51.100.7")
        self.assertRedirects(r, "/cms/", fetch_redirect_response=False)


class ClientIpTests(SimpleTestCase):
    def ip(self, **meta):
        return get_client_ip(RequestFactory().get("/", **meta))

    def test_uses_last_forwarded_for_entry(self):
        # The first entry was sent by the client and can be forged.
        ip = self.ip(
            HTTP_X_FORWARDED_FOR="10.0.0.1, 203.0.113.5", REMOTE_ADDR="172.18.0.3"
        )
        assert ip == "203.0.113.5"

    def test_falls_back_to_remote_addr(self):
        assert self.ip(REMOTE_ADDR="172.18.0.3") == "172.18.0.3"
