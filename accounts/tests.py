from unittest.mock import patch

from django.core.cache import cache
from rest_framework.test import APITestCase

from .models import User

PAYLOAD = {
    "full_name": "Rahim Uddin",
    "email": "Rahim@Example.com",
    "phone": "+8801712345678",
    "facebook_page_name": "Rahim Fashion",
    "address": "Mirpur, Dhaka",
    "date_of_birth": "1995-05-20",
    "password": "StrongPass#2026",
    "confirm_password": "StrongPass#2026",
}


@patch("accounts.utils.generate_code", return_value="123456")
class AuthFlowTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_full_flow(self, _):
        r = self.client.post("/api/auth/register/", PAYLOAD, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(User.objects.get().phone, "01712345678")

        # verify hoyni, login block
        r = self.client.post("/api/auth/login/", {"phone": "01712345678", "password": PAYLOAD["password"]}, format="json")
        self.assertEqual(r.status_code, 403)

        # vul OTP
        r = self.client.post("/api/auth/verify-otp/", {"phone": "01712345678", "code": "000000"}, format="json")
        self.assertEqual(r.status_code, 400)

        r = self.client.post("/api/auth/verify-otp/", {"phone": "01712345678", "code": "123456"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertIn("access", r.data)

        r = self.client.post("/api/auth/login/", {"phone": "01712345678", "password": PAYLOAD["password"]}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        access = r.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        r = self.client.get("/api/auth/me/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["email"], "rahim@example.com")

    def test_wrong_password(self, _):
        self.client.post("/api/auth/register/", PAYLOAD, format="json")
        r = self.client.post("/api/auth/login/", {"phone": "01712345678", "password": "nope"}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_validation(self, _):
        bad = {**PAYLOAD, "confirm_password": "different", "phone": "123"}
        r = self.client.post("/api/auth/register/", bad, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("phone", r.data)

    def test_duplicate(self, _):
        self.client.post("/api/auth/register/", PAYLOAD, format="json")
        r = self.client.post("/api/auth/register/", PAYLOAD, format="json")
        self.assertEqual(r.status_code, 400)

    def test_resend_cooldown(self, _):
        self.client.post("/api/auth/register/", PAYLOAD, format="json")
        r = self.client.post("/api/auth/resend-otp/", {"phone": "01712345678"}, format="json")
        self.assertEqual(r.status_code, 429)

    def test_password_reset(self, _):
        self.client.post("/api/auth/register/", PAYLOAD, format="json")
        self.client.post("/api/auth/verify-otp/", {"phone": "01712345678", "code": "123456"}, format="json")
        r = self.client.post("/api/auth/forgot-password/", {"phone": "01712345678"}, format="json")
        self.assertEqual(r.status_code, 200)
        r = self.client.post("/api/auth/reset-password/", {
            "phone": "01712345678", "code": "123456",
            "new_password": "NewStrong#2026", "confirm_password": "NewStrong#2026"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        r = self.client.post("/api/auth/login/", {"phone": "01712345678", "password": "NewStrong#2026"}, format="json")
        self.assertEqual(r.status_code, 200)
