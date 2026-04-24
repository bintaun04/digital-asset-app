import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import update

from app.core.database import get_db
from ..models.user import User
from ..utils.user_backup import UserBackupJSON

logger = logging.getLogger("UserRepository")

# ✅ Khởi tạo backup service
try:
    backup_service = UserBackupJSON()
    logger.info(f"✅ Backup service initialized: {backup_service.backup_file}")
except Exception as e:
    logger.error(f"❌ Failed to init backup service: {e}")
    backup_service = None


class UserRepository:
    @staticmethod
    def save_voice_enrollment(
        user_id: int,
        embedding: bytes,
        voice_key_text: str,
        language: str = "vi"
    ) -> bool:
        """Lưu voice + auto backup"""
        db: Session = next(get_db())
        try:
            from datetime import datetime
            
            stmt = update(User).where(User.id == user_id).values(
                voice_embedding=embedding,
                voice_key_text=voice_key_text,
                voice_language=language,
                voice_registered_at=datetime.utcnow()
            )
            
            result = db.execute(stmt)
            db.commit()
            
            if result.rowcount > 0:
                logger.info(f"✅ Saved voice enrollment for user {user_id} | lang={language}")
                
                # ✅ Auto backup to JSON
                if backup_service:
                    user = UserRepository.get_by_id(user_id)
                    if user:
                        backup_service.save_user({
                            'id': user.id,
                            'email': user.email,
                            'full_name': user.full_name,
                            'is_active': user.is_active,
                            'voice_embedding': user.voice_embedding,
                            'voice_key_text': user.voice_key_text,
                            'voice_language': user.voice_language,
                            'voice_registered_at': user.voice_registered_at,
                            'created_at': user.created_at,
                        })
                
                return True
            return False
                
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to save voice for user {user_id}: {e}")
            return False
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
    def get_by_email(email: str) -> Optional[User]:
        """Lấy user theo email"""
        db: Session = next(get_db())
        try:
            return db.query(User).filter(User.email == email).first()
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
    def delete_voice_enrollment(user_id: int) -> bool:
        """Xóa voice enrollment"""
        db: Session = next(get_db())
        try:
            stmt = update(User).where(User.id == user_id).values(
                voice_embedding=None,
                voice_key_text=None,
                voice_language='vi',
                voice_registered_at=None
            )
            
            result = db.execute(stmt)
            db.commit()
            
            if result.rowcount > 0:
                logger.info(f"✅ Deleted voice enrollment for user {user_id}")
                
                # ✅ Update backup
                if backup_service:
                    user = UserRepository.get_by_id(user_id)
                    if user:
                        backup_service.save_user({
                            'id': user.id,
                            'email': user.email,
                            'full_name': user.full_name,
                            'is_active': user.is_active,
                            'voice_embedding': None,
                            'voice_key_text': None,
                            'voice_language': 'vi',
                            'created_at': user.created_at,
                        })
                
                return True
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