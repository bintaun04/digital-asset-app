# fe/services/auth_api.py
import requests
from config import BACKEND_URL

def register_user(email: str, password: str, full_name: str = ""):
    response = requests.post(
        f"{BACKEND_URL}/auth/register",
        json={"email": email, "password": password, "full_name": full_name}
    )
    response.raise_for_status()
    return response.json()

def login_user(email: str, password: str):
    response = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": email, "password": password}
    )
    response.raise_for_status()
    return response.json()