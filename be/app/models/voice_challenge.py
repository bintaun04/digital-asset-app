# app/models/voice_challenge.py
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from app.core.database import Base


class VoiceChallenge(Base):
    __tablename__ = "voice_challenges"

    id             = Column(String(20), primary_key=True)
    user_id        = Column(Integer,    nullable=False, index=True)
    challenge_text = Column(Text,       nullable=False)
    expires_at     = Column(TIMESTAMP,  nullable=False)
    created_at     = Column(TIMESTAMP,  server_default=func.now())