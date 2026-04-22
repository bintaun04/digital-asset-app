# backend/app/engines/voice_engine.py
import logging
import os
from typing import Dict, Optional
import numpy as np

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

class VoiceEngine:
    def __init__(self, config: Optional[dict] = None):
        cfg = config or {
            # 🔥 NÂNG CẤP LÊN MEDIUM (chính xác hơn SMALL rất nhiều)
            "model_size": "vinai/PhoWhisper-medium", 
            "device": "cpu",
            "compute_type": "int8",
            "language": "vi",         # 🔥 KHÓA TIẾNG VIỆT
            "beam_size": 5,
            "vad_filter": True        # 🔥 LỌC TẠP ÂM
        }

        self.model_size = cfg.get("model_size", "vinai/PhoWhisper-small")
        self.device = cfg.get("device", "cpu")
        self.compute_type = cfg.get("compute_type", "int8")
        self.language = cfg.get("language", "vi")
        self.beam_size = cfg.get("beam_size", 5)
        self.vad_filter = cfg.get("vad_filter", False)

        logger.info(f"🧠 Loading Whisper Model: {self.model_size} | Device: {self.device}")

        try:
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info("✅ Whisper Model Loaded!")
        except Exception as e:
            logger.error(f"❌ Load failed: {e}")
            self.model = WhisperModel("small", device=self.device, compute_type=self.compute_type)

    def transcribe(self, audio: np.ndarray) -> Dict:
        """STT với Prompt Engineering để chống ảo giác"""
        if len(audio) == 0:
            return {"text": "", "error": "Audio empty"}

        try:
            # 🔥 MẸO CHỐNG ẢO GIÁC: Dùng prompt ép format
            # Nó sẽ ưu tiên tìm text sau chữ "Text:"
            segments, info = self.model.transcribe(
                audio,
                language=self.language,
                beam_size=self.beam_size,
                vad_filter=self.vad_filter,
                # 🔥 ÉP BUỘC PROMPT
                initial_prompt="Text: " 
            )

            full_text = [segment.text.strip() for segment in segments if segment.text.strip()]
            raw_text = " ".join(full_text)

            # 🔥 LỌC BỎ PROMPT RA KHỎI KẾT QUẢ
            if raw_text.startswith("Text:"):
                raw_text = raw_text[5:].strip()

            return {
                "text": raw_text,
                "language": info.language,
                "language_probability": round(getattr(info, 'language_probability', 0.0), 3),
            }

        except Exception as e:
            logger.error(f"Error transcribe: {e}")
            return {"text": "", "error": str(e)}