# backend/app/engines/stt/audio_processor.py
"""
Convert audio bytes → numpy float32 array 16kHz mono
Không cần ffmpeg – xử lý hoàn toàn in-memory bằng soundfile + librosa.
Hỗ trợ: WAV, FLAC, OGG, MP3
"""

import io
import logging
import os
import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000


def convert_to_wav(audio_bytes: bytes, filename: str = "") -> np.ndarray:
    """
    Nhận raw bytes của bất kỳ định dạng audio nào,
    trả về numpy array float32 ở 16kHz mono.

    Không gọi ffmpeg, không tạo file tạm trên disk.
    """
    if not audio_bytes:
        raise ValueError("audio_bytes rỗng")

    ext = os.path.splitext(filename)[-1].lower() if filename else ""

    audio_np, sr = _load_bytes(audio_bytes, ext)

    # Stereo → mono
    if audio_np.ndim > 1:
        audio_np = audio_np.mean(axis=1)

    # Resample nếu cần
    if sr != SAMPLE_RATE:
        audio_np = _resample(audio_np, sr, SAMPLE_RATE)

    return audio_np.astype(np.float32)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_bytes(audio_bytes: bytes, ext: str = ""):
    """
    Thử soundfile trước (WAV/FLAC/OGG nhanh, không cần codec ngoài),
    fallback sang librosa nếu thất bại (hỗ trợ thêm MP3).
    """
    import soundfile as sf

    e_sf = None
    # Thử soundfile
    try:
        buf = io.BytesIO(audio_bytes)
        audio_np, sr = sf.read(buf, dtype="float32", always_2d=False)
        logger.debug(f"soundfile OK – sr={sr}, shape={audio_np.shape}")
        return audio_np, sr
    except Exception as e:
        e_sf = e
        logger.debug(f"soundfile failed: {e_sf} → thử librosa...")

    # Fallback: librosa (hỗ trợ MP3 qua audioread)
    try:
        import librosa
        buf = io.BytesIO(audio_bytes)
        audio_np, sr = librosa.load(buf, sr=None, mono=True)
        logger.debug(f"librosa OK – sr={sr}, shape={audio_np.shape}")
        return audio_np, sr
    except Exception as e_lb:
        raise ValueError(
            f"Không thể đọc audio.\n"
            f"  soundfile: {e_sf}\n"
            f"  librosa:   {e_lb}\n"
            f"Hỗ trợ định dạng: WAV, FLAC, OGG, MP3."
        )


def _resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """
    Resample bằng librosa (scipy bên dưới, không cần ffmpeg).
    Fallback sang linear interpolation nếu librosa không có.
    """
    try:
        import librosa
        logger.debug(f"Resample {orig_sr} → {target_sr} Hz (librosa)")
        return librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)
    except Exception:
        logger.debug(f"Resample {orig_sr} → {target_sr} Hz (numpy interp)")
        n_samples = int(len(audio) * target_sr / orig_sr)
        indices = np.linspace(0, len(audio) - 1, n_samples)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.int16)