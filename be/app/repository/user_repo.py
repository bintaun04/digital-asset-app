# backend/app/repository/user_repo.py
import logging
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.user import User

logger = logging.getLogger("UserRepository")


class UserRepository:

    @staticmethod
    def get_by_id(user_id: int):
        """Lấy user theo ID"""
        with SessionLocal() as db:
            return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(email: str):
        """Lấy user theo email"""
        with SessionLocal() as db:
            return db.query(User).filter(User.email == email).first()

    @staticmethod
    def save_voice_enrollment(
        user_id: int,
        embedding: bytes,
        voice_key_text: str,
    ) -> bool:
        """Lưu embedding + voice_key_text"""
        with SessionLocal() as db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    logger.warning(f"User {user_id} không tồn tại")
                    return False

                user.voice_embedding = embedding
                user.voice_key_text = voice_key_text.strip().lower()

                db.commit()
                db.refresh(user)

                logger.info(
                    f"✅ Saved enrollment | user={user_id} | "
                    f"key='{voice_key_text[:40]}...'"
                )
                return True

            except Exception as e:
                db.rollback()
                logger.error(f"Lỗi save_voice_enrollment user={user_id}: {e}")
                return False

    @staticmethod
    def delete_voice_enrollment(user_id: int) -> bool:
        """Xóa voice data"""
        with SessionLocal() as db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return False

                user.voice_embedding = None
                user.voice_key_text = None

                db.commit()
                return True
            except Exception as e:
                db.rollback()
                logger.error(f"Lỗi delete_voice_enrollment: {e}")
                return False