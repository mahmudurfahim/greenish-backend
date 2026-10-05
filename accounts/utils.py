import json
import secrets
import urllib.parse
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from .models import OTP

BULKSMSBD_URL = "http://bulksmsbd.net/api/smsapi"

BULKSMSBD_ERRORS = {
    1001: "Invalid number",
    1002: "Sender ID not correct / disabled",
    1003: "Required field missing",
    1005: "Internal error",
    1006: "Balance validity not available",
    1007: "Balance insufficient",
    1011: "User id not found",
    1012: "Masking SMS must be sent in Bengali",
    1031: "Account not verified, contact administrator",
    1032: "IP not whitelisted",
}


class TooManyRequests(APIException):
    status_code = 429
    default_detail = "অনেক বেশি চেষ্টা করা হয়েছে। একটু পরে আবার চেষ্টা করুন।"
    default_code = "throttled"


class SmsFailed(APIException):
    status_code = 503
    default_detail = "SMS পাঠানো যায়নি। একটু পরে আবার চেষ্টা করুন।"
    default_code = "sms_failed"


def generate_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"  # 6 digit


def send_sms(phone: str, message: str) -> None:
    """SMS pathay. SMS_BACKEND=console hole terminal e print, bulksmsbd hole asol SMS."""
    if settings.SMS_BACKEND == "console":
        print(f"\n[SMS to {phone}] {message}\n")
        return

    if settings.SMS_BACKEND == "bulksmsbd":
        payload = urllib.parse.urlencode({
            "api_key": settings.BULKSMSBD_API_KEY,
            "senderid": settings.BULKSMSBD_SENDER_ID,
            "type": "text",
            "number": "88" + phone,  # 01XXXXXXXXX -> 8801XXXXXXXXX
            "message": message,
        }).encode("utf-8")
        request = urllib.request.Request(BULKSMSBD_URL, data=payload, method="POST")
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
        try:
            code = int(json.loads(body).get("response_code"))
        except (ValueError, TypeError, AttributeError):
            raise RuntimeError(f"Unexpected SMS response: {body}")
        if code != 202:
            raise RuntimeError(f"SMS failed ({code}): {BULKSMSBD_ERRORS.get(code, 'Unknown error')}")
        return

    raise RuntimeError("SMS_BACKEND thik moto set kora nei")


def issue_otp(user, purpose: str) -> None:
    """Notun OTP baniye SMS e pathay. SMS fail hole error dey."""
    now = timezone.now()

    last = OTP.objects.filter(user=user, purpose=purpose).order_by("-created_at").first()
    if last:
        elapsed = (now - last.created_at).total_seconds()
        if elapsed < settings.OTP_RESEND_COOLDOWN:
            wait = int(settings.OTP_RESEND_COOLDOWN - elapsed) + 1
            raise TooManyRequests(f"নতুন OTP পেতে {wait} সেকেন্ড অপেক্ষা করুন।")

    OTP.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)

    code = generate_code()
    otp = OTP.objects.create(
        user=user,
        purpose=purpose,
        code_hash=make_password(code),
        debug_code=code if settings.DEBUG else "",  # production e (DEBUG=False) plain code save hobe na
        expires_at=now + timedelta(minutes=settings.OTP_EXPIRY_MINUTES),
    )

    sms_text = (
        f"Greenish Trade: Your OTP is {code}. "
        f"Valid for {settings.OTP_EXPIRY_MINUTES} minutes. Do not share it."
    )
    try:
        send_sms(user.phone, sms_text)
    except Exception as exc:
        print("SMS error:", exc)  # Render Logs e dekha jabe
        otp.delete()  # jate sathe sathe abar chesta kora jay (cooldown na lage)
        raise SmsFailed()


def check_otp(user, code: str, purpose: str) -> None:
    """OTP thik hole used mark kore, na hole ValidationError."""
    otp = (
        OTP.objects.filter(user=user, purpose=purpose, is_used=False)
        .order_by("-created_at")
        .first()
    )
    if not otp:
        raise ValidationError({"code": ["কোনো সক্রিয় OTP নেই। নতুন OTP চান।"]})
    if otp.expires_at < timezone.now():
        raise ValidationError({"code": ["OTP এর মেয়াদ শেষ। নতুন OTP চান।"]})
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise ValidationError({"code": ["অনেকবার ভুল হয়েছে। নতুন OTP চান।"]})
    if not check_password(code, otp.code_hash):
        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        raise ValidationError({"code": ["OTP ভুল হয়েছে।"]})

    otp.is_used = True
    otp.save(update_fields=["is_used"])