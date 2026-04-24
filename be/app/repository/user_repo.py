import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import update

from app.core.database import get_db
from ..models.user import User

logger = logging.getLogger("UserRepository")


class UserRepository:
    @staticmethod
    def get_by_email(email: str) -> Optional[User]:
        """Lấy user theo email"""
        db: Session = next(get_db())
        try:
            return db.query(User).filter(User.email == email).first()
        finally:
            db.close()

    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        """Lấy user theo ID"""
        db: Session = next(get_db())
        try:
            return db.query(User).filter(User.id == user_id).first()
        finally:
            db.close()

    @staticmethod
    def create_user(email: str, hashed_password: str, full_name: str = "") -> User:
        """Tạo user mới"""
        db: Session = next(get_db())
        try:
            new_user = User(
                email=email,
                hashed_password=hashed_password,
                full_name=full_name,
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            logger.info(f"✅ Created user: {email} (ID={new_user.id})")
            return new_user
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to create user {email}: {e}")
            raise
        finally:
            db.close()

    @staticmethod
    def save_voice_enrollment(
        user_id: int,
        embedding: bytes,
        voice_key_text: str,
        language: str = "vi"  # ✅ THÊM PARAMETER NÀY
    ) -> bool:
        """
        Lưu voice enrollment vào user
        
        Args:
            user_id: ID user
            embedding: Binary embedding data
            voice_key_text: Transcribed passphrase
            language: Language code ('vi' hoặc 'en')
        """
        db: Session = next(get_db())
        try:
            from datetime import datetime
            
            stmt = update(User).where(User.id == user_id).values(
                voice_embedding=embedding,
                voice_key_text=voice_key_text,
                voice_language=language,  # ✅ LƯU LANGUAGE
                voice_registered_at=datetime.utcnow()
            )
            
            result = db.execute(stmt)
            db.commit()
            
            if result.rowcount > 0:
                logger.info(
                    f"✅ Saved voice enrollment for user {user_id} | "
                    f"lang={language} | text='{voice_key_text[:50]}...'"
                )
                return True
            else:
                logger.warning(f"⚠ User {user_id} not found for voice enrollment")
                return False
                
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to save voice for user {user_id}: {e}")
            return False
        finally:
            db.close()

    @staticmethod
    def delete_voice_enrollment(user_id: int) -> bool:
        """Xóa voice enrollment của user"""
        db: Session = next(get_db())
        try:
            stmt = update(User).where(User.id == user_id).values(
                voice_embedding=None,
                voice_key_text=None,
                voice_language='vi',  # Reset về default
                voice_registered_at=None
            )
            
            result = db.execute(stmt)
            db.commit()
            
            if result.rowcount > 0:
                logger.info(f"✅ Deleted voice enrollment for user {user_id}")
                return True
            else:
                logger.warning(f"⚠ User {user_id} not found")
                return False
                
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to delete voice for user {user_id}: {e}")
            return False
        finally:
            db.close()

    @staticmethod
    def update_user(user_id: int, **kwargs) -> bool:
        """Update thông tin user"""
        db: Session = next(get_db())
        try:
            stmt = update(User).where(User.id == user_id).values(**kwargs)
            result = db.execute(stmt)
            db.commit()
            
            if result.rowcount > 0:
                logger.info(f"✅ Updated user {user_id}: {list(kwargs.keys())}")
                return True
            return False
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to update user {user_id}: {e}")
            return False
        finally:
            db.close()