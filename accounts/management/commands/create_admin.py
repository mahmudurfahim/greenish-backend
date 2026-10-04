import os

from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = "Create or promote the Render admin user."

    def handle(self, *args, **options):
        phone = os.getenv("DJANGO_SUPERUSER_PHONE")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
        name = os.getenv("DJANGO_SUPERUSER_NAME", "Admin")

        if not phone or not password:
            self.stdout.write(
                self.style.WARNING(
                    "DJANGO_SUPERUSER_PHONE or DJANGO_SUPERUSER_PASSWORD is not set."
                )
            )
            return

        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={"name": name},
        )

        if created:
            user.set_password(password)
        else:
            user.set_password(password)

        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Admin user {'created' if created else 'updated'} successfully."
            )
        )