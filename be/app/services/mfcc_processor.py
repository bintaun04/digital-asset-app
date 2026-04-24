# backend/app/services/mfcc_processor.py
"""
Speaker Verification: MFCC (124-d) + Resemblyzer GE2E (256-d) → fused (380-d)

Toàn bộ logic xử lý nằm trong file này — audio_service.py không cần đổi.

Cài thêm: pip install resemblyzer
Nếu chưa cài → tự động fallback MFCC 124-d (kém hơn).
"""

import logging
import numpy as np
from typing import Tuple

logger = logging.getLogger("MFCCProcessor")

SAMPLE_RATE = 16_000
N_MFCC      = 20
N_FFT       = 512
HOP_LENGTH  = 160

_encoder = None  # lazy-load, chỉ load 1 lần


def _get_encoder():
    """Load Resemblyzer VoiceEncoder 1 lần duy nhất."""
    global _encoder
    if _encoder is None:
        try:
            from resemblyzer import VoiceEncoder
            _encoder = VoiceEncoder(device="cpu")
            logger.info("✅ Resemblyzer GE2E loaded — dùng fused 380-d")
        except ImportError:
            logger.warning(
                "⚠️  resemblyzer chưa cài → fallback MFCC 124-d\n"
                "   Chạy: pip install resemblyzer"
            )
            _encoder = "fallback"
    return _encoder


class MFCCProcessor:
    """
    Tự động chọn chế độ:
      ✅ Có resemblyzer  → MFCC 124-d ++ GE2E 256-d → fused 380-d  (phân biệt người chính xác)
      ⚠️  Không có       → MFCC 124-d                               (dễ bị bypass, chỉ tạm thời)
    """

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    # ── API chính (audio_service.py gọi vào đây) ─────────────────────────────

    def extract_features(self, audio: np.ndarray) -> np.ndarray:
        """
        Trả về speaker embedding vector đã L2-normalize.
        Shape: (380,) nếu có resemblyzer | (124,) nếu fallback.
        """
        mfcc_vec = self._extract_mfcc(audio)        # luôn tính MFCC

        enc = _get_encoder()
        if enc == "fallback":
            logger.debug("[extract] MFCC-only 124-d")
            return mfcc_vec

        ge2e_vec = self._extract_ge2e(audio, enc)   # (256,) L2-normed

        # Weighted concat — GE2E quan trọng hơn MFCC để phân biệt người
        fused = np.concatenate([
            mfcc_vec,           # 124-d  (vocal tract / cách phát âm)
            ge2e_vec * 2.0,     # 256-d  (voice identity sinh học) — weight 2x
        ])

        norm = np.linalg.norm(fused)
        result = (fused / norm if norm > 0 else fused).astype(np.float32)
        logger.debug(f"[extract] Fused 380-d | mfcc_norm={np.linalg.norm(mfcc_vec):.3f} | ge2e_norm={np.linalg.norm(ge2e_vec):.3f}")
        return result

    def extract_mfcc(self, audio: np.ndarray) -> np.ndarray:
        """Alias backward compat cho các chỗ gọi tên cũ."""
        return self.extract_features(audio)

    def compare(
        self,
        vec1: np.ndarray,
        vec2: np.ndarray,
        threshold: float = 0.75,
    ) -> Tuple[bool, float]:
        """
        Cosine similarity giữa 2 embedding.

        Threshold mặc định:
          0.75 → fused 380-d  (MFCC + GE2E)
          0.82 → MFCC-only 124-d  (kém, dùng tạm)

        Shape không khớp = user enroll lúc chưa cài resemblyzer,
        giờ đã cài → cần re-enroll.
        """
        if vec1.shape != vec2.shape:
            logger.error(
                f"⚠️  Shape mismatch: stored={vec1.shape} vs new={vec2.shape}\n"
                "   User cần re-enroll sau khi nâng cấp processor."
            )
            return False, 0.0

        v1    = vec1 / (np.linalg.norm(vec1) + 1e-8)
        v2    = vec2 / (np.linalg.norm(vec2) + 1e-8)
        score = float(np.dot(v1, v2))

        logger.debug(f"[compare] score={score:.4f} threshold={threshold} match={score >= threshold}")
        return score >= threshold, round(score, 4)

    # ── MFCC 124-d ────────────────────────────────────────────────────────────

    def _extract_mfcc(self, audio: np.ndarray) -> np.ndarray:
        """
        MFCC(20) + Delta(20) + Delta2(20) → mean+std pooling → 120-d
        + spectral_centroid, spectral_rolloff, zcr, rms → 4-d
        = 124-d, L2-normalized
        """
        import librosa

        if len(audio) < N_FFT:
            raise ValueError(
                f"Audio quá ngắn: {len(audio)} samples (cần ít nhất {N_FFT} ~ 32ms)"
            )

        # MFCC + delta + delta2
        mfcc   = librosa.feature.mfcc(
            y=audio, sr=self.sample_rate,
            n_mfcc=N_MFCC, n_fft=N_FFT,
            hop_length=HOP_LENGTH, n_mels=128,
        )
        d1     = librosa.feature.delta(mfcc)
        d2     = librosa.feature.delta(mfcc, order=2)
        feat   = np.concatenate([mfcc, d1, d2], axis=0)   # (60, T)

        # Temporal pooling: mean + std → (120,)
        stat   = np.concatenate([feat.mean(axis=1), feat.std(axis=1)])

        # DFT-based spectral features
        extra  = np.array([
            float(np.mean(librosa.feature.spectral_centroid(y=audio, sr=self.sample_rate))),
            float(np.mean(librosa.feature.spectral_rolloff(y=audio,  sr=self.sample_rate))),
            float(np.mean(librosa.feature.zero_crossing_rate(y=audio))),
            float(np.mean(librosa.feature.rms(y=audio))),
        ], dtype=np.float32)

        # Normalize extra về cùng scale MFCC
        extra  = extra / (np.linalg.norm(extra) + 1e-8)

        vec    = np.concatenate([stat, extra]).astype(np.float32)   # (124,)
        norm   = np.linalg.norm(vec)
        return (vec / norm if norm > 0 else vec)

    # ── Resemblyzer GE2E 256-d ────────────────────────────────────────────────

    def _extract_ge2e(self, audio: np.ndarray, encoder) -> np.ndarray:
        """
        GE2E (Generalized End-to-End Loss) speaker embedding.
        Model train với contrastive loss:
          → cùng người  : embedding gần nhau  (score > 0.8)
          → khác người  : embedding xa nhau   (score < 0.5)
        Output: (256,) float32, đã L2-normalize.
        """
        from resemblyzer import preprocess_wav

        # Normalize amplitude
        if np.max(np.abs(audio)) > 0:
            audio = audio / np.max(np.abs(audio))

        # preprocess_wav: trim silence + resample nếu cần
        wav       = preprocess_wav(audio, source_sr=self.sample_rate)
        embedding = encoder.embed_utterance(wav)   # (256,) đã L2-norm bởi resemblyzer
        return embedding.astype(np.float32)