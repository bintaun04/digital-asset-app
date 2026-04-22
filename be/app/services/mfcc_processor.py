# backend/app/services/mfcc_processor.py
import numpy as np
import librosa
from typing import Tuple

SAMPLE_RATE = 16_000
N_MFCC     = 20        # tăng từ 13 → 20 để bắt nhiều đặc trưng hơn
N_FFT      = 512
HOP_LENGTH = 160
MIN_AUDIO_SAMPLES = N_FFT  # 512 samples ~ 32ms @ 16kHz


class MFCCProcessor:
    """
    MFCC + Delta + DFT Feature Extraction cho Speaker Verification.

    Vector đầu ra: 2*N_MFCC*2 + 4 = 84 chiều
        • mean/std của [mfcc, delta, delta2]  → 3 * N_MFCC * 2 = 120
        • spectral_centroid, spectral_rolloff,
          zero_crossing_rate, rms_energy        → 4
    """

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def extract_features(self, audio: np.ndarray) -> np.ndarray:
        """Trích xuất vector đặc trưng cố định từ raw audio float32."""
        if len(audio) < MIN_AUDIO_SAMPLES:
            raise ValueError(
                f"Audio quá ngắn: {len(audio)} samples "
                f"(cần ít nhất {MIN_AUDIO_SAMPLES})"
            )

        # ── 1. MFCC + Delta + Delta² ──────────────────────────────────
        mfcc = librosa.feature.mfcc(
            y=audio, sr=self.sample_rate,
            n_mfcc=N_MFCC, n_fft=N_FFT,
            hop_length=HOP_LENGTH, n_mels=128,
        )
        delta  = librosa.feature.delta(mfcc)
        delta2 = librosa.feature.delta(mfcc, order=2)

        # shape: (3*N_MFCC, T) → pool → (3*N_MFCC*2,)
        combined   = np.concatenate([mfcc, delta, delta2], axis=0)   # (60, T)
        stat_feats = np.concatenate([
            combined.mean(axis=1),
            combined.std(axis=1),
        ])                                                             # (120,)

        # ── 2. Spectral / Energy features (DFT-based) ────────────────
        spectral_centroid = float(np.mean(
            librosa.feature.spectral_centroid(y=audio, sr=self.sample_rate)
        ))
        spectral_rolloff = float(np.mean(
            librosa.feature.spectral_rolloff(y=audio, sr=self.sample_rate)
        ))
        zcr = float(np.mean(
            librosa.feature.zero_crossing_rate(y=audio)
        ))
        rms = float(np.mean(
            librosa.feature.rms(y=audio)
        ))

        extra = np.array(
            [spectral_centroid, spectral_rolloff, zcr, rms],
            dtype=np.float32,
        )

        # ── 3. Normalize extra features ──────────────────────────────
        # Đưa về cùng scale với MFCC để cosine không bị lệch
        extra_norm = extra / (np.linalg.norm(extra) + 1e-8)

        final = np.concatenate([stat_feats, extra_norm]).astype(np.float32)
        return final

    def compare(
        self,
        vec1: np.ndarray,
        vec2: np.ndarray,
        threshold: float = 0.82,
    ) -> Tuple[bool, float]:
        """
        Cosine Similarity giữa hai embedding vector.

        Returns:
            (is_match, score)  score ∈ [-1, 1]
        """
        if vec1.shape != vec2.shape:
            return False, 0.0

        v1 = vec1 / (np.linalg.norm(vec1) + 1e-8)
        v2 = vec2 / (np.linalg.norm(vec2) + 1e-8)
        score = float(np.dot(v1, v2))

        return score >= threshold, round(score, 4)