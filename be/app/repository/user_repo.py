# backend/app/repository/user_repo.py
import logging
from typing import Optional
from sqlalchemy.orm import Session

from ..models.user import User
from ..core.database import SessionLocal

logger = logging.getLogger("UserRepository")


class UserRepository:
    """
    Static/class methods dùng session riêng mỗi lần gọi.
    Phù hợp để gọi từ BiometricService mà không cần inject db.
    """

    # ── Read ──────────────────────────────────────────────────────────────────

    @classmethod
    async def get_by_id(cls, user_id: int) -> Optional[User]:
        db: Session = SessionLocal()
        try:
            return db.query(User).filter(User.id == int(user_id)).first()
        finally:
            db.close()

    @classmethod
    async def get_by_email(cls, email: str) -> Optional[User]:
        db: Session = SessionLocal()
        try:
            return db.query(User).filter(User.email == email).first()
        finally:
            db.close()

    # ── Voice embedding ───────────────────────────────────────────────────────

    @classmethod
    async def update_voice_embedding(cls, user_id: int, embedding_bytes: bytes) -> bool:
        """Lưu voice embedding (bytes) vào cột voice_embedding của user."""
        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if not user:
                logger.warning(f"update_voice_embedding: không tìm thấy user {user_id}")
                return False
            user.voice_embedding = embedding_bytes
            db.commit()
            logger.info(f"✅ Đã lưu voice embedding cho user {user_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Lỗi update_voice_embedding user {user_id}: {e}")
            return False
        finally:
            db.close()

    @classmethod
    async def delete_voice_embedding(cls, user_id: int) -> bool:
        """Xóa voice embedding của user."""
        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if not user:
                return False
            user.voice_embedding = None
            db.commit()
            logger.info(f"✅ Đã xóa voice embedding của user {user_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Lỗi delete_voice_embedding user {user_id}: {e}")
            return False
        finally:
            db.close()