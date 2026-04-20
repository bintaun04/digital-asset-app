# backend/app/engines/voice_engine.py
import logging
import numpy as np
from typing import Dict, Any

from .stt.whisper_engine import WhisperEngine

logger = logging.getLogger("VoiceEngine")

class VoiceEngine:
    """
    Voice Engine chính - Chỉ xử lý STT (Whisper) sau khi đã xác thực thành công
    """

    def __init__(self, config: dict):
        logger.info("Đang khởi tạo VoiceEngine...")
        whisper_config = config.get("whisper", {})
        self.stt = WhisperEngine(whisper_config)
        logger.info("✅ VoiceEngine đã sẵn sàng.")

    def transcribe(self, audio_data: np.ndarray) -> str:
        """Chuyển giọng nói thành văn bản"""
        result = self.stt.transcribe(audio_data)
        return result.get("text", "").strip()

    def process_voice_command(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """
        Xử lý lệnh sau khi đã xác thực giọng nói thành công
        """
        try:
            text = self.transcribe(audio_data)

            if not text:
                return {"status": "error", "message": "Không nhận diện được lời nói"}

            logger.info(f"[USER COMMAND] {text}")

            # TODO: Sau này sẽ gọi LLM để xử lý intent (check balance, transfer, etc.)
            return {
                "status": "success",
                "user_text": text,
                "ai_response": f"Bạn vừa nói: '{text}'. Hệ thống đang xử lý lệnh...",
                "action": "pending"
            }

        except Exception as e:
            logger.error(f"Lỗi xử lý voice command: {e}")
            return {"status": "error", "message": str(e)}