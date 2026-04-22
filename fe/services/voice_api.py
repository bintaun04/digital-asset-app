# fe/services/voice_api.py
import requests
from config import BACKEND_URL

def enroll_voice(user_id: str, file_path: str, token: str = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with open(file_path, "rb") as f:
        response = requests.post(
            f"{BACKEND_URL}/voice/enroll",
            data={"user_id": user_id},
            files={"file": f},
            headers=headers
        )
    response.raise_for_status()
    return response.json()

def verify_voice(user_id: str, file_path: str, token: str = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with open(file_path, "rb") as f:
        response = requests.post(
            f"{BACKEND_URL}/voice/verify",
            data={"user_id": user_id},
            files={"file": f},
            headers=headers
        )
    response.raise_for_status()
    return response.json()