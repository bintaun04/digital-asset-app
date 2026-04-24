import requests
from config import BACKEND_URL


def enroll_voice(user_id: str, file_path: str, token: str = None, language: str = "vi"):
    """
    Đăng ký giọng nói với ngôn ngữ được chỉ định
    
    Args:
        user_id: ID người dùng
        file_path: Đường dẫn file audio
        token: JWT token
        language: Ngôn ngữ ('vi' hoặc 'en')
    """
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    with open(file_path, "rb") as f:
        files = {"file": ("voice.wav", f, "audio/wav")}
        data = {
            "user_id": str(user_id),
            "language": language  # ✅ Gửi language
        }
        
        response = requests.post(
            f"{BACKEND_URL}/voice/enroll",
            data=data, 
            files=files, 
            headers=headers, 
            timeout=30
        )
    
    print(f"ENROLL STATUS ({language}):", response.status_code)
    print("RESPONSE:", response.text)
    response.raise_for_status()
    return response.json()


def verify_voice(user_id: str, file_path: str, token: str = None, language: str = "vi"):
    """
    Xác thực giọng nói với ngôn ngữ được chỉ định
    
    Args:
        user_id: ID người dùng
        file_path: Đường dẫn file audio
        token: JWT token
        language: Ngôn ngữ ('vi' hoặc 'en')
    """
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with open(file_path, "rb") as f:
        files = {"file": ("voice.wav", f, "audio/wav")}
        data = {
            "user_id": str(user_id),
            "language": language  # ✅ Gửi language
        }

        response = requests.post(
            f"{BACKEND_URL}/voice/verify",
            data=data,
            files=files,
            headers=headers,
            timeout=30
        )

    print(f"VERIFY STATUS ({language}):", response.status_code)
    print("TEXT:", response.text)

    response.raise_for_status()
    return response.json()