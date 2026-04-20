# backend/app/services/voice_service.py
import logging
from typing import Dict, Any

from ..engines.voice_engine import VoiceEngine
from .audio_service import AudioService
from .biometric_service import BiometricService

logger = logging.getLogger("VoiceService")

class VoiceService:
    def __init__(self, config: dict):
        self.audio_service = AudioService()
        self.voice_engine = VoiceEngine(config)
        self.biometric = BiometricService()

    async def process_full_command(self, audio_bytes: bytes, user_id: int = 1) -> Dict[str, Any]:
        """Pipeline: Verify → STT"""
        # Bước 1: Xác thực giọng nói trước
        is_match, score = await self.biometric.verify_voice(user_id, audio_bytes)
        
        if not is_match:
            return {
                "status": "unauthorized",
                "message": f"Xác thực thất bại (Score: {score:.4f})",
                "score": score
            }

        # Bước 2: Nếu xác thực thành công → chạy Whisper
        try:
            audio_np = await self.audio_service.process_audio(audio_bytes)
            result = self.voice_engine.process_voice_command(audio_np)

            return {
                "status": "success",
                "user_text": self.voice_engine.transcribe(audio_np),
                "ai_response": result.get("ai_response", ""),
                "score": score
            }
        except Exception as e:
            logger.error(f"Lỗi xử lý lệnh: {e}")
            return {"status": "error", "message": str(e)}