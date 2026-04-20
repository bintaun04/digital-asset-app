# backend/app/services/biometric_service.py
import logging
from fastapi import HTTPException

from .audio_service import AudioService
from ..repository.user_repo import UserRepository

logger = logging.getLogger("BiometricService")

class BiometricService:
    """
    Xác thực giọng nói sử dụng MFCC + DFT
    """

    def __init__(self):
        self.audio_service = AudioService()
        self.voice_threshold = 0.80   # Độ khắt khe

    async def enroll_voice(self, user_id: int, audio_bytes: bytes) -> bool:
        """Đăng ký giọng nói"""
        try:
            audio_np = await self.audio_service.process_audio(audio_bytes)
            embedding = self.audio_service.extract_features(audio_np)

            success = await UserRepository.update_voice_embedding(user_id, embedding.tobytes())
            if success:
                logger.info(f"✅ [MFCC+DFT] Đăng ký giọng nói user {user_id} thành công")
            return success
        except Exception as e:
            logger.error(f"Lỗi enroll voice user {user_id}: {e}")
            return False

    async def verify_voice(self, user_id: int, audio_bytes: bytes) -> tuple:
        """Xác thực giọng nói"""
        user = await UserRepository.get_by_id(user_id)
        if not user or not user.voice_embedding:
            raise HTTPException(status_code=400, detail="User chưa đăng ký giọng nói")

        try:
            is_match, score = self.audio_service.verify_voice(
                stored_embedding=user.voice_embedding,
                audio_bytes=audio_bytes,
                threshold=self.voice_threshold
            )

            logger.info(f"[MFCC+DFT Verify] User {user_id} | Score: {score:.4f} | Match: {is_match}")
            return is_match, score

        except Exception as e:
            logger.error(f"Lỗi verify voice: {e}")
            raise HTTPException(status_code=500, detail="Lỗi xử lý giọng nói")

    async def update_voice(self, user_id: int, audio_bytes: bytes) -> bool:
        """Cập nhật giọng nói"""
        return await self.enroll_voice(user_id, audio_bytes)

    async def delete_voice(self, user_id: int) -> bool:
        """Xóa giọng nói"""
        success = await UserRepository.delete_voice_embedding(user_id)
        if success:
            logger.info(f"✅ Đã xóa giọng nói của user {user_id}")
        return success