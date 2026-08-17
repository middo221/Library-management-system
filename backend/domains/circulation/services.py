"""Circulation workflows — the actual product.

Every rule in the plan's rules table is enforced here and nowhere else. Views call these
functions; models hold invariants; the database holds the two constraints that concurrency
could otherwise defeat.
"""

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from domains.accounts.models import User
from domains.catalog.models import Book, BookCopy
from domains.circulation.exceptions import (
    AlreadyOnLoanByMember,
    CopyHeldForOtherMember,
    CopyNotAvailable,
    DuplicateReservation,
    FineAlreadySettled,
    LoanAlreadyReturned,
    LoanLimitReached,
    MembershipExpired,
    MembershipSuspended,
    NoCopyAvailable,
    RenewalBlockedOverdue,
    RenewalBlockedReserved,
    RenewalLimitReached,
    ReservationNotActive,
    ReservationNotReady,
    UnpaidFines,
)
from domains.circulation.models import Fine, Loan, Reservation
from domains.circulation.policy import get_policy
from domains.common.exceptions import ValidationError
from domains.common.logging import log_action

CENTS = Decimal("0.01")


# --------------------------------------------------------------------------------------
# Eligibility
# --------------------------------------------------------------------------------------


def outstanding_fine_total(member: User) -> Decimal:
    total = Fine.objects.filter(
        member=member, paid_at__isnull=True, waived_at__isnull=True
    ).aggregate(total=Sum("amount"))["total"]
    return Decimal(total or 0)


def assert_member_can_borrow(member: User, *, check_loan_cap: bool = True) -> None:
    """Shared gate for checkout and reservation. Each failure has its own code so the UI can
    say what to do about it rather than 'not allowed'."""
    policy = get_policy()
    profile = getattr(member, "member_profile", None)

    if profile is None or not member.is_member:
        raise ValidationError("That user is not a borrowing member.")

    if not member.is_active or profile.is_suspended:
        raise MembershipSuspended(
            details={"reason": profile.suspension_reason} if profile.suspension_reason else {}
        )

    if profile.is_expired:
        raise MembershipExpired(details={"expired_on": str(profile.membership_expires_on)})

    if check_loan_cap:
        active_loans = Loan.objects.filter(member=member, returned_at__isnull=True).count()
        if active_loans >= policy.max_active_loans:
            raise LoanLimitReached(
                f"Member already has {active_loans} active loans.",
                details={"active_loans": active_loans, "limit": policy.max_active_loans},
            )

    owed = outstanding_fine_total(member)
    if owed >= policy.unpaid_fine_block_threshold:
        raise UnpaidFines(
            details={"outstanding": str(owed), "threshold": str(policy.unpaid_fine_block_threshold)}
        )


# --------------------------------------------------------------------------------------
# Checkout / check-in
# --------------------------------------------------------------------------------------


@transaction.atomic
def checkout(*, barcode: str, member: User, librarian: User) -> Loan:
    policy = get_policy()

    # Lock the row first: two desks scanning the same barcode must serialise here, and the
    # partial unique index on Loan is the backstop if they somehow do not.
    copy = (
        BookCopy.objects.select_for_update()
        .select_related("book")
        .filter(barcode=barcode.strip())
        .first()
    )
    if copy is None:
        raise CopyNotAvailable("No copy with that barcode exists.", status_code=404)

    member_hold = (
        Reservation.objects.filter(
            book_id=copy.book_id, member=member, status=Reservation.Status.READY
        )
        .order_by("reserved_at")
        .first()
    )

    if copy.status == BookCopy.Status.RESERVED:
        holder = (
            Reservation.objects.filter(held_copy=copy, status=Reservation.Status.READY)
            .select_related("member")
            .first()
        )
        if holder is not None and holder.member_id != member.id:
            raise CopyHeldForOtherMember(
                details={"held_for": holder.member.member_profile.membership_number}
            )
        member_hold = holder or member_hold
    elif copy.status != BookCopy.Status.AVAILABLE:
        raise CopyNotAvailable(
            f"Copy {copy.barcode} is marked {copy.get_status_display().lower()}.",
            details={"barcode": copy.barcode, "status": copy.status},
        )

    assert_member_can_borrow(member)

    if Loan.objects.filter(copy=copy, returned_at__isnull=True).exists():
        raise CopyNotAvailable("That copy is already on loan.", details={"barcode": copy.barcode})

    loan = Loan.objects.create(
        copy=copy,
        member=member,
        checked_out_by=librarian,
        due_on=timezone.localdate() + timedelta(days=policy.loan_period_days),
    )

    copy.status = BookCopy.Status.ON_LOAN
    copy.save(update_fields=["status", "updated_at"])

    if member_hold is not None:
        member_hold.status = Reservation.Status.FULFILLED
        member_hold.held_copy = copy
        member_hold.save(update_fields=["status", "held_copy", "updated_at"])

    log_action(
        "loan.checked_out",
        actor=librarian,
        loan_id=loan.id,
        barcode=copy.barcode,
        member_id=member.id,
        due_on=loan.due_on,
    )
    return loan


def _assess_overdue_fine(loan: Loan) -> Fine | None:
    """0.50/day, capped at the copy's replacement cost. Returns ``None`` when nothing is owed."""
    if not loan.is_overdue or loan.days_overdue <= 0:
        return None
    if hasattr(loan, "fine"):
        return loan.fine

    policy = get_policy()
    cap = loan.copy.replacement_cost or policy.default_replacement_cost
    amount = min(policy.overdue_fine_per_day * loan.days_overdue, cap)

    return Fine.objects.create(
        loan=loan,
        member=loan.member,
        amount=amount.quantize(CENTS, rounding=ROUND_HALF_UP),
        reason=Fine.Reason.OVERDUE,
    )


def _promote_next_reservation(copy: BookCopy) -> Reservation | None:
    """Give a returned copy to the front of the queue, if anyone is waiting for the title."""
    policy = get_policy()
    next_up = (
        Reservation.objects.select_for_update()
        .filter(book_id=copy.book_id, status=Reservation.Status.PENDING)
        .order_by("reserved_at")
        .first()
    )
    if next_up is None:
        return None

    next_up.status = Reservation.Status.READY
    next_up.ready_at = timezone.now()
    next_up.expires_on = timezone.localdate() + timedelta(days=policy.hold_shelf_days)
    next_up.held_copy = copy
    next_up.save(update_fields=["status", "ready_at", "expires_on", "held_copy", "updated_at"])
    return next_up


@transaction.atomic
def return_loan(*, loan: Loan, librarian: User) -> dict:
    if loan.returned_at is not None:
        raise LoanAlreadyReturned(details={"returned_at": loan.returned_at.isoformat()})

    copy = BookCopy.objects.select_for_update().get(pk=loan.copy_id)

    loan.returned_at = timezone.now()
    loan.checked_in_by = librarian
    loan.save(update_fields=["returned_at", "checked_in_by", "updated_at"])

    fine = _assess_overdue_fine(loan)
    held_for = _promote_next_reservation(copy)

    copy.status = BookCopy.Status.RESERVED if held_for else BookCopy.Status.AVAILABLE
    copy.save(update_fields=["status", "updated_at"])

    log_action(
        "loan.returned",
        actor=librarian,
        loan_id=loan.id,
        barcode=copy.barcode,
        member_id=loan.member_id,
        fine=str(fine.amount) if fine else "none",
        held_for=held_for.member_id if held_for else "none",
    )
    return {"loan": loan, "fine": fine, "reservation": held_for, "copy": copy}


@transaction.atomic
def renew_loan(*, loan: Loan, actor: User) -> Loan:
    policy = get_policy()

    if loan.returned_at is not None:
        raise LoanAlreadyReturned()

    if loan.renewal_count >= policy.max_renewals:
        raise RenewalLimitReached(
            details={"renewal_count": loan.renewal_count, "limit": policy.max_renewals}
        )

    if loan.is_overdue:
        raise RenewalBlockedOverdue(details={"days_overdue": loan.days_overdue})

    if Reservation.objects.filter(
        book_id=loan.copy.book_id, status__in=Reservation.ACTIVE_STATUSES
    ).exists():
        raise RenewalBlockedReserved()

    loan.due_on = max(loan.due_on, timezone.localdate()) + timedelta(days=policy.loan_period_days)
    loan.renewal_count += 1
    loan.save(update_fields=["due_on", "renewal_count", "updated_at"])

    log_action(
        "loan.renewed",
        actor=actor,
        loan_id=loan.id,
        due_on=loan.due_on,
        renewal_count=loan.renewal_count,
    )
    return loan


# --------------------------------------------------------------------------------------
# Reservations
# --------------------------------------------------------------------------------------


@transaction.atomic
def reserve(*, book: Book, member: User) -> Reservation:
    policy = get_policy()

    # The loan cap governs what you may hold, not what you may queue for.
    assert_member_can_borrow(member, check_loan_cap=False)

    if Reservation.objects.filter(
        book=book, member=member, status__in=Reservation.ACTIVE_STATUSES
    ).exists():
        raise DuplicateReservation()

    if Loan.objects.filter(copy__book=book, member=member, returned_at__isnull=True).exists():
        raise AlreadyOnLoanByMember()

    reservation = Reservation.objects.create(book=book, member=member)

    # If something is already on the shelf, hold it now rather than making the member wait
    # for a return that will never come.
    free_copy = (
        BookCopy.objects.select_for_update()
        .filter(book=book, status=BookCopy.Status.AVAILABLE)
        .order_by("barcode")
        .first()
    )
    if free_copy is not None:
        reservation.status = Reservation.Status.READY
        reservation.ready_at = timezone.now()
        reservation.expires_on = timezone.localdate() + timedelta(days=policy.hold_shelf_days)
        reservation.held_copy = free_copy
        reservation.save(
            update_fields=["status", "ready_at", "expires_on", "held_copy", "updated_at"]
        )

        free_copy.status = BookCopy.Status.RESERVED
        free_copy.save(update_fields=["status", "updated_at"])

    log_action(
        "reservation.created",
        actor=member,
        reservation_id=reservation.id,
        book_id=book.id,
        status=reservation.status,
    )
    return reservation


def _release_held_copy(reservation: Reservation) -> None:
    """Put a held copy back into play, offering it to the next in the queue first."""
    if reservation.held_copy_id is None:
        return

    copy = BookCopy.objects.select_for_update().get(pk=reservation.held_copy_id)
    if copy.status != BookCopy.Status.RESERVED:
        return

    next_up = _promote_next_reservation(copy)
    copy.status = BookCopy.Status.RESERVED if next_up else BookCopy.Status.AVAILABLE
    copy.save(update_fields=["status", "updated_at"])


@transaction.atomic
def cancel_reservation(*, reservation: Reservation, actor: User) -> Reservation:
    if not reservation.is_active:
        raise ReservationNotActive(details={"status": reservation.status})

    was_ready = reservation.status == Reservation.Status.READY

    reservation.status = Reservation.Status.CANCELLED
    reservation.save(update_fields=["status", "updated_at"])

    if was_ready:
        _release_held_copy(reservation)

    log_action("reservation.cancelled", actor=actor, reservation_id=reservation.id)
    return reservation


@transaction.atomic
def fulfil_reservation(*, reservation: Reservation, librarian: User) -> Loan:
    """Turn a hold into a loan at the desk."""
    if not reservation.is_active:
        raise ReservationNotActive(details={"status": reservation.status})

    copy = None
    if reservation.held_copy_id is not None:
        copy = BookCopy.objects.select_for_update().get(pk=reservation.held_copy_id)
        if copy.status not in (BookCopy.Status.RESERVED, BookCopy.Status.AVAILABLE):
            copy = None

    if copy is None:
        if reservation.status == Reservation.Status.READY:
            raise ReservationNotReady("The held copy is no longer on the hold shelf.")
        copy = (
            BookCopy.objects.select_for_update()
            .filter(book_id=reservation.book_id, status=BookCopy.Status.AVAILABLE)
            .order_by("barcode")
            .first()
        )
    if copy is None:
        raise NoCopyAvailable()

    # Free the copy so ``checkout`` sees a clean shelf state, then let it apply every
    # borrowing rule exactly as it would at the desk.
    copy.status = BookCopy.Status.AVAILABLE
    copy.save(update_fields=["status", "updated_at"])

    loan = checkout(barcode=copy.barcode, member=reservation.member, librarian=librarian)

    reservation.refresh_from_db()
    if reservation.status != Reservation.Status.FULFILLED:
        reservation.status = Reservation.Status.FULFILLED
        reservation.held_copy = copy
        reservation.save(update_fields=["status", "held_copy", "updated_at"])

    log_action(
        "reservation.fulfilled", actor=librarian, reservation_id=reservation.id, loan_id=loan.id
    )
    return loan


@transaction.atomic
def expire_stale_reservations() -> int:
    """Move READY holds past their shelf date to EXPIRED and offer the copy on."""
    today = timezone.localdate()
    stale = list(
        Reservation.objects.select_for_update()
        .filter(status=Reservation.Status.READY, expires_on__lt=today)
        .select_related("held_copy")
    )

    for reservation in stale:
        reservation.status = Reservation.Status.EXPIRED
        reservation.save(update_fields=["status", "updated_at"])
        _release_held_copy(reservation)
        log_action("reservation.expired", reservation_id=reservation.id)

    return len(stale)


# --------------------------------------------------------------------------------------
# Fines
# --------------------------------------------------------------------------------------


@transaction.atomic
def pay_fine(*, fine: Fine, librarian: User) -> Fine:
    if not fine.is_outstanding:
        raise FineAlreadySettled(details={"status": fine.status})

    fine.paid_at = timezone.now()
    fine.save(update_fields=["paid_at", "updated_at"])

    log_action("fine.paid", actor=librarian, fine_id=fine.id, amount=str(fine.amount))
    return fine


@transaction.atomic
def waive_fine(*, fine: Fine, librarian: User, reason: str) -> Fine:
    if not fine.is_outstanding:
        raise FineAlreadySettled(details={"status": fine.status})
    if not reason.strip():
        raise ValidationError(
            "A reason is required to waive a fine.", details={"reason": "Required."}
        )

    fine.waived_at = timezone.now()
    fine.waived_by = librarian
    fine.waiver_reason = reason.strip()
    fine.save(update_fields=["waived_at", "waived_by", "waiver_reason", "updated_at"])

    log_action("fine.waived", actor=librarian, fine_id=fine.id, reason=fine.waiver_reason)
    return fine


@transaction.atomic
def assess_manual_fine(*, loan: Loan, amount: Decimal, reason: str, librarian: User) -> Fine:
    """Damage and loss are judgement calls made at the desk, not derived from dates."""
    if hasattr(loan, "fine"):
        raise FineAlreadySettled("This loan already has a fine attached.")

    fine = Fine.objects.create(
        loan=loan,
        member=loan.member,
        amount=Decimal(amount).quantize(CENTS, rounding=ROUND_HALF_UP),
        reason=reason,
    )
    log_action("fine.assessed", actor=librarian, fine_id=fine.id, loan_id=loan.id, reason=reason)
    return fine
