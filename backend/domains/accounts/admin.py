from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from domains.accounts.models import MemberProfile, User


class MemberProfileInline(admin.StackedInline):
    model = MemberProfile
    can_delete = False
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [MemberProfileInline]
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "role", "password1", "password2")}),
    )


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ("membership_number", "user", "is_suspended", "membership_expires_on")
    search_fields = ("membership_number", "user__email")
    list_filter = ("is_suspended",)
