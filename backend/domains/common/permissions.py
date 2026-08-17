from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsLibrarian(BasePermission):
    message = "Only librarians may perform this action."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_librarian)


class IsMember(BasePermission):
    message = "Only members may perform this action."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_member)


class IsLibrarianOrReadOnly(BasePermission):
    """Anyone authenticated may read the catalogue; only librarians may change it."""

    message = "Only librarians may change the catalogue."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return bool(user.is_librarian)


class IsOwnerOrLibrarian(BasePermission):
    """Object-level: the member the record belongs to, or any librarian.

    Objects expose the owning member through ``owner_user`` so this stays generic.
    """

    message = "You may only access your own records."

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_librarian:
            return True
        owner = getattr(obj, "owner_user", None)
        return owner is not None and owner == user
