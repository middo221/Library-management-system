"""One command that produces a library mid-week: loans out, some overdue, a hold queue,
unpaid fines. Everything the UI needs to look like a real working day."""

import random
from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from domains.accounts.models import User
from domains.catalog.models import Book, BookCopy
from domains.circulation.models import Fine, Loan, Reservation
from domains.circulation.policy import get_policy
from domains.circulation.services import reserve


class Command(BaseCommand):
    help = "Seed users, catalogue and a realistic circulation state (overdues, holds, fines)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--seed", type=int, default=7)

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        rng = random.Random(options["seed"])
        policy = get_policy()

        call_command("seed_users")
        call_command("seed_catalog")

        librarian = User.objects.filter(role=User.Role.LIBRARIAN).first()
        members = list(User.objects.filter(role=User.Role.MEMBER).order_by("id"))
        if not members:
            self.stderr.write("No members to lend to.")
            return

        if Loan.objects.exists():
            self.stdout.write("Circulation data already present — leaving it alone.")
            return

        today = timezone.localdate()
        available = list(
            BookCopy.objects.filter(status=BookCopy.Status.AVAILABLE).order_by("barcode")
        )
        rng.shuffle(available)

        loans_created = overdue_created = 0

        # A spread of current loans: mostly healthy, a few well past due.
        for index, copy in enumerate(available[:14]):
            member = members[index % len(members)]
            days_ago = rng.randint(1, 25)
            checked_out = timezone.now() - timedelta(days=days_ago)
            due_on = checked_out.date() + timedelta(days=policy.loan_period_days)

            loan = Loan.objects.create(
                copy=copy,
                member=member,
                checked_out_by=librarian,
                checked_out_at=checked_out,
                due_on=due_on,
            )
            copy.status = BookCopy.Status.ON_LOAN
            copy.save(update_fields=["status"])
            loans_created += 1

            if due_on < today:
                overdue_created += 1
                days_overdue = (today - due_on).days
                cap = copy.replacement_cost or policy.default_replacement_cost
                amount = min(policy.overdue_fine_per_day * days_overdue, cap)
                if rng.random() < 0.5:
                    Fine.objects.create(
                        loan=loan,
                        member=member,
                        amount=amount,
                        reason=Fine.Reason.OVERDUE,
                        assessed_on=today,
                    )

        # A queue needs a title with nothing on the shelf, otherwise every reservation goes
        # straight to READY and there is no waiting list to look at.
        fully_out_books = list(
            Book.objects.filter(copies__status=BookCopy.Status.ON_LOAN)
            .exclude(copies__status=BookCopy.Status.AVAILABLE)
            .distinct()[:2]
        )
        reservations_created = 0
        for book in fully_out_books:
            for member in members[:3]:
                already_borrowed = Loan.objects.filter(
                    copy__book=book, member=member, returned_at__isnull=True
                ).exists()
                if already_borrowed:
                    continue
                try:
                    reserve(book=book, member=member)
                    reservations_created += 1
                except Exception as exc:
                    self.stdout.write(f"  skipped reservation for {member.email}: {exc}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready: {loans_created} loans ({overdue_created} overdue), "
                f"{reservations_created} reservations, "
                f"{Fine.objects.count()} fines, "
                f"{Reservation.objects.filter(status=Reservation.Status.PENDING).count()} waiting."
            )
        )
