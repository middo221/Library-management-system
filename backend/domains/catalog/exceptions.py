from domains.common import error_codes
from domains.common.exceptions import ConflictError, NotFoundError


class BookNotFound(NotFoundError):
    message = "No book with that id exists."


class CopyNotFound(NotFoundError):
    message = "No copy with that id or barcode exists."


class AuthorNotFound(NotFoundError):
    message = "No author with that id exists."


class CategoryNotFound(NotFoundError):
    message = "No category with that id exists."


class BookHasCopies(ConflictError):
    code = error_codes.BOOK_HAS_COPIES
    message = "This book still has copies. Withdraw or delete them first."


class CopyOnLoan(ConflictError):
    code = error_codes.COPY_ON_LOAN
    message = "This copy is on loan and cannot be removed until it is returned."


class DuplicateIsbn(ConflictError):
    code = error_codes.DUPLICATE_ISBN
    message = "A book with that ISBN is already catalogued."


class DuplicateBarcode(ConflictError):
    code = error_codes.DUPLICATE_BARCODE
    message = "A copy with that barcode already exists."


class AuthorHasBooks(ConflictError):
    code = error_codes.AUTHOR_HAS_BOOKS
    message = "This author is still attached to catalogued books."


class CategoryHasBooks(ConflictError):
    code = error_codes.CATEGORY_HAS_BOOKS
    message = "This category is still attached to catalogued books."
