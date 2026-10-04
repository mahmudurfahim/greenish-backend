from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import OTP, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-date_joined",)
    list_display = ("phone", "full_name", "email", "is_verified", "is_active", "date_joined")
    list_filter = ("is_verified", "is_active", "is_staff")
    search_fields = ("phone", "full_name", "email", "facebook_page_name")
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Profile", {"fields": ("full_name", "email", "facebook_page_name", "address", "date_of_birth")}),
        ("Status", {"fields": ("is_verified", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("phone", "full_name", "email", "password1", "password2")}),
    )


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("user_phone", "purpose", "debug_code", "created_at", "expires_at", "attempts", "is_used")
    list_filter = ("purpose", "is_used")
    search_fields = ("user__phone", "user__email")
    ordering = ("-created_at",)

    @admin.display(description="Phone")
    def user_phone(self, obj):
        return obj.user.phone