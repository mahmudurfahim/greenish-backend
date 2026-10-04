from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Mobile number dewa lagbe")
        if "email" in extra_fields and extra_fields["email"]:
            extra_fields["email"] = extra_fields["email"].lower()
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Reseller user. Login hoy mobile number + password diye."""

    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=11, unique=True)  # 01XXXXXXXXX
    facebook_page_name = models.CharField(max_length=150, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    is_verified = models.BooleanField(default=False)  # OTP verify hole True
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["full_name", "email"]

    def __str__(self):
        return f"{self.full_name} ({self.phone})"


class OTP(models.Model):
    REGISTER = "register"
    RESET = "reset"
    PURPOSES = [(REGISTER, "Registration"), (RESET, "Password reset")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    purpose = models.CharField(max_length=20, choices=PURPOSES)
    code_hash = models.CharField(max_length=128)  # OTP hash kore rakha hoy
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)
    debug_code = models.CharField(max_length=6, blank=True)  # shudhu DEBUG=True te save hoy

    class Meta:
        indexes = [models.Index(fields=["user", "purpose", "-created_at"])]