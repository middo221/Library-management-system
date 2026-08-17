from domains.common import error_codes
from domains.common.exceptions import DomainError


class EmailAlreadyRegistered(DomainError):
    code = error_codes.EMAIL_ALREADY_REGISTERED
    message = "An account with that email address already exists."
    status_code = 409


class InvalidCredentials(DomainError):
    code = error_codes.INVALID_CREDENTIALS
    message = "Email or password is incorrect."
    status_code = 401


class IncorrectPassword(DomainError):
    code = error_codes.INCORRECT_PASSWORD
    message = "The current password you entered is incorrect."
    status_code = 400


class InvalidRefreshToken(DomainError):
    code = error_codes.INVALID_REFRESH_TOKEN
    message = "That refresh token is invalid or has already been used."
    status_code = 401


class NotAMember(DomainError):
    code = error_codes.NOT_A_MEMBER
    message = "That user is not a library member."
    status_code = 404
