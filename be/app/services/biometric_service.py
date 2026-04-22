# backend/app/services/biometric_service.py
import logging
from difflib import SequenceMatcher
import numpy as np
from fastapi import HTTPException, status

from .audio_service import AudioService
from ..repository.user_repo import UserRepository

logger = logging.getLogger("BiometricService")

VOICE_THRESHOLD = 0.82
TEXT_MATCH_THRESHOLD = 0.75


def _text_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()


class BiometricService:
    def __init__(self, voice_service=None):  # ← Inject VoiceService để dùng STT
        self.audio_service = AudioService()
        self.voice_service = voice_service
        self.voice_threshold = VOICE_THRESHOLD
        self.text_threshold = TEXT_MATCH_THRESHOLD

    async def enroll_voice(self, user_id: str, audio_bytes: bytes) -> bool:
        """Auto-STT → voice_key + embedding → SAVE"""
        uid = int(user_id)

        # 1. STT để lấy voice_key_text tự động
        if not self.voice_service:
            raise ValueError("VoiceService chưa được inject")
        
        transcribed = await self.voice_service.transcribe(audio_bytes)
        if not transcribed or len(transcribed.strip()) < 3:
            raise HTTPException(
                status_code=422,
                detail="Không nhận diện được lời nói rõ ràng (ít nhất 3 ký tự)"
            )
        
        voice_key_text = transcribed.strip().lower()
        logger.info(f"[Enroll] Auto-STT user {uid}: '{voice_key_text}'")

        # 2. Trích xuất embedding
        audio_np = await self.audio_service.process_audio(audio_bytes)
        embedding = self.audio_service.extract_features(audio_np)
        embedding_bytes = embedding.tobytes()

        # 3. Lưu vào DB
        success = UserRepository.save_voice_enrollment(
            user_id=uid,
            embedding=embedding_bytes,
            voice_key_text=voice_key_text,
        )

        if success:
            logger.info(
                f"✅ Enrolled user {uid} | "
                f"key='{voice_key_text[:50]}...' | "
                f"dim={len(embedding)}"
            )
        return success

    async def verify_voice(
        self, user_id: str, audio_bytes: bytes, transcribed_text: str
    ) -> tuple[bool, float, str]:
        """Two-Factor: text match + embedding match"""
        uid = int(user_id)
        user = UserRepository.get_by_id(uid)
        
        if not user or not user.voice_embedding:
            raise HTTPException(status_code=404, detail="User chưa đăng ký giọng nói")
        
        stored_vector = np.frombuffer(user.voice_embedding, dtype=np.float32)
        voice_key = user.voice_key_text or ""
        
        if not voice_key:
            raise HTTPException(status_code=400, detail="Chưa có voice key")

        # Factor 1: Text match
        text_sim = _text_similarity(transcribed_text, voice_key)
        if text_sim < self.text_threshold:
            return False, 0.0, f"Nội dung không khớp ({text_sim:.1%})"

        # Factor 2: Voice embedding
        is_match, score = self.audio_service.verify_voice(
            user.voice_embedding, audio_bytes, self.voice_threshold
        )
        
        fail_msg = "" if is_match else f"Giọng không khớp (score={score:.3f})"
        return is_match, score, fail_msg

    async def delete_voice(self, user_id: str) -> bool:
        return UserRepository.delete_voice_enrollment(int(user_id))
    
    async def enroll_voice_with_stt(self, user_id: str, audio_bytes: bytes) -> tuple[bool, str]:
        """Enroll + trả về transcribed text để debug"""
        uid = int(user_id)

        # 1. STT
        transcribed = await self.voice_service.transcribe(audio_bytes)
        voice_key_text = transcribed.strip().lower() if transcribed else ""

        if len(voice_key_text) < 5:
            logger.warning(f"[Enroll] STT quá ngắn: '{voice_key_text}'")
            return False, transcribed or "Không nhận diện được"

        logger.info(f"[Enroll STT] User {uid} → '{voice_key_text}'")

        # 2. Extract embedding
        audio_np = await self.audio_service.process_audio(audio_bytes)
        embedding = self.audio_service.extract_features(audio_np)
        embedding_bytes = embedding.tobytes()

        # 3. Lưu vào DB - KHÔNG DÙNG AWAIT (vì repo đã là đồng bộ)
        success = UserRepository.save_voice_enrollment(   # ← XÓA CHỮ "await"
            user_id=uid,
            embedding=embedding_bytes,
            voice_key_text=voice_key_text,
        )

        if success:
            logger.info(f"✅ Enrolled user {uid} | key='{voice_key_text[:60]}...'")
        
        return success, transcribed