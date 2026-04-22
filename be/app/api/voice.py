from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
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


# ========================= Helpers =========================

def _parse_user_id(raw: Optional[str], field: str = "user_id") -> int:
    """
    Parse và validate user_id từ form data.
    Raises HTTPException 400 nếu thiếu hoặc không hợp lệ.
    """
    if raw is None:
        raise HTTPException(
            status_code=400,
            detail=f"Thiếu trường '{field}' trong form data"
        )
    try:
        uid = int(raw)
        if uid <= 0:
            raise ValueError("user_id phải là số nguyên dương")
        return uid
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"'{field}' không hợp lệ: {str(e)}"
        )


def _check_services(*services_with_names):
    """
    Kiểm tra các service đã được khởi tạo chưa.
    Nhận list of (service, name) tuples.
    """
    for service, name in services_with_names:
        if service is None:
            raise HTTPException(
                status_code=500,
                detail=f"{name} chưa được khởi tạo"
            )


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
    _check_services((biometric_service, "BiometricService"))

    # Validate user_id
    uid = _parse_user_id(user_id)

    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="File không hợp lệ")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="File audio rỗng")

    success = await biometric_service.enroll_voice(str(uid), audio_bytes)

    if success:
        return EnrollResponse(
            user_id=str(uid),
            status="success",
            message="Đăng ký giọng nói thành công (MFCC + DFT)"
        )
    raise HTTPException(
        status_code=500,
        detail="Không thể đăng ký giọng nói"
    )


@router.post("/verify", response_model=VerifyResponse)
async def verify_voice(
    user_id: int = Form(..., gt=0, description="User ID (số nguyên dương)"),
    file: UploadFile = File(..., description="File audio (wav/flac/ogg/mp3)")
):
    _check_services((biometric_service, "BiometricService"))

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu file audio")

    audio_bytes = await file.read()
    if not audio_bytes or len(audio_bytes) < 1024:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File audio quá ngắn hoặc rỗng")

    try:
        is_match, score = await biometric_service.verify_voice(str(user_id), audio_bytes)
    except HTTPException as he:
        raise he
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Lỗi xử lý: {str(e)}")

    return VerifyResponse(
        user_id=str(user_id),
        is_verified=is_match,
        similarity_score=float(score),
        message="Xác thực thành công" if is_match else "Xác thực thất bại"
    )

@router.post("/command")
async def voice_command(
    file: UploadFile = File(...),
    user_id: str = Form("1")
):
    """Xử lý lệnh giọng nói - Chỉ chạy sau khi verify thành công"""
    _check_services((voice_service, "VoiceService"))

    uid = _parse_user_id(user_id)

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="File audio rỗng")

    result = await voice_service.process_full_command(audio_bytes, uid)
    return result


@router.post("/test", response_model=TestResponse)
async def test_voice(
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Test kết hợp: Verify + STT"""
    _check_services(
        (biometric_service, "BiometricService"),
        (voice_service, "VoiceService")
    )

    uid = _parse_user_id(user_id)

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="File audio rỗng")

    # Bước 1: Verify
    is_match, score = await biometric_service.verify_voice(str(uid), audio_bytes)

    # Bước 2: Nếu thành công thì chạy STT
    text = ""
    if is_match:
        result = await voice_service.process_full_command(audio_bytes, uid)
        text = result.get("user_text", "")

    return TestResponse(
        user_id=str(uid),
        is_verified=is_match,
        similarity_score=float(score),
        text=text
    )


@router.delete("/delete")
async def delete_voice(user_id: str = Form(...)):
    """Xóa giọng nói"""
    _check_services((biometric_service, "BiometricService"))

    uid = _parse_user_id(user_id)
    success = await biometric_service.delete_voice(str(uid))

    if success:
        return {
            "status": "success",
            "message": f"Đã xóa giọng nói của user {uid}"
        }
    raise HTTPException(
        status_code=404,
        detail=f"Không tìm thấy giọng nói của user {uid}"
    )
@router.get("/enroll/status")
async def enroll_status(user_id: int = Form(..., gt=0)):
    user = await UserRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User không tồn tại")
    return {
        "user_id": user_id,
        "enrolled": bool(user.voice_embedding),
        "embedding_size": len(user.voice_embedding) if user.voice_embedding else 0
    }