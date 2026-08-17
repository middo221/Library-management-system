# API errors

Every failure — validation, permission, business rule, or crash — comes back in one shape:

```json
{
  "error": {
    "code": "LOAN_LIMIT_REACHED",
    "message": "Member already has 5 active loans.",
    "details": { "active_loans": 5, "limit": 5 }
  }
}
```

`code` is stable and safe to branch on. `message` is written for a person and can be shown
directly. `details` is advisory: present when there is something useful to say, `{}` otherwise.

Codes are declared in `backend/domains/common/error_codes.py`. Adding a failure mode means adding
it there and here.

## Generic

| Code | Status | When |
|---|---|---|
| `VALIDATION_ERROR` | 400 | A request DTO rejected the body. `details` is keyed by field name. |
| `NOT_AUTHENTICATED` | 401 | No token, an expired token, or a bad one. |
| `PERMISSION_DENIED` | 403 | Authenticated, but not allowed — including reading another member's records. |
| `NOT_FOUND` | 404 | No such object, or no such endpoint. |
| `METHOD_NOT_ALLOWED` | 405 | Wrong verb for that path. |
| `THROTTLED` | 429 | Rate limit hit. Auth endpoints are tighter than the rest. |
| `CONFLICT` | 409 | A database constraint was violated in a way no more specific code covers. |
| `INTERNAL_ERROR` | 5xx | Unhandled. Logged server-side with a traceback. |

## Accounts

| Code | Status | When |
|---|---|---|
| `EMAIL_ALREADY_REGISTERED` | 409 | Registration with an email that already has an account. |
| `INVALID_CREDENTIALS` | 401 | Login with a wrong email or password, or an inactive account. |
| `INCORRECT_PASSWORD` | 400 | `current_password` did not match on change-password. |
| `INVALID_REFRESH_TOKEN` | 401 | The refresh token is malformed, expired, or already rotated. |
| `NOT_A_MEMBER` | 404 | The id exists but is not a borrowing member. |

## Catalogue

| Code | Status | When |
|---|---|---|
| `DUPLICATE_ISBN` | 409 | Another book already has that ISBN. |
| `DUPLICATE_BARCODE` | 409 | Another copy already has that barcode. |
| `BOOK_HAS_COPIES` | 409 | Deleting a title that still has physical copies. |
| `COPY_ON_LOAN` | 409 | Deleting a copy, or changing its status, while it is out. |
| `AUTHOR_HAS_BOOKS` | 409 | Deleting an author still attached to a title. |
| `CATEGORY_HAS_BOOKS` | 409 | Deleting a category still attached to a title. |

An invalid ISBN is a `VALIDATION_ERROR` with `details.isbn`, not its own code — the check digit
is a field rule, not a business rule.

## Circulation

| Code | Status | When | `details` |
|---|---|---|---|
| `COPY_NOT_AVAILABLE` | 409 (404 for an unknown barcode) | The copy is lost, damaged, withdrawn, or already on loan. | `barcode`, `status` |
| `LOAN_LIMIT_REACHED` | 409 | The member is at the concurrent loan cap. | `active_loans`, `limit` |
| `MEMBERSHIP_SUSPENDED` | 409 | The card is suspended, or the user is inactive. | `reason` when one was recorded |
| `MEMBERSHIP_EXPIRED` | 409 | `membership_expires_on` is in the past. | `expired_on` |
| `UNPAID_FINES` | 409 | Outstanding fines are at or above the borrowing threshold. | `outstanding`, `threshold` |
| `COPY_HELD_FOR_OTHER_MEMBER` | 409 | That copy is on the hold shelf for someone else. | `held_for` |
| `LOAN_ALREADY_RETURNED` | 409 | Checking in or renewing a loan that is already closed. | `returned_at` |
| `RENEWAL_LIMIT_REACHED` | 409 | The renewal cap is spent. | `renewal_count`, `limit` |
| `RENEWAL_BLOCKED_OVERDUE` | 409 | Overdue loans are renewed at the desk, not online. | `days_overdue` |
| `RENEWAL_BLOCKED_RESERVED` | 409 | Someone is queued for that title. | — |
| `DUPLICATE_RESERVATION` | 409 | The member already has an active hold on that title. | — |
| `ALREADY_ON_LOAN_BY_MEMBER` | 409 | The member already has a copy of that title out. | — |
| `RESERVATION_NOT_ACTIVE` | 409 | Cancelling or fulfilling a hold that is already closed. | `status` |
| `RESERVATION_NOT_READY` | 409 | The held copy is no longer on the hold shelf. | — |
| `NO_COPY_AVAILABLE` | 409 | Fulfilling a hold with nothing on the shelf. | — |
| `FINE_ALREADY_SETTLED` | 409 | Paying or waiving a fine that is already paid or waived. | `status` |

## Handling them on the client

`src/api/errors.ts` turns any of these into a typed `ApiError` with `code`, `status`, `message`
and `details`. `ApiError.fieldErrors` flattens a `VALIDATION_ERROR`'s `details` into a
`{ field: message }` map for `react-hook-form`. Everywhere else, showing `error.message` is
correct — the messages are written to be read.
