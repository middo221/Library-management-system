from django.core.management.base import BaseCommand
from django.db import transaction

from domains.accounts.models import MemberProfile, User
from domains.accounts.services import register_member

DEMO_PASSWORD = "LibraryDemo123!"

LIBRARIANS = [("librarian@library.test", "Ada", "Shelford")]
MEMBERS = [
    ("member@library.test", "Rosa", "Quill"),
    ("theo@library.test", "Theo", "Marlowe"),
    ("nadia@library.test", "Nadia", "Okonkwo"),
]


class Command(BaseCommand):
    help = "Create one librarian and three members for local development."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        for email, first, last in LIBRARIANS:
            if User.objects.filter(email=email).exists():
                self.stdout.write(f"  = librarian {email} already exists")
                continue
            User.objects.create_librarian(
                email=email, password=DEMO_PASSWORD, first_name=first, last_name=last
            )
            self.stdout.write(self.style.SUCCESS(f"  + librarian {email}"))

        for email, first, last in MEMBERS:
            if User.objects.filter(email=email).exists():
                self.stdout.write(f"  = member {email} already exists")
                continue
            user = register_member(
                email=email, password=DEMO_PASSWORD, first_name=first, last_name=last
            )
            number = MemberProfile.objects.get(user=user).membership_number
            self.stdout.write(self.style.SUCCESS(f"  + member {email} ({number})"))

        self.stdout.write(f"\nAll seeded accounts use the password: {DEMO_PASSWORD}")
