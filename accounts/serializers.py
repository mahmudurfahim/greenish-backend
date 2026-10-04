import re

from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from .models import User

PHONE_RE = re.compile(r"^(?:\+?88)?(01[3-9]\d{8})$")


def normalize_phone(value: str) -> str:
    cleaned = str(value).strip().replace(" ", "").replace("-", "")
    match = PHONE_RE.match(cleaned)
    if not match:
        raise serializers.ValidationError("সঠিক মোবাইল নম্বর দিন (যেমন 01712345678)")
    return match.group(1)


class PhoneField(serializers.CharField):
    """+8801..., 8801..., 01... shob 01XXXXXXXXX te convert kore."""

    def to_internal_value(self, data):
        return normalize_phone(super().to_internal_value(data))


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id", "full_name", "email", "phone",
            "facebook_page_name", "address", "date_of_birth", "is_verified",
        )


class RegisterSerializer(serializers.ModelSerializer):
    phone = PhoneField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    date_of_birth = serializers.DateField(input_formats=["%Y-%m-%d"])  # YYYY-MM-DD

    class Meta:
        model = User
        fields = (
            "full_name", "email", "phone", "facebook_page_name",
            "address", "date_of_birth", "password", "confirm_password",
        )
        extra_kwargs = {
            "full_name": {"required": True, "allow_blank": False},
            "facebook_page_name": {"required": True, "allow_blank": False},
            "address": {"required": True, "allow_blank": False},
        }

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("এই মোবাইল নম্বর দিয়ে আগেই নিবন্ধন করা হয়েছে।")
        return value

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("এই ইমেইল দিয়ে আগেই নিবন্ধন করা হয়েছে।")
        return value

    def validate_date_of_birth(self, value):
        if value >= timezone.localdate():
            raise serializers.ValidationError("সঠিক তারিখ দিন।")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": ["পাসওয়ার্ড দুটি মিলছে না।"]})
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class LoginSerializer(serializers.Serializer):
    phone = PhoneField()
    password = serializers.CharField(write_only=True)


class VerifyOTPSerializer(serializers.Serializer):
    phone = PhoneField()
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "৬ সংখ্যার OTP দিন।"})


class ResendOTPSerializer(serializers.Serializer):
    phone = PhoneField()


class ForgotPasswordSerializer(serializers.Serializer):
    phone = PhoneField()


class ResetPasswordSerializer(serializers.Serializer):
    phone = PhoneField()
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "৬ সংখ্যার OTP দিন।"})
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": ["পাসওয়ার্ড দুটি মিলছে না।"]})
        validate_password(attrs["new_password"])
        return attrs
