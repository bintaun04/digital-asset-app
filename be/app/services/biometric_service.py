# backend/app/services/biometric_service.py
import logging
from fastapi import HTTPException

from .audio_service import AudioService
from ..repository.user_repo import UserRepository

logger = logging.getLogger("BiometricService")

class BiometricService:
    def __init__(self):
        self.audio_service = AudioService()
        self.voice_threshold = 0.80

    async def verify_voice(self, user_id: int, audio_bytes: bytes) -> tuple:
        user = await UserRepository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User không tồn tại")

        if not user.voice_embedding:
            raise HTTPException(status_code=404, detail="User chưa đăng ký giọng nói")

        if not isinstance(user.voice_embedding, (bytes, bytearray)):
            raise HTTPException(status_code=500, detail="Dữ liệu embedding không hợp lệ (không phải bytes)")

        stored_vector = np.frombuffer(user.voice_embedding, dtype=np.float32)
        if stored_vector.size == 0:
            raise HTTPException(status_code=500, detail="Embedding rỗng")

        logger.info(f"[Verify] user_id={user_id} | embedding_len={stored_vector.size} | threshold={self.voice_threshold}")

        try:
            is_match, score = self.audio_service.verify_voice(
                stored_embedding=user.voice_embedding,
                audio_bytes=audio_bytes,
                threshold=self.voice_threshold
            )
            logger.info(f"[Verify] Score: {score:.4f} | Match: {is_match}")
            return is_match, score
        except ValueError as ve:
            raise HTTPException(status_code=422, detail=str(ve))
        except Exception as e:
            logger.exception("Lỗi verify voice")
            raise HTTPException(status_code=503, detail="Lỗi xử lý giọng nói")

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