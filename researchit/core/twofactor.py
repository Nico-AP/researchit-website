"""Two-factor authentication (TOTP) for everyone with admin access.

Built directly on django-otp (wagtail-2fa doesn't support Wagtail 8).

Flow: a user signs in with username + password as usual (Wagtail or Django admin login).
Before any admin page is shown, RequireOTPMiddleware sends them to
- /cms/2fa/setup/  if they have no authenticator yet: scan the QR code, confirm a code,
- /cms/2fa/verify/ otherwise: enter the 6-digit code from the app.
Wrong codes are throttled with exponential back-off (django-otp's ThrottlingMixin).

Lost the phone? On the server: `just manage reset_2fa <username>`, then set up again.
"""

from base64 import b32encode

import qrcode
import qrcode.image.svg
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe
from django_otp import login as otp_login
from django_otp import user_has_device
from django_otp.plugins.otp_totp.models import TOTPDevice

# Views an authenticated but not yet verified admin user may still reach.
EXEMPT_VIEWS = {
    "otp_setup",
    "otp_verify",
    "wagtailadmin_login",
    "wagtailadmin_logout",
    "admin:login",
    "admin:logout",
    # Assets the admin page loads via JS (icons, translations) - not content.
    "wagtailadmin_sprite",
    "wagtailadmin_javascript_catalog",
}


def has_admin_access(user) -> bool:
    return (
        user.is_staff or user.is_superuser or user.has_perm("wagtailadmin.access_admin")
    )


def _protected_prefixes() -> tuple[str, ...]:
    # /documents/ too: private Wagtail documents are served to logged-in users.
    return (f"/{settings.ADMIN_URL}", f"/{settings.WAGTAILADMIN_URL}", "/documents/")


class RequireOTPMiddleware:
    """Require a verified second factor for admin users on admin URLs.

    Must come after django_otp.middleware.OTPMiddleware (which adds user.is_verified()).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not settings.TWO_FACTOR_REQUIRED:
            return None
        if not request.path.startswith(_protected_prefixes()):
            return None
        user = request.user
        if (
            not user.is_authenticated
            or not has_admin_access(user)
            or user.is_verified()
        ):
            return None
        if request.resolver_match and request.resolver_match.view_name in EXEMPT_VIEWS:
            return None
        target = "otp_verify" if user_has_device(user, confirmed=True) else "otp_setup"
        return redirect(f"{reverse(target)}?next={request.get_full_path()}")


class TokenForm(forms.Form):
    token = forms.CharField(
        label="Authentication code",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "autofocus": True,
            },
        ),
    )


def _next_url(request) -> str:
    url = request.POST.get("next") or request.GET.get("next")
    if url and url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return url
    return reverse("wagtailadmin_home")


def _check_token(device: TOTPDevice, form: TokenForm) -> bool:
    """Validate the code; on failure add an error to the form."""
    allowed, _ = device.verify_is_allowed()
    if not allowed:
        form.add_error(None, "Too many wrong codes. Wait a moment, then try again.")
        return False
    if device.verify_token(form.cleaned_data["token"]):
        return True
    form.add_error(
        "token", "This code is not valid. Check the time on your phone and try again."
    )
    return False


@login_required(login_url="wagtailadmin_login")
def verify(request):
    device = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
    if device is None:
        return redirect(f"{reverse('otp_setup')}?next={_next_url(request)}")
    if request.user.is_verified():
        return redirect(_next_url(request))

    form = TokenForm(request.POST or None)
    if request.method == "POST" and form.is_valid() and _check_token(device, form):
        otp_login(request, device)
        return redirect(_next_url(request))
    return render(
        request,
        "core/twofactor/verify.html",
        {"form": form, "next": _next_url(request)},
    )


@login_required(login_url="wagtailadmin_login")
def setup(request):
    if user_has_device(request.user, confirmed=True):
        return redirect(f"{reverse('otp_verify')}?next={_next_url(request)}")

    device = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
    if device is None:
        device = TOTPDevice.objects.create(
            user=request.user, name="Authenticator app", confirmed=False
        )

    form = TokenForm(request.POST or None)
    if request.method == "POST" and form.is_valid() and _check_token(device, form):
        device.confirmed = True
        device.save(update_fields=["confirmed"])
        otp_login(request, device)
        messages.success(request, "Two-factor authentication is set up.")
        return redirect(_next_url(request))

    qr_svg = qrcode.make(
        device.config_url, image_factory=qrcode.image.svg.SvgPathImage, box_size=8
    )
    secret = b32encode(device.bin_key).decode()
    context = {
        "form": form,
        "next": _next_url(request),
        # Generated locally from our own data - safe to inline.
        "qr_svg": mark_safe(qr_svg.to_string(encoding="unicode")),  # noqa: S308
        "secret": " ".join(secret[i : i + 4] for i in range(0, len(secret), 4)),
    }
    return render(request, "core/twofactor/setup.html", context)


urlpatterns = [
    path("verify/", verify, name="otp_verify"),
    path("setup/", setup, name="otp_setup"),
]
