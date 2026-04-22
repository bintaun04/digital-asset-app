# backend/app/services/audio_service.py
import numpy as np
from ..engines.stt.audio_processor import convert_to_wav
from .mfcc_processor import MFCCProcessor


class AudioService:
    def __init__(self):
        self.mfcc_processor = MFCCProcessor()

    async def process_audio(self, audio_bytes: bytes) -> np.ndarray:
        """Bytes → float32 numpy array 16 kHz mono, normalized [-1, 1]."""
        try:
            audio_np = convert_to_wav(audio_bytes)
            peak = np.max(np.abs(audio_np))
            if peak > 0:
                audio_np = audio_np / peak
            return audio_np.astype(np.float32)
        except Exception as e:
            raise ValueError(f"Lỗi xử lý audio: {str(e)}")

    def extract_features(self, audio_np: np.ndarray) -> np.ndarray:
        """Trích xuất MFCC + DFT feature vector."""
        return self.mfcc_processor.extract_features(audio_np)

    def verify_voice(
        self,
        stored_embedding: bytes,
        audio_bytes: bytes,
        threshold: float = 0.82,
    ) -> tuple[bool, float]:
        """
        So sánh audio_bytes với stored_embedding (bytes).
        Trả về (is_match, cosine_score).
        """
        audio_np = convert_to_wav(audio_bytes)
        peak = np.max(np.abs(audio_np))
        if peak > 0:
            audio_np = audio_np / peak

        test_vector   = self.extract_features(audio_np)
        stored_vector = np.frombuffer(stored_embedding, dtype=np.float32)

        return self.mfcc_processor.compare(test_vector, stored_vector, threshold)