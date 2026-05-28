# backend/app/services/biometric_service.py
import logging
from difflib import SequenceMatcher

import numpy as np
from fastapi import HTTPException

from .audio_service import AudioService
from ..repository.user_repo import UserRepository
from ..repository.insight_repo import InsightRepository
from app.services.challenge_service import ChallengeService

logger = logging.getLogger("BiometricService")

VOICE_THRESHOLD = 0.7
TEXT_THRESHOLD  = 0.60


def _text_sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()


class BiometricService:
    def __init__(self, voice_service=None):
        self.audio_service   = AudioService()
        self.voice_service   = voice_service
        self.voice_threshold = VOICE_THRESHOLD
        self.text_threshold  = TEXT_THRESHOLD

    # ── Enroll ────────────────────────────────────────────────────────────────

    async def enroll_voice_with_stt(
        self,
        user_id: str,
        audio_bytes: bytes,
        language: str = "vi",
    ) -> tuple[bool, str]:
        """STT → embedding → lưu DB. Không lưu file audio."""
        uid = int(user_id)

        if not self.voice_service:
            raise ValueError("VoiceService chưa được inject")

        transcribed = await self.voice_service.transcribe(audio_bytes, language=language)
        voice_key   = transcribed.strip() if transcribed else ""

        if len(voice_key) < 3:
            raise HTTPException(
                status_code=422,
                detail="Không nhận diện được lời nói rõ ràng (cần ít nhất 3 ký tự)",
            )

        logger.info(f"[Enroll STT] User {uid} | Lang: {language} | Text: '{voice_key}'")

        audio_np  = await self.audio_service.process_audio(audio_bytes)
        embedding = self.audio_service.extract_features(audio_np)
        emb_bytes = embedding.tobytes()

        logger.info(
            f"[Enroll] User {uid} | dim={len(embedding)} | "
            f"{'MFCC+GE2E' if len(embedding) > 200 else 'MFCC-only'}"
        )

        success = UserRepository.save_voice_enrollment(
            user_id=uid,
            embedding=emb_bytes,
            voice_key_text=voice_key,
            language=language,
        )

        # Lưu insight enroll (score=1.0 vì đây là lần đầu, không có gốc để so)
        if success:
            InsightRepository.save(
                user_id=uid,
                action_type="enroll",
                insight={
                    "is_match":         True,
                    "cosine_score":     1.0,
                    "mfcc_score":       None,
                    "ge2e_score":       None,
                    "text_similarity":  1.0,
                    "threshold":        self.voice_threshold,
                    "gap_to_threshold": 1.0 - self.voice_threshold,
                    "embedding_dim":    int(len(embedding)),
                    "mode":             "MFCC+GE2E" if len(embedding) > 200 else "MFCC-only",
                    "confidence":       "high",
                },
                language=language,
                transcribed_text=voice_key,
            )
            logger.info(f"✅ Enrolled user {uid} | lang={language} | key='{voice_key[:60]}'")

        return success, transcribed or ""

    # ── Verify + Insight ──────────────────────────────────────────────────────

    async def verify_voice_with_insight(
        self,
        user_id: str,
        audio_bytes: bytes,
        transcribed_text: str,
        language: str = "vi",
        action_type: str = "verify",
    ) -> tuple[bool, float, str, dict]:
        """
        Two-factor verify và trả insight chi tiết.
        Tự động lưu insight vào DB sau mỗi lần verify.
        """
        uid  = int(user_id)
        user = UserRepository.get_by_id(uid)

        if not user or not user.voice_embedding:
            raise HTTPException(status_code=404, detail="User chưa đăng ký giọng nói")

        voice_key = user.voice_key_text or ""
        if not voice_key:
            raise HTTPException(status_code=400, detail="Chưa có voice key trong DB")

        # Factor 1: Text
        text_sim = _text_sim(transcribed_text, voice_key)
        logger.info(
            f"[Verify Text] user={uid} | spoken='{transcribed_text}' | "
            f"key='{voice_key}' | sim={text_sim:.2f}"
        )

        if text_sim < self.text_threshold:
            try:
                audio_np = await self.audio_service.process_audio(audio_bytes)
                acoustic = self.audio_service.extract_acoustic(audio_np)
            except Exception:
                acoustic = {}

            fail_insight = {
                "is_match":         False,
                "cosine_score":     0.0,
                "mfcc_score":       None,
                "ge2e_score":       None,
                "text_similarity":  round(text_sim, 4),
                "threshold":        self.voice_threshold,
                "gap_to_threshold": round(0.0 - self.voice_threshold, 4),
                "embedding_dim":    int(np.frombuffer(user.voice_embedding, dtype=np.float32).size),
                "mode":             "N/A",
                "confidence":       "very_low",
                **acoustic,
            }
            InsightRepository.save(uid, action_type, fail_insight, language, transcribed_text)
            return False, 0.0, f"Nội dung không khớp ({text_sim:.0%})", fail_insight
        # Factor 2: Voice embedding
        try:
            insight_raw = self.audio_service.compute_insight(
                user.voice_embedding, audio_bytes, self.voice_threshold
            )
        except ValueError as ve:
            raise HTTPException(status_code=422, detail=str(ve))
        except Exception:
            logger.exception("Lỗi compute insight")
            raise HTTPException(status_code=503, detail="Lỗi xử lý giọng nói")

        insight_raw["text_similarity"] = round(text_sim, 4)

        is_match = insight_raw["is_match"]
        score    = insight_raw["cosine_score"]

        logger.info(
            f"[Insight] user={uid} | score={score:.4f} | text={text_sim:.2f} | "
            f"mfcc={insight_raw.get('mfcc_score')} | ge2e={insight_raw.get('ge2e_score')} | "
            f"conf={insight_raw.get('confidence')}"
        )

        # Lưu insight vào DB
        InsightRepository.save(uid, action_type, insight_raw, language, transcribed_text)

        reason = "" if is_match else (
            f"Giọng nói không khớp (score={score:.3f}, cần ≥{self.voice_threshold})"
        )
        return is_match, score, reason, insight_raw

    # backward-compat alias
    async def verify_voice(
        self,
        user_id: str,
        audio_bytes: bytes,
        transcribed_text: str,
        language: str = "vi",
    ) -> tuple[bool, float, str]:
        is_match, score, reason, _ = await self.verify_voice_with_insight(
            user_id, audio_bytes, transcribed_text, language
        )
        return is_match, score, reason

    # ── Delete ────────────────────────────────────────────────────────────────

    async def delete_voice(self, user_id: str) -> bool:
        return UserRepository.delete_voice_enrollment(int(user_id))

    # ── Challenge ─────────────────────────────────────────────────────────────

    async def verify_with_challenge(
        self,
        user_id: int,
        audio_bytes: bytes,
        challenge_id: str,
        language: str = "vi",
    ) -> tuple[bool, float, str]:

        challenge = ChallengeService.get_challenge(challenge_id, user_id)
        if not challenge:
            return False, 0.0, "Challenge không hợp lệ hoặc đã hết hạn (90 giây)"

        try:
            transcribed = await self.voice_service.transcribe(audio_bytes, language)
            if not transcribed or len(transcribed.strip()) < 5:
                ChallengeService.delete_challenge(challenge_id)
                return False, 0.0, "Không nhận diện được giọng nói"
        except Exception as e:
            logger.error(f"STT Error: {e}")
            ChallengeService.delete_challenge(challenge_id)
            return False, 0.0, "Lỗi chuyển giọng nói thành văn bản"

        text_score = SequenceMatcher(
            None,
            transcribed.lower().strip(),
            challenge["text"].lower().strip(),
        ).ratio()

        if text_score < 0.82:
            ChallengeService.delete_challenge(challenge_id)
            # Lưu insight fail
            try:
                audio_np = await self.audio_service.process_audio(audio_bytes)
                acoustic = self.audio_service.extract_acoustic(audio_np)
            except Exception:
                acoustic = {}

            InsightRepository.save(
                user_id=user_id,
                action_type="challenge",
                insight={
                    "is_match":         False,
                    "cosine_score":     0.0,
                    "mfcc_score":       None,
                    "ge2e_score":       None,
                    "text_similarity":  round(text_score, 4),
                    "threshold":        0.7,
                    "gap_to_threshold": round(0.0 - 0.78, 4),
                    "embedding_dim":    0,
                    "mode":             "N/A",
                    "confidence":       "very_low",
                    **acoustic,
                },
                language=language,
                transcribed_text=transcribed,
            )
            return False, text_score, f"Nội dung nói không khớp ({text_score:.1%})"
        user = UserRepository.get_by_id(user_id)
        if not user or not user.voice_embedding:
            ChallengeService.delete_challenge(challenge_id)
            return False, 0.0, "Người dùng chưa đăng ký giọng nói"

        try:
            insight_raw = self.audio_service.compute_insight(
                stored_embedding=user.voice_embedding,
                audio_bytes=audio_bytes,
                threshold=0.7,
            )
        except Exception as e:
            logger.error(f"Voice compare error: {e}")
            ChallengeService.delete_challenge(challenge_id)
            return False, 0.0, "Lỗi so sánh giọng nói"

        insight_raw["text_similarity"] = round(text_score, 4)
        ChallengeService.delete_challenge(challenge_id)

        # Lưu insight challenge
        InsightRepository.save(user_id, "challenge", insight_raw, language, transcribed)

        if insight_raw["is_match"] and text_score >= 0.82:
            return True, insight_raw["cosine_score"], "Xác thực thành công"
        return False, insight_raw["cosine_score"], f"Giọng nói không khớp (score: {insight_raw['cosine_score']:.4f})"