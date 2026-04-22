# backend/app/api/voice.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
import numpy as np

from ..services.voice_service import VoiceService
from ..services.biometric_service import BiometricService

router = APIRouter()

# Global services
voice_service: VoiceService = None
biometric_service: BiometricService = None

def init_voice_services(config: dict):
    """Khởi tạo services - được gọi từ main.py"""
    global voice_service, biometric_service
    voice_service = VoiceService(config)
    biometric_service = BiometricService()
    print("✅ VoiceService & BiometricService (MFCC+DFT) đã khởi tạo thành công!")

# ========================= Schemas =========================
class HealthResponse(BaseModel):
    status: str
    message: str

class EnrollResponse(BaseModel):
    user_id: str
    status: str
    message: str

class VerifyResponse(BaseModel):
    user_id: str
    is_verified: bool
    similarity_score: float
    message: str

class TranscribeResponse(BaseModel):
    text: str

class TestResponse(BaseModel):
    user_id: str
    is_verified: bool
    similarity_score: float
    text: str

# ========================= Endpoints =========================

@router.get("/health", response_model=HealthResponse)
async def health():
    return {
        "status": "healthy",
        "message": "Voice Biometric API (MFCC + DFT) is running"
    }

@router.post("/enroll", response_model=EnrollResponse)
async def enroll_voice(
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Đăng ký giọng nói (MFCC + DFT)"""
    if not biometric_service:
        raise HTTPException(500, "Biometric service chưa khởi tạo")

    audio_bytes = await file.read()
    success = await biometric_service.enroll_voice(user_id, audio_bytes)

    if success:
        return EnrollResponse(
            user_id=user_id,
            status="success",
            message="Đăng ký giọng nói thành công (MFCC + DFT)"
        )
    raise HTTPException(500, "Không thể đăng ký giọng nói")

@router.post("/verify", response_model=VerifyResponse)
async def verify_voice(
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Xác thực giọng nói"""
    if not biometric_service:
        raise HTTPException(500, "Biometric service chưa khởi tạo")

    audio_bytes = await file.read()
    is_match, score = await biometric_service.verify_voice(user_id, audio_bytes)

    return VerifyResponse(
        user_id=user_id,
        is_verified=is_match,
        similarity_score=score,
        message="Xác thực thành công" if is_match else "Xác thực thất bại"
    )

@router.post("/command")
async def voice_command(
    file: UploadFile = File(...),
    user_id: str = Form("1")
):
    """Xử lý lệnh giọng nói - Chỉ chạy sau khi verify thành công"""
    if not voice_service:
        raise HTTPException(500, "Voice service chưa khởi tạo")

    audio_bytes = await file.read()
    result = await voice_service.process_full_command(audio_bytes, int(user_id))
    return result

@router.post("/test", response_model=TestResponse)
async def test_voice(
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Test kết hợp: Verify + STT"""
    if not biometric_service or not voice_service:
        raise HTTPException(500, "Service chưa khởi tạo")

    audio_bytes = await file.read()

    # Bước 1: Verify
    is_match, score = await biometric_service.verify_voice(user_id, audio_bytes)

    # Bước 2: Nếu thành công thì chạy STT
    text = ""
    if is_match:
        result = await voice_service.process_full_command(audio_bytes, int(user_id))
        text = result.get("user_text", "")

    return TestResponse(
        user_id=user_id,
        is_verified=is_match,
        similarity_score=score,
        text=text
    )

@router.delete("/delete")
async def delete_voice(user_id: str = Form(...)):
    """Xóa giọng nói"""
    if not biometric_service:
        raise HTTPException(500, "Biometric service chưa khởi tạo")
    
    success = await biometric_service.delete_voice(user_id)
    if success:
        return {"status": "success", "message": f"Đã xóa giọng nói của user {user_id}"}
    raise HTTPException(404, "Không tìm thấy giọng nói")