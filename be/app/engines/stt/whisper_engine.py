# backend/app/engines/stt/whisper_engine.py
import logging
import os
from typing import Dict, Optional

import numpy as np

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

class WhisperEngine:
    """
    Whisper Engine cho Speech-to-Text (chỉ chạy sau khi verify giọng nói thành công)
    """

    def __init__(self, config: Optional[dict] = None):
        cfg = config or {
            "model_size": "vinai/PhoWhisper-medium",
            "device": "cpu",
            "compute_type": "int8",
            "language": "vi",
            "beam_size": 5,
            "vad_filter": True
        }

        self.model_size = cfg.get("model_size", "vinai/PhoWhisper-small")
        self.device = cfg.get("device", "cpu")
        self.compute_type = cfg.get("compute_type", "int8")
        self.language = cfg.get("language", "vi")
        self.beam_size = cfg.get("beam_size", 5)
        self.vad_filter = cfg.get("vad_filter", True)

        logger.info(f"Đang tải Whisper model: {self.model_size} | Device: {self.device}")

        try:
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info("✅ Whisper model tải thành công!")
        except Exception as e:
            logger.error(f"❌ Lỗi tải Whisper model: {e}")
            # Fallback sang model nhỏ hơn nếu lỗi
            self.model = WhisperModel("small", device=self.device, compute_type=self.compute_type)
            logger.info("✅ Đã fallback sang model 'small'")

    def transcribe(self, audio: np.ndarray) -> Dict:
        """Chuyển audio thành văn bản"""
        if len(audio) == 0:
            return {"text": "", "error": "Audio rỗng"}

        try:
            segments, info = self.model.transcribe(
                audio,
                language=self.language,
                beam_size=self.beam_size,
                vad_filter=self.vad_filter,
                condition_on_previous_text=False,
            )

            full_text = [segment.text.strip() for segment in segments if segment.text.strip()]

            return {
                "text": " ".join(full_text).strip(),
                "language": info.language,
                "language_probability": round(getattr(info, 'language_probability', 0.0), 3),
            }

        except Exception as e:
            logger.error(f"Lỗi transcribe Whisper: {e}")
            return {"text": "", "error": str(e)}