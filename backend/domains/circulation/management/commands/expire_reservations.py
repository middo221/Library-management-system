from django.core.management.base import BaseCommand

from domains.circulation.services import expire_stale_reservations


class Command(BaseCommand):
    help = (
        "Expire READY reservations left on the hold shelf past their date and offer each copy "
        "to the next member in the queue. Intended to run daily."
    )

    def handle(self, *args, **options) -> None:
        count = expire_stale_reservations()
        self.stdout.write(self.style.SUCCESS(f"Expired {count} stale reservation(s)."))
