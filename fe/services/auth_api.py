# fe/services/auth_api.py
import requests
from config import BACKEND_URL, REQUEST_TIMEOUT


def register_user(email: str, password: str, full_name: str = "") -> dict:
    """Đăng ký tài khoản – gửi JSON."""
    response = requests.post(
        f"{BACKEND_URL}/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def login_user(email: str, password: str, voice_file_path: str = None) -> dict:
    """
    Đăng nhập:
    - Không có voice_file_path → /auth/login-no-voice (form-data, chỉ password)
    - Có voice_file_path       → /auth/login (multipart, password + audio)
    """
    if voice_file_path:
        with open(voice_file_path, "rb") as f:
            response = requests.post(
                f"{BACKEND_URL}/auth/login",
                data={"email": email, "password": password},
                files={"file": ("voice.wav", f, "audio/wav")},
                timeout=REQUEST_TIMEOUT,
            )
    else:
        # ✅ form-data (KHÔNG dùng json=)
        response = requests.post(
            f"{BACKEND_URL}/auth/login-no-voice",
            data={"email": email, "password": password},
            timeout=REQUEST_TIMEOUT,
        )

    if not response.ok:
        # Lấy detail lỗi từ BE để hiển thị đúng
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise Exception(f"{response.status_code}: {detail}")

    return response.json()


def get_me(token: str) -> dict:
    response = requests.get(
        f"{BACKEND_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()