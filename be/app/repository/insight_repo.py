# app/repository/insight_repo.py
import logging
from typing import List, Optional, Dict
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.voice_insight import VoiceInsight

logger = logging.getLogger("InsightRepository")


class InsightRepository:

    @staticmethod
    def save(
        user_id: int,
        action_type: str,
        insight: dict,
        language: str = "vi",
        transcribed_text: str = "",
    ) -> Optional[VoiceInsight]:
        db: Session = next(get_db())
        try:
            record = VoiceInsight(
                user_id          = user_id,
                action_type      = action_type,
                is_match         = insight.get("is_match", False),
                cosine_score     = insight.get("cosine_score", 0.0),
                mfcc_score       = insight.get("mfcc_score"),
                ge2e_score       = insight.get("ge2e_score"),
                text_similarity  = insight.get("text_similarity"),
                threshold        = insight.get("threshold", 0.75),
                gap_to_threshold = insight.get("gap_to_threshold"),
                embedding_dim    = insight.get("embedding_dim", 380),
                mode             = insight.get("mode", "MFCC+GE2E"),
                confidence       = insight.get("confidence"),
                # Acoustic
                duration_sec     = insight.get("duration_sec"),
                pitch_mean       = insight.get("pitch_mean"),
                pitch_std        = insight.get("pitch_std"),
                speaking_rate    = insight.get("speaking_rate"),
                energy_mean      = insight.get("energy_mean"),
                energy_std       = insight.get("energy_std"),
                snr_db           = insight.get("snr_db"),
                silence_ratio    = insight.get("silence_ratio"),
                voice_quality    = insight.get("voice_quality"),
                # Meta
                language         = language,
                transcribed_text = transcribed_text or "",
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            logger.info(
                f"✅ Insight saved | user={user_id} | type={action_type} | "
                f"match={insight.get('is_match')} | score={insight.get('cosine_score', 0):.4f}"
            )
            return record
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to save insight for user {user_id}: {e}")
            return None
        finally:
            db.close()

    @staticmethod
    def get_by_user(
        user_id: int,
        action_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict]:
        db: Session = next(get_db())
        try:
            q = db.query(VoiceInsight).filter(VoiceInsight.user_id == user_id)
            if action_type:
                q = q.filter(VoiceInsight.action_type == action_type)
            rows = q.order_by(VoiceInsight.created_at.desc()).limit(limit).all()

            return [
                {
                    "id":               r.id,
                    "action_type":      r.action_type,
                    "is_match":         r.is_match,
                    "cosine_score":     r.cosine_score,
                    "mfcc_score":       r.mfcc_score,
                    "ge2e_score":       r.ge2e_score,
                    "text_similarity":  r.text_similarity,
                    "threshold":        r.threshold,
                    "gap_to_threshold": r.gap_to_threshold,
                    "embedding_dim":    r.embedding_dim,
                    "mode":             r.mode,
                    "confidence":       r.confidence,
                    # Acoustic
                    "duration_sec":     r.duration_sec,
                    "pitch_mean":       r.pitch_mean,
                    "pitch_std":        r.pitch_std,
                    "speaking_rate":    r.speaking_rate,
                    "energy_mean":      r.energy_mean,
                    "energy_std":       r.energy_std,
                    "snr_db":           r.snr_db,
                    "silence_ratio":    r.silence_ratio,
                    "voice_quality":    r.voice_quality,
                    # Meta
                    "language":         r.language,
                    "transcribed_text": r.transcribed_text,
                    "created_at":       r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        finally:
            db.close()

    @staticmethod
    def get_stats(user_id: int) -> Dict:
        db: Session = next(get_db())
        try:
            rows = (
                db.query(VoiceInsight)
                .filter(
                    VoiceInsight.user_id == user_id,
                    VoiceInsight.action_type.in_(["verify", "challenge"]),
                )
                .all()
            )
            if not rows:
                return {"total": 0, "success_rate": 0.0, "avg_score": 0.0}

            total   = len(rows)
            matched = sum(1 for r in rows if r.is_match)
            scores  = [r.cosine_score for r in rows if r.cosine_score is not None]
            avg     = round(sum(scores) / len(scores), 4) if scores else 0.0

            return {
                "total":        total,
                "success":      matched,
                "failed":       total - matched,
                "success_rate": round(matched / total, 4),
                "avg_score":    avg,
                "max_score":    round(max(scores), 4) if scores else 0.0,
                "min_score":    round(min(scores), 4) if scores else 0.0,
            }
        finally:
            db.close()