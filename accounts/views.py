from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTP, User
from .serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResendOTPSerializer,
    ResetPasswordSerializer,
    UserSerializer,
    VerifyOTPSerializer,
)
from .utils import SmsFailed, check_otp, issue_otp


def tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


class PublicAuthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class RegisterView(PublicAuthView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        try:
            issue_otp(user, OTP.REGISTER)
        except SmsFailed:
            user.delete()  # SMS na gele user rakhbo na, jate abar register kora jay
            raise
        return Response(
            {
                "message": "নিবন্ধন সফল। আপনার ফোনে ৬ সংখ্যার OTP পাঠানো হয়েছে।",
                "phone": user.phone,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyOTPView(PublicAuthView):
    def post(self, request):
        s = VerifyOTPSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = User.objects.filter(phone=s.validated_data["phone"]).first()
        if not user:
            return Response({"detail": "ব্যবহারকারী পাওয়া যায়নি।"}, status=404)
        if user.is_verified:
            return Response({"detail": "অ্যাকাউন্ট আগেই ভেরিফাই করা হয়েছে।"}, status=400)

        check_otp(user, s.validated_data["code"], OTP.REGISTER)
        user.is_verified = True
        user.save(update_fields=["is_verified"])
        return Response(
            {"message": "ভেরিফিকেশন সফল।", "user": UserSerializer(user).data, **tokens_for(user)}
        )


class ResendOTPView(PublicAuthView):
    def post(self, request):
        s = ResendOTPSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = User.objects.filter(phone=s.validated_data["phone"], is_verified=False).first()
        if user:
            issue_otp(user, OTP.REGISTER)
        # user na thakleo ek-i response (kono info leak na kora)
        return Response({"message": "নতুন OTP পাঠানো হয়েছে।"})


class LoginView(PublicAuthView):
    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = authenticate(request, phone=s.validated_data["phone"], password=s.validated_data["password"])
        if user is None:
            return Response({"detail": "মোবাইল নম্বর বা পাসওয়ার্ড ভুল।"}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_verified:
            return Response(
                {"detail": "আপনার অ্যাকাউন্ট ভেরিফাই করা হয়নি।", "code": "not_verified", "phone": user.phone},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response({"message": "লগইন সফল।", "user": UserSerializer(user).data, **tokens_for(user)})


class ForgotPasswordView(PublicAuthView):
    def post(self, request):
        s = ForgotPasswordSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = User.objects.filter(phone=s.validated_data["phone"], is_active=True).first()
        if user:
            issue_otp(user, OTP.RESET)
        return Response({"message": "নম্বরটি নিবন্ধিত থাকলে একটি OTP পাঠানো হয়েছে।"})


class ResetPasswordView(PublicAuthView):
    def post(self, request):
        s = ResetPasswordSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = User.objects.filter(phone=s.validated_data["phone"], is_active=True).first()
        if not user:
            return Response({"code": ["OTP ভুল হয়েছে।"]}, status=400)
        check_otp(user, s.validated_data["code"], OTP.RESET)
        user.set_password(s.validated_data["new_password"])
        user.is_verified = True  # OTP diye phone prove hoye gese
        user.save()
        return Response({"message": "পাসওয়ার্ড পরিবর্তন সফল। এখন লগইন করুন।"})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)