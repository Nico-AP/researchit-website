from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from researchit.core.models import User
from researchit.website.test import HttpsClient


def current_code(device: TOTPDevice) -> str:
    code = totp(device.bin_key, step=device.step, t0=device.t0, digits=device.digits)
    return f"{code:06d}"


@override_settings(TWO_FACTOR_REQUIRED=True)  # regardless of a local .env
class TwoFactorTests(TestCase):
    client_class = HttpsClient

    def setUp(self):
        self.admin = User.objects.create_superuser(
            "editor", "editor@example.com", "pw-for-tests-only"
        )
        self.client.force_login(self.admin)

    def confirmed_device(self) -> TOTPDevice:
        return TOTPDevice.objects.create(user=self.admin, name="app", confirmed=True)

    def test_admin_without_device_is_sent_to_setup(self):
        for url in ["/cms/", "/admin/", "/cms/pages/"]:
            r = self.client.get(url)
            self.assertRedirects(
                r, f"/cms/2fa/setup/?next={url}", fetch_redirect_response=False
            )

    def test_setup_confirms_device_and_grants_access(self):
        r = self.client.get("/cms/2fa/setup/?next=/cms/pages/")
        self.assertContains(r, "<svg")
        device = TOTPDevice.objects.get(user=self.admin, confirmed=False)

        r = self.client.post(
            "/cms/2fa/setup/", {"token": current_code(device), "next": "/cms/pages/"}
        )
        self.assertRedirects(r, "/cms/pages/", fetch_redirect_response=False)
        device.refresh_from_db()
        assert device.confirmed
        assert self.client.get("/cms/").status_code == 200

    def test_admin_with_device_must_verify(self):
        device = self.confirmed_device()
        r = self.client.get("/cms/")
        self.assertRedirects(
            r, "/cms/2fa/verify/?next=/cms/", fetch_redirect_response=False
        )

        r = self.client.post("/cms/2fa/verify/", {"token": "000000", "next": "/cms/"})
        self.assertContains(r, "not valid")
        device.throttle_reset()

        r = self.client.post(
            "/cms/2fa/verify/", {"token": current_code(device), "next": "/admin/"}
        )
        self.assertRedirects(r, "/admin/", fetch_redirect_response=False)
        assert self.client.get("/admin/").status_code == 200

    def test_wrong_codes_are_throttled(self):
        device = self.confirmed_device()
        self.client.post("/cms/2fa/verify/", {"token": "000000"})
        r = self.client.post("/cms/2fa/verify/", {"token": current_code(device)})
        self.assertContains(r, "Too many wrong codes")
        assert self.client.get("/cms/").status_code == 302

    def test_setup_is_not_reachable_once_a_device_exists(self):
        self.confirmed_device()
        r = self.client.get("/cms/2fa/setup/")
        self.assertRedirects(
            r, "/cms/2fa/verify/?next=/cms/", fetch_redirect_response=False
        )

    def test_next_must_stay_on_site(self):
        device = self.confirmed_device()
        r = self.client.post(
            "/cms/2fa/verify/",
            {"token": current_code(device), "next": "https://evil.example/"},
        )
        self.assertRedirects(r, "/cms/", fetch_redirect_response=False)

    def test_public_site_admin_assets_and_logout_are_not_blocked(self):
        assert self.client.get("/").status_code == 200
        # The 2FA pages themselves load the icon sprite via JS.
        assert self.client.get("/cms/sprite/").status_code == 200
        r = self.client.post("/cms/logout/")
        self.assertRedirects(r, "/cms/login/", fetch_redirect_response=False)

    def test_anonymous_users_get_the_normal_login(self):
        self.client.logout()
        r = self.client.get("/cms/2fa/verify/")
        assert r.status_code == 302
        assert r["Location"].startswith("/cms/login/")

    @override_settings(TWO_FACTOR_REQUIRED=False)
    def test_can_be_disabled(self):
        assert self.client.get("/cms/").status_code == 200

    def test_reset_command_removes_devices(self):
        self.confirmed_device()
        call_command("reset_2fa", "editor", stdout=StringIO())
        assert not TOTPDevice.objects.filter(user=self.admin).exists()
