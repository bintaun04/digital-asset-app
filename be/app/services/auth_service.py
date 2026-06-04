# be/app/services/auth_service.py
import logging
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from sqlalchemy.orm import Session
from ..models.user import User

logger = logging.getLogger("AuthService")

# ========================= Config =========================
SECRET_KEY = "change-this-to-a-random-secret-key-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def verify_password(self, plain: str, stored_password: str) -> bool:
        """So sánh trực tiếp password"""
        return plain == stored_password

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def create_user(self, email: str, password: str, full_name: str = "") -> User:
        user = User(
            email=email,
            hashed_password=password,        # Lưu trực tiếp password (plain text)
            full_name=full_name,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> Optional[User]:
        user = self.get_user_by_email(email)
        if not user:
            logger.warning(f"⚠️ Không tìm thấy user: {email}")
            return None
        
        if not self.verify_password(password, user.hashed_password):
            logger.warning(f"⚠️ Sai mật khẩu cho user: {email}")
            return None
        
        return user

    # ==================== 2ND KEY LOGIC ====================

    def setup_2ndkey(self, user: User, pin: str, enable: bool = True) -> bool:
        if not pin.isdigit() or not (6 <= len(pin) <= 8):
            return False
        
        user.hashed_password = new_password   # Lưu trực tiếp
        self.db.commit()
        logger.info(f"✅ 2nd Key đã được thiết lập cho user {user.email}")
        return True

    def verify_2ndkey(self, user: User, pin: str) -> bool:
        if not user.enable_2ndkey or not user.second_key:
            return False
        if user.second_key == pin:
            # Reset fail count khi xác thực PIN thành công
            user.voice_fail_count = 0
            self.db.commit()
            logger.info(f"✅ Xác thực 2nd Key thành công cho user {user.email}")
            return True
        return False

    def increment_voice_fail(self, user: User):
        user.voice_fail_count = (user.voice_fail_count or 0) + 1
        self.db.commit()
        return user.voice_fail_count

    def reset_voice_fail_count(self, user: User):
        user.voice_fail_count = 0
        self.db.commit()

    def create_token(self, user: User) -> str:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "exp": expire,
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    def get_user_from_token(self, token: str) -> Optional[User]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = int(payload.get("sub"))
            return self.get_user_by_id(user_id)
        except (JWTError, ValueError, TypeError):
            return None