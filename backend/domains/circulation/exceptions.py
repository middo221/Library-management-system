from domains.common import error_codes
from domains.common.exceptions import ConflictError, NotFoundError


class LoanNotFound(NotFoundError):
    message = "No loan with that id exists."


class ReservationNotFound(NotFoundError):
    message = "No reservation with that id exists."


class FineNotFound(NotFoundError):
    message = "No fine with that id exists."


class CopyNotAvailable(ConflictError):
    code = error_codes.COPY_NOT_AVAILABLE
    message = "That copy is not on the shelf."


class LoanLimitReached(ConflictError):
    code = error_codes.LOAN_LIMIT_REACHED
    message = "This member has reached the borrowing limit."


class MembershipSuspended(ConflictError):
    code = error_codes.MEMBERSHIP_SUSPENDED
    message = "This membership is suspended and cannot borrow."


class MembershipExpired(ConflictError):
    code = error_codes.MEMBERSHIP_EXPIRED
    message = "This membership has expired. Renew it before borrowing."


class UnpaidFines(ConflictError):
    code = error_codes.UNPAID_FINES
    message = "This member has unpaid fines above the borrowing threshold."


class CopyHeldForOtherMember(ConflictError):
    code = error_codes.COPY_HELD_FOR_OTHER_MEMBER
    message = "This copy is being held for another member's reservation."


class LoanAlreadyReturned(ConflictError):
    code = error_codes.LOAN_ALREADY_RETURNED
    message = "This loan has already been checked in."


class RenewalLimitReached(ConflictError):
    code = error_codes.RENEWAL_LIMIT_REACHED
    message = "This loan has already been renewed the maximum number of times."


class RenewalBlockedOverdue(ConflictError):
    code = error_codes.RENEWAL_BLOCKED_OVERDUE
    message = "An overdue loan cannot be renewed. Return it at the desk."


class RenewalBlockedReserved(ConflictError):
    code = error_codes.RENEWAL_BLOCKED_RESERVED
    message = "Another member is waiting for this title, so it cannot be renewed."


class DuplicateReservation(ConflictError):
    code = error_codes.DUPLICATE_RESERVATION
    message = "You already have an active reservation for this title."


class AlreadyOnLoanByMember(ConflictError):
    code = error_codes.ALREADY_ON_LOAN_BY_MEMBER
    message = "You already have a copy of this title on loan."


class ReservationNotActive(ConflictError):
    code = error_codes.RESERVATION_NOT_ACTIVE
    message = "This reservation is no longer active."


class ReservationNotReady(ConflictError):
    code = error_codes.RESERVATION_NOT_READY
    message = "This reservation is not ready for collection yet."


class NoCopyAvailable(ConflictError):
    code = error_codes.NO_COPY_AVAILABLE
    message = "No copy of this title is on the shelf."


class FineAlreadySettled(ConflictError):
    code = error_codes.FINE_ALREADY_SETTLED
    message = "This fine has already been paid or waived."
