# backend/app/services/voice_service.py
import logging
import numpy as np
from typing import Dict, Any

from ..engines.voice_engine import VoiceEngine
from .audio_service import AudioService

logger = logging.getLogger("VoiceService")

class VoiceService:
    def __init__(self, config: dict):
        self.audio_service = AudioService()
        self.voice_engine = VoiceEngine(config)
    
    async def transcribe(self, audio_bytes: bytes) -> str:
            try:
                audio_np = await self.audio_service.process_audio(audio_bytes)

                # Tiền xử lý mạnh
                if np.max(np.abs(audio_np)) > 0:
                    audio_np = audio_np / np.max(np.abs(audio_np)) * 0.95   # normalize + giảm clipping

                # Noise reduction đơn giản
                audio_np = np.where(np.abs(audio_np) < 0.025, 0.0, audio_np)

                result = self.voice_engine.transcribe(audio_np)
                text = result.get("text", "").strip()

                logger.info(f"[STT] Input: {len(audio_np)/16000:.1f}s | Output: '{text}'")
                return text

            except Exception as e:
                logger.error(f"Lỗi transcribe: {e}")
                return ""

    async def process_command_only(
        self, audio_bytes: bytes, user_id: int = 1
    ) -> Dict[str, Any]:
        """Chỉ chạy STT cho lệnh sau khi verify"""
        try:
            text = await self.transcribe(audio_bytes)

            if not text:
                return {
                    "status": "error",
                    "user_text": "",
                    "message": "Không nhận diện được lời nói"
                }

            logger.info(f"[Command STT] user={user_id} | text='{text}'")

            return {
                "status": "success",
                "user_text": text,
                "ai_response": f"Bạn vừa nói: '{text}'",
            }

        except Exception as e:
            logger.exception(f"Lỗi process_command_only user {user_id}")
            return {
                "status": "error",
                "user_text": "",
                "message": str(e)
            }