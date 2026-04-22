# backend/app/services/auth_service.py
import logging
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from ..models.user import User

logger = logging.getLogger("AuthService")

# ========================= Config =========================
SECRET_KEY = "change-this-to-a-random-secret-key-in-production"  # Đổi sang .env khi deploy
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    # -------- Password helpers --------

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    # -------- User CRUD --------

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def create_user(self, email: str, password: str, full_name: str = "") -> User:
        user = User(
            email=email,
            hashed_password=self.hash_password(password),
            full_name=full_name
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        logger.info(f"✅ Đã tạo user mới: {email}")
        return user

    # -------- Auth logic --------

    def authenticate(self, email: str, password: str) -> Optional[User]:
        user = self.get_user_by_email(email)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    def change_password(self, user: User, old_password: str, new_password: str) -> bool:
        if not self.verify_password(old_password, user.hashed_password):
            return False
        user.hashed_password = self.hash_password(new_password)
        self.db.commit()
        logger.info(f"🔑 User {user.email} đã đổi mật khẩu")
        return True

    # -------- JWT --------

    def create_token(self, user: User) -> str:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "exp": expire
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    def get_user_from_token(self, token: str) -> Optional[User]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = int(payload.get("sub"))
            return self.get_user_by_id(user_id)
        except (JWTError, ValueError, TypeError):
            return None