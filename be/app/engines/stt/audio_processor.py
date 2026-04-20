# backend/app/engines/stt/audio_processor.py
import io
import numpy as np
import soundfile as sf
import subprocess
import tempfile
import os

SAMPLE_RATE = 16000

def convert_to_wav(audio_bytes: bytes, filename: str = "") -> np.ndarray:
    """
    Chuyển audio bytes sang numpy array 16kHz mono float32
    """
    ext = os.path.splitext(filename)[-1].lower() if filename else ""

    # Thử đọc trực tiếp nếu là WAV
    if ext == ".wav":
        try:
            audio, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
            if audio.ndim > 1:
                audio = audio.mean(axis=1)  # stereo → mono
            if sr != SAMPLE_RATE:
                audio = _resample(audio, sr, SAMPLE_RATE)
            return audio
        except Exception:
            pass  # fallback sang ffmpeg

    # Dùng ffmpeg để chuyển tất cả định dạng
    return _convert_via_ffmpeg(audio_bytes)


def _convert_via_ffmpeg(audio_bytes: bytes) -> np.ndarray:
    """Dùng ffmpeg decode audio"""
    with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", tmp_path,
            "-ar", str(SAMPLE_RATE),
            "-ac", "1",           # mono
            "-f", "f32le",
            "-"
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=60)

        if result.returncode != 0:
            error = result.stderr.decode(errors="ignore")
            raise RuntimeError(f"ffmpeg error: {error}")

        return np.frombuffer(result.stdout, dtype=np.float32)

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Resample audio"""
    if orig_sr == target_sr:
        return audio
    ratio = target_sr / orig_sr
    n_samples = int(len(audio) * ratio)
    indices = np.linspace(0, len(audio) - 1, n_samples)
    return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)