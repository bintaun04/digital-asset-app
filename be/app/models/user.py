from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, LargeBinary, Text
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    # Auth fields
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(150), default="")
    is_active = Column(Boolean, default=True)

    # Voice biometric fields
    voice_embedding = Column(LargeBinary, nullable=True)  # BLOB
    voice_key_text = Column(Text, nullable=True)  # TEXT
    voice_language = Column(String(2), default="vi")  # VARCHAR(2)
    voice_registered_at = Column(TIMESTAMP, nullable=True)  # TIMESTAMP

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"