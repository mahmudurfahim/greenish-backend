# Greenish Trade – Reseller Auth API (Django + PostgreSQL)

Base URL (local): `http://127.0.0.1:8000/api/auth/`

| Method | Endpoint | Kaj |
|---|---|---|
| POST | `register/` | Notun reseller nibondhon, OTP pathay |
| POST | `verify-otp/` | OTP verify, token ferot dey |
| POST | `resend-otp/` | Notun OTP |
| POST | `login/` | Mobile + password diye login |
| POST | `token/refresh/` | Access token renew |
| POST | `forgot-password/` | Password reset OTP |
| POST | `reset-password/` | OTP diye notun password |
| GET  | `me/` | Logged in user er info (Bearer token lagbe) |

## Register
```json
POST /api/auth/register/
{
  "full_name": "Rahim Uddin",
  "email": "rahim@example.com",
  "phone": "01712345678",
  "facebook_page_name": "Rahim Fashion",
  "address": "Mirpur, Dhaka",
  "date_of_birth": "1995-05-20",
  "password": "StrongPass#2026",
  "confirm_password": "StrongPass#2026"
}
```
## Verify OTP
```json
POST /api/auth/verify-otp/
{ "phone": "01712345678", "code": "123456" }
```
## Login
```json
POST /api/auth/login/
{ "phone": "01712345678", "password": "StrongPass#2026" }
```
Response: `{ "message", "user": {...}, "access": "...", "refresh": "..." }`

Protected API call: header `Authorization: Bearer <access>`

Verify na kora user login korle `403` + `"code": "not_verified"` ashe.
