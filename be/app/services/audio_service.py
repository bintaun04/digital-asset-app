# backend/app/services/audio_service.py
import numpy as np
import logging
from ..engines.stt.audio_processor import convert_to_wav
from .mfcc_processor import MFCCProcessor

logger = logging.getLogger("AudioService")

SAMPLE_RATE = 16_000


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
        """Trích xuất MFCC + GE2E feature vector."""
        return self.mfcc_processor.extract_features(audio_np)

    def verify_voice(
        self,
        stored_embedding: bytes,
        audio_bytes: bytes,
        threshold: float = 0.82,
    ) -> tuple[bool, float]:
        """So sánh audio_bytes với stored_embedding. Trả về (is_match, score)."""
        audio_np = convert_to_wav(audio_bytes)
        peak = np.max(np.abs(audio_np))
        if peak > 0:
            audio_np = audio_np / peak
        test_vector   = self.extract_features(audio_np)
        stored_vector = np.frombuffer(stored_embedding, dtype=np.float32)
        return self.mfcc_processor.compare(test_vector, stored_vector, threshold)

    # ── Acoustic features ─────────────────────────────────────────────────────

    def extract_acoustic(self, audio_np: np.ndarray) -> dict:
        """
        Tính các thông số acoustic từ audio numpy array.
        Tất cả dùng librosa — không cần thư viện thêm.

        Trả về:
            duration_sec   float  — độ dài (giây)
            pitch_mean     float  — F0 trung bình (Hz), None nếu không tìm được
            pitch_std      float  — độ lệch chuẩn F0
            speaking_rate  float  — ước lượng tốc độ nói (onset/giây)
            energy_mean    float  — RMS trung bình
            energy_std     float  — RMS std
            snr_db         float  — Signal-to-Noise Ratio (dB)
            silence_ratio  float  — tỉ lệ frame im lặng [0-1]
            voice_quality  str    — "good" / "fair" / "poor"
        """
        import librosa

        sr  = SAMPLE_RATE
        out = {}

        # Duration
        out["duration_sec"] = round(len(audio_np) / sr, 3)

        # Energy (RMS)
        rms = librosa.feature.rms(y=audio_np, hop_length=160)[0]
        out["energy_mean"] = round(float(np.mean(rms)), 6)
        out["energy_std"]  = round(float(np.std(rms)),  6)

        # Silence ratio (frames where RMS < 5% of max)
        silence_thresh = np.max(rms) * 0.05 if np.max(rms) > 0 else 1e-6
        out["silence_ratio"] = round(float(np.mean(rms < silence_thresh)), 4)

        # SNR — signal frames vs noise frames
        try:
            signal_frames = rms[rms >= silence_thresh]
            noise_frames  = rms[rms <  silence_thresh]
            if len(signal_frames) > 0 and len(noise_frames) > 0:
                signal_power = float(np.mean(signal_frames ** 2))
                noise_power  = float(np.mean(noise_frames  ** 2))
                snr = 10 * np.log10(signal_power / (noise_power + 1e-10))
                out["snr_db"] = round(float(snr), 2)
            else:
                out["snr_db"] = None
        except Exception:
            out["snr_db"] = None

        # Pitch (F0) via pyin — chỉ lấy voiced frames
        try:
            f0, voiced_flag, _ = librosa.pyin(
                audio_np, fmin=60, fmax=400, sr=sr, hop_length=160
            )
            voiced_f0 = f0[voiced_flag] if voiced_flag is not None else f0
            voiced_f0 = voiced_f0[~np.isnan(voiced_f0)] if voiced_f0 is not None else []
            if len(voiced_f0) > 0:
                out["pitch_mean"] = round(float(np.mean(voiced_f0)), 2)
                out["pitch_std"]  = round(float(np.std(voiced_f0)),  2)
            else:
                out["pitch_mean"] = None
                out["pitch_std"]  = None
        except Exception:
            out["pitch_mean"] = None
            out["pitch_std"]  = None

        # Speaking rate — onset density (onsets per second)
        try:
            onsets = librosa.onset.onset_detect(
                y=audio_np, sr=sr, hop_length=160, units="time"
            )
            duration = out["duration_sec"] or 1.0
            out["speaking_rate"] = round(len(onsets) / duration, 3)
        except Exception:
            out["speaking_rate"] = None

        # Voice quality tổng hợp từ SNR + silence_ratio
        snr = out.get("snr_db")
        sil = out.get("silence_ratio", 1.0)
        if snr is not None and snr >= 15 and sil <= 0.30:
            out["voice_quality"] = "good"
        elif snr is not None and snr >= 8 and sil <= 0.50:
            out["voice_quality"] = "fair"
        else:
            out["voice_quality"] = "poor"

        return out

    # ── Full insight ──────────────────────────────────────────────────────────

    def compute_insight(
        self,
        stored_embedding: bytes,
        audio_bytes: bytes,
        threshold: float = 0.75,
    ) -> dict:
        """
        So sánh embedding + tính acoustic features của giọng vừa nói.
        Trả về dict đầy đủ để lưu vào voice_insights.
        """
        audio_np = convert_to_wav(audio_bytes)
        peak = np.max(np.abs(audio_np))
        if peak > 0:
            audio_np = audio_np / peak

        stored_vector = np.frombuffer(stored_embedding, dtype=np.float32)
        test_vector   = self.extract_features(audio_np)

        is_match, cosine_score = self.mfcc_processor.compare(
            test_vector, stored_vector, threshold
        )

        dim  = stored_vector.size
        mode = "MFCC+GE2E" if dim > 200 else "MFCC-only"

        # Tách MFCC / GE2E score riêng
        mfcc_score = ge2e_score = None
        if dim == 380 and test_vector.size == 380:
            def _cos(a, b):
                a = a / (np.linalg.norm(a) + 1e-8)
                b = b / (np.linalg.norm(b) + 1e-8)
                return round(float(np.dot(a, b)), 4)
            mfcc_score = _cos(stored_vector[:124], test_vector[:124])
            ge2e_score = _cos(stored_vector[124:], test_vector[124:])
        elif dim == 124 and test_vector.size == 124:
            sv = stored_vector / (np.linalg.norm(stored_vector) + 1e-8)
            tv = test_vector   / (np.linalg.norm(test_vector)   + 1e-8)
            mfcc_score = round(float(np.dot(sv, tv)), 4)

        # Confidence band
        gap = round(cosine_score - threshold, 4)
        if   cosine_score >= threshold + 0.08: confidence = "high"
        elif cosine_score >= threshold:         confidence = "medium"
        elif cosine_score >= threshold - 0.08: confidence = "low"
        else:                                   confidence = "very_low"

        # Acoustic features
        try:
            acoustic = self.extract_acoustic(audio_np)
        except Exception as e:
            logger.warning(f"extract_acoustic thất bại (bỏ qua): {e}")
            acoustic = {}

        return {
            # Embedding comparison
            "cosine_score":     round(cosine_score, 4),
            "is_match":         is_match,
            "threshold":        threshold,
            "embedding_dim":    dim,
            "mode":             mode,
            "mfcc_score":       mfcc_score,
            "ge2e_score":       ge2e_score,
            "confidence":       confidence,
            "gap_to_threshold": gap,
            # Acoustic
            "duration_sec":     acoustic.get("duration_sec"),
            "pitch_mean":       acoustic.get("pitch_mean"),
            "pitch_std":        acoustic.get("pitch_std"),
            "speaking_rate":    acoustic.get("speaking_rate"),
            "energy_mean":      acoustic.get("energy_mean"),
            "energy_std":       acoustic.get("energy_std"),
            "snr_db":           acoustic.get("snr_db"),
            "silence_ratio":    acoustic.get("silence_ratio"),
            "voice_quality":    acoustic.get("voice_quality"),
        }