import logging
from difflib import SequenceMatcher

import numpy as np
from fastapi import HTTPException

from .audio_service import AudioService
from ..repository.user_repo import UserRepository

logger = logging.getLogger("BiometricService")

# Thresholds
VOICE_THRESHOLD = 0.75
TEXT_THRESHOLD = 0.60


def _text_sim(a: str, b: str) -> float:
    """Tính độ tương đồng text (không normalize)"""
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()


class BiometricService:
    def __init__(self, voice_service=None):
        self.audio_service = AudioService()
        self.voice_service = voice_service
        self.voice_threshold = VOICE_THRESHOLD
        self.text_threshold = TEXT_THRESHOLD

    # ── Enroll ────────────────────────────────────────────────────────────────

    async def enroll_voice_with_stt(
        self, 
        user_id: str, 
        audio_bytes: bytes,
        language: str = "vi"
    ) -> tuple[bool, str]:
        """
        Đăng ký giọng nói với STT tự động
        
        Args:
            user_id: ID người dùng
            audio_bytes: Audio data
            language: Ngôn ngữ ('vi' hoặc 'en')
        """
        uid = int(user_id)

        if not self.voice_service:
            raise ValueError("VoiceService chưa được inject")

        # 1. STT
        transcribed = await self.voice_service.transcribe(audio_bytes, language=language)
        voice_key = transcribed.strip() if transcribed else ""

        if len(voice_key) < 3:
            raise HTTPException(
                status_code=422,
                detail="Không nhận diện được lời nói rõ ràng (cần ít nhất 3 ký tự)"
            )

        logger.info(f"[Enroll STT] User {uid} | Lang: {language} | Text: '{voice_key}'")

        # 2. Extract embedding
        audio_np = await self.audio_service.process_audio(audio_bytes)
        embedding = self.audio_service.extract_features(audio_np)
        emb_bytes = embedding.tobytes()

        logger.info(
            f"[Enroll] User {uid} | embedding_dim={len(embedding)} | "
            f"{'MFCC+GE2E fused' if len(embedding) > 200 else 'MFCC-only fallback'}"
        )

        # 3. Lưu DB (kèm language)
        success = UserRepository.save_voice_enrollment(
            user_id=uid,
            embedding=emb_bytes,
            voice_key_text=voice_key,
            language=language  # Lưu ngôn ngữ đã đăng ký
        )

        if success:
            logger.info(f"✅ Enrolled user {uid} | lang={language} | key='{voice_key[:60]}'")

        return success, transcribed or ""

    # ── Verify ────────────────────────────────────────────────────────────────

    async def verify_voice(
        self, 
        user_id: str, 
        audio_bytes: bytes, 
        transcribed_text: str
    ) -> tuple[bool, float, str]:
        """
        Two-factor verification:
          1. Text matching
          2. Voice embedding matching
        """
        uid = int(user_id)
        user = UserRepository.get_by_id(uid)

        if not user or not user.voice_embedding:
            raise HTTPException(
                status_code=404,
                detail="User chưa đăng ký giọng nói"
            )

        stored_vector = np.frombuffer(user.voice_embedding, dtype=np.float32)
        voice_key = user.voice_key_text or ""

        if not voice_key:
            raise HTTPException(status_code=400, detail="Chưa có voice key trong DB")

        if stored_vector.size == 0:
            raise HTTPException(status_code=500, detail="Embedding rỗng trong DB")

        # ── Factor 1: Text match ──────────────────────────────────────────────
        text_sim = _text_sim(transcribed_text, voice_key)

        logger.info(
            f"[Verify Text] user={uid} | "
            f"spoken='{transcribed_text}' | key='{voice_key}' | sim={text_sim:.2f}"
        )

        if text_sim < self.text_threshold:
            return False, 0.0, (
                f"Nội dung không khớp ({text_sim:.0%}) — "
                f"hãy đọc đúng câu đã đăng ký"
            )

        # ── Factor 2: Voice embedding ─────────────────────────────────────────
        try:
            is_match, score = self.audio_service.verify_voice(
                user.voice_embedding,
                audio_bytes,
                self.voice_threshold,
            )
        except ValueError as ve:
            raise HTTPException(status_code=422, detail=str(ve))
        except Exception as e:
            logger.exception("Lỗi verify embedding")
            raise HTTPException(status_code=503, detail="Lỗi xử lý giọng nói")

        emb_dim = stored_vector.size
        logger.info(
            f"[Verify Voice] user={uid} | score={score:.4f} | "
            f"match={is_match} | dim={emb_dim} | "
            f"{'MFCC+GE2E' if emb_dim > 200 else 'MFCC-only'}"
        )

        if not is_match:
            return False, score, (
                f"Giọng nói không khớp (score={score:.3f}, "
                f"cần ≥{self.voice_threshold})"
            )

        return True, score, ""

    # ── Delete ────────────────────────────────────────────────────────────────

    async def delete_voice(self, user_id: str) -> bool:
        return UserRepository.delete_voice_enrollment(int(user_id))