# backend/app/services/mfcc_processor.py
import numpy as np
import librosa
from typing import Tuple

SAMPLE_RATE = 16000
N_MFCC = 13
N_FFT = 512
HOP_LENGTH = 160

class MFCCProcessor:
    """
    MFCC + DFT Feature Extraction cho Speaker Verification
    """

    def __init__(self):
        self.sample_rate = SAMPLE_RATE

    def extract_features(self, audio: np.ndarray) -> np.ndarray:
        """
        Trích xuất đặc trưng: MFCC 39 chiều + năng lượng từ DFT
        """
        if len(audio) < N_FFT:
            raise ValueError(f"Audio quá ngắn (cần ít nhất {N_FFT} samples)")

        # 1. MFCC Static (13)
        mfcc = librosa.feature.mfcc(
            y=audio,
            sr=self.sample_rate,
            n_mfcc=N_MFCC,
            n_fft=N_FFT,
            hop_length=HOP_LENGTH,
            n_mels=128
        )

        # 2. Delta và Delta2 (tăng độ nhạy cảm với chuyển động giọng nói)
        delta = librosa.feature.delta(mfcc)
        delta2 = librosa.feature.delta(mfcc, order=2)

        # 3. Ghép thành 39 chiều
        mfcc_features = np.concatenate([mfcc, delta, delta2], axis=0)

        # 4. Mean + Std pooling để có vector cố định
        mean_features = np.mean(mfcc_features, axis=1)
        std_features = np.std(mfcc_features, axis=1)

        # 5. Thêm Spectral Centroid & RMS Energy từ DFT
        spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=audio, sr=self.sample_rate))
        rms_energy = np.mean(librosa.feature.rms(y=audio))

        # Ghép tất cả thành vector đặc trưng cuối cùng
        final_vector = np.concatenate([
            mean_features,
            std_features,
            [spectral_centroid, rms_energy]
        ])

        return final_vector.astype(np.float32)

    def compare(self, vec1: np.ndarray, vec2: np.ndarray, threshold: float = 0.78) -> Tuple[bool, float]:
        """So sánh bằng Cosine Similarity"""
        if vec1.shape != vec2.shape:
            return False, 0.0

        v1 = vec1 / (np.linalg.norm(vec1) + 1e-8)
        v2 = vec2 / (np.linalg.norm(vec2) + 1e-8)

        similarity = np.dot(v1, v2)
        is_match = similarity >= threshold

        return is_match, round(float(similarity), 4)