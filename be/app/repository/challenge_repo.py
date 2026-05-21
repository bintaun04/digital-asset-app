# app/repository/challenge_repo.py
import logging
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.voice_challenge import VoiceChallenge   # ← model riêng

logger = logging.getLogger("ChallengeRepository")


class ChallengeRepository:

    @staticmethod
    def save_challenge(
        challenge_id: str,
        user_id: int,
        text: str,
        expires_at: datetime,
    ):
        db: Session = next(get_db())
        try:
            challenge = VoiceChallenge(
                id             = challenge_id,
                user_id        = user_id,
                challenge_text = text,
                expires_at     = expires_at,
            )
            db.add(challenge)
            db.commit()
            logger.debug(f"Saved challenge {challenge_id} for user {user_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save challenge: {e}")
        finally:
            db.close()

    @staticmethod
    def get_challenge(challenge_id: str, user_id: int) -> Optional[Dict]:
        db: Session = next(get_db())
        try:
            ch = db.query(VoiceChallenge).filter(
                VoiceChallenge.id      == challenge_id,
                VoiceChallenge.user_id == user_id,
            ).first()

            if not ch:
                return None

            if datetime.utcnow() > ch.expires_at:
                db.delete(ch)
                db.commit()
                return None

            return {
                "id":         ch.id,
                "user_id":    ch.user_id,
                "text":       ch.challenge_text,
                "expires_at": ch.expires_at,
            }
        finally:
            db.close()

    @staticmethod
    def delete_challenge(challenge_id: str):
        db: Session = next(get_db())
        try:
            db.query(VoiceChallenge).filter(
                VoiceChallenge.id == challenge_id
            ).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete challenge {challenge_id}: {e}")
        finally:
            db.close()