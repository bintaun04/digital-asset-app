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

    def transcribe(self, audio: np.ndarray, language: Optional[str] = None) -> Dict:
        """STT với hỗ trợ đa ngôn ngữ (vi/en)"""
        if len(audio) == 0:
            return {"text": "", "error": "Audio empty"}

        try:
            # Sử dụng ngôn ngữ được chỉ định hoặc mặc định
            target_language = language or self.language
            
            segments, info = self.model.transcribe(
                audio,
                language=target_language,
                beam_size=self.beam_size,
                vad_filter=self.vad_filter,
                initial_prompt="Text: " 
            )

            full_text = [segment.text.strip() for segment in segments if segment.text.strip()]
            raw_text = " ".join(full_text)

            # Loại bỏ prompt nếu có
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


class MultiLanguageVoiceEngine:
    """Engine hỗ trợ cả tiếng Việt và tiếng Anh"""
    
    def __init__(self, config: Optional[dict] = None):
        # Engine tiếng Việt (PhoWhisper)
        vi_config = {
            "model_size": "vinai/PhoWhisper-medium",
            "device": "cpu",
            "compute_type": "int8",
            "language": "vi",
            "beam_size": 5,
            "vad_filter": True
        }
        
        # Engine tiếng Anh (OpenAI Whisper)
        en_config = {
            "model_size": "medium.en",  # Whisper English-only model
            "device": "cpu",
            "compute_type": "int8",
            "language": "en",
            "beam_size": 5,
            "vad_filter": True
        }
        
        # Override với config từ ngoài nếu có
        if config:
            vi_config.update({k: v for k, v in config.items() if k != "language"})
            en_config.update({k: v for k, v in config.items() if k != "language"})
        
        self.vi_engine = VoiceEngine(vi_config)
        self.en_engine = VoiceEngine(en_config)
        
        logger.info("✅ Multi-language Voice Engine initialized (VI + EN)")
    
    def transcribe(self, audio: np.ndarray, language: str = "vi") -> Dict:
        """
        Transcribe audio với ngôn ngữ được chỉ định
        
        Args:
            audio: Audio numpy array
            language: 'vi' hoặc 'en'
        """
        if language.lower() == "en":
            return self.en_engine.transcribe(audio, language="en")
        else:
            return self.vi_engine.transcribe(audio, language="vi")