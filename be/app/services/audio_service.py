# backend/app/services/audio_service.py
import numpy as np
from ..engines.stt.audio_processor import convert_to_wav
from .mfcc_processor import MFCCProcessor


class AudioService:
    def __init__(self):
        self.mfcc_processor = MFCCProcessor()

    async def process_audio(self, audio_bytes: bytes) -> np.ndarray:
        """Chuẩn hóa audio → float32 numpy array"""
        try:
            audio_np = convert_to_wav(audio_bytes)
            # Normalize về [-1, 1]
            audio_np = audio_np / (np.max(np.abs(audio_np)) + 1e-8)
            return audio_np.astype(np.float32)
        except Exception as e:
            raise ValueError(f"Lỗi xử lý audio: {str(e)}")

    def extract_features(self, audio_np: np.ndarray) -> np.ndarray:
        """Trích xuất MFCC + DFT features — tên đúng để BiometricService gọi"""
        return self.mfcc_processor.extract_features(audio_np)

    # Alias để không breaking nếu code khác gọi tên cũ
    def extract_mfcc(self, audio_np: np.ndarray) -> np.ndarray:
        return self.extract_features(audio_np)

    def verify_voice(
        self,
        stored_embedding: bytes,
        audio_bytes: bytes,
        threshold: float = 0.78,
    ):
        """Xác thực giọng nói – so sánh cosine với embedding đã lưu"""
        audio_np = convert_to_wav(audio_bytes)
        # Normalize trước khi so sánh
        audio_np = audio_np / (np.max(np.abs(audio_np)) + 1e-8)

        test_vector = self.extract_features(audio_np)
        stored_vector = np.frombuffer(stored_embedding, dtype=np.float32)

        return self.mfcc_processor.compare(test_vector, stored_vector, threshold)