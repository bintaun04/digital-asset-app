# app/models/voice_insight.py
from sqlalchemy import (
    Column, Integer, SmallInteger, Float, Boolean,
    String, Text, Enum, TIMESTAMP
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ActionType(str, enum.Enum):
    enroll    = "enroll"
    verify    = "verify"
    challenge = "challenge"


class VoiceInsight(Base):
    __tablename__ = "voice_insights"

    id               = Column(Integer,     primary_key=True, autoincrement=True)
    user_id          = Column(Integer,     nullable=False, index=True)
    action_type      = Column(Enum(ActionType), nullable=False)

    # Embedding comparison
    is_match         = Column(Boolean,     default=False)
    cosine_score     = Column(Float,       default=0.0)
    mfcc_score       = Column(Float,       nullable=True)
    ge2e_score       = Column(Float,       nullable=True)
    text_similarity  = Column(Float,       nullable=True)
    threshold        = Column(Float,       default=0.75)
    gap_to_threshold = Column(Float,       nullable=True)
    embedding_dim    = Column(SmallInteger, default=380)
    mode             = Column(String(20),  default="MFCC+GE2E")
    confidence       = Column(String(10),  nullable=True)

    # Acoustic features
    duration_sec     = Column(Float,       nullable=True)
    pitch_mean       = Column(Float,       nullable=True)
    pitch_std        = Column(Float,       nullable=True)
    speaking_rate    = Column(Float,       nullable=True)
    energy_mean      = Column(Float,       nullable=True)
    energy_std       = Column(Float,       nullable=True)
    snr_db           = Column(Float,       nullable=True)
    silence_ratio    = Column(Float,       nullable=True)
    voice_quality    = Column(String(10),  nullable=True)

    # Meta
    language         = Column(String(2),   default="vi")
    transcribed_text = Column(Text,        nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now())