import requests
from config import BACKEND_URL


def enroll_voice(user_id: str, file_path: str, token: str = None):
    """Đăng ký giọng nói - gọi đúng endpoint /voice/enroll"""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with open(file_path, "rb") as f:
        files = {
            "file": (
                "voice.wav",
                f,
                "audio/wav"
            )
        }
        data = {"user_id": str(user_id)}

        response = requests.post(
            f"{BACKEND_URL}/voice/enroll",  # FIX: was /voice/verify
            data=data,
            files=files,
            headers=headers,
            timeout=30
        )

    print("STATUS:", response.status_code)
    print("TEXT:", response.text)

    response.raise_for_status()
    return response.json()


def verify_voice(user_id: str, file_path: str, token: str = None):
    """Xác thực giọng nói - gọi /voice/verify"""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with open(file_path, "rb") as f:
        files = {
            "file": (
                "voice.wav",
                f,
                "audio/wav"
            )
        }
        data = {"user_id": str(user_id)}

        response = requests.post(
            f"{BACKEND_URL}/voice/verify",
            data=data,
            files=files,
            headers=headers,
            timeout=30
        )

    print("STATUS:", response.status_code)
    print("TEXT:", response.text)

    response.raise_for_status()
    return response.json()