from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django_otp.plugins.otp_totp.models import TOTPDevice


class Command(BaseCommand):
    help = "Remove a user's authenticator so they set up 2FA again at their next login."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        user_model = get_user_model()
        try:
            user = user_model.objects.get(
                **{user_model.USERNAME_FIELD: options["username"]}
            )
        except user_model.DoesNotExist as e:
            msg = f"No user {options['username']!r}."
            raise CommandError(msg) from e
        count, _ = TOTPDevice.objects.filter(user=user).delete()
        self.stdout.write(
            f"Removed {count} authenticator(s) for {user}. "
            "They set up 2FA again at their next login."
        )
