from sqlalchemy import Column, Integer, String, LargeBinary, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    # ── Thông tin cơ bản ──────────────────────────────────────────────────────
    id               = Column(Integer, primary_key=True, index=True)
    email            = Column(String(100), unique=True, index=True, nullable=False)
    full_name        = Column(String(100), default="")
    hashed_password  = Column(String(255), nullable=False)

    # ── Voice biometric ───────────────────────────────────────────────────────
    # Câu STT nhận diện được lúc enroll — dùng để so sánh text khi login
    voice_key_text   = Column(Text, nullable=True)

    # Vector embedding (MFCC 124-d hoặc fused MFCC+GE2E 380-d, serialized bytes)
    voice_embedding  = Column(LargeBinary, nullable=True)

    # ── Meta ──────────────────────────────────────────────────────────────────
    is_active        = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow,
                              onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<User id={self.id} email={self.email}>"