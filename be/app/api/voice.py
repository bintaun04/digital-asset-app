from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request,Query,status
from pydantic import BaseModel
from typing import Optional
import numpy as np

from ..services.voice_service import VoiceService
from ..services.biometric_service import BiometricService
from ..repository.user_repo import UserRepository 
router = APIRouter()

# Global services
voice_service: VoiceService = None
biometric_service: BiometricService = None

def init_voice_services(config: dict):
    global voice_service, biometric_service
    voice_service = VoiceService(config)
    biometric_service = BiometricService(voice_service)  # ← Inject STT service
    print("✅ Services ready!")

# ========================= Schemas =========================

class HealthResponse(BaseModel):
    status: str
    message: str


class EnrollResponse(BaseModel):
    user_id: str
    status: str
    message: str
    transcribed_text: str = ""


class VerifyResponse(BaseModel):
    user_id: str
    is_verified: bool
    similarity_score: float
    message: str


class EnrollStatusResponse(BaseModel):
    user_id: int
    enrolled: bool
    embedding_size: int


class TestResponse(BaseModel):
    user_id: str
    is_verified: bool
    similarity_score: float
    text: str


class CommandResponse(BaseModel):
    status: str
    user_text: str
    ai_response: str
    score: Optional[float] = None
    message: Optional[str] = None


# ========================= Helpers =========================

def _parse_user_id(raw: Optional[str], field: str = "user_id") -> int:
    """
    Parse và validate user_id từ form data.
    Raises HTTPException 400 nếu thiếu hoặc không hợp lệ.
    """
    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Thiếu trường '{field}' trong form data",
        )
    try:
        uid = int(raw)
        if uid <= 0:
            raise ValueError("user_id phải là số nguyên dương")
        return uid
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{field}' không hợp lệ: {str(e)}",
        )


def _check_services(*services_with_names: tuple) -> None:
    """
    Kiểm tra các service đã được khởi tạo chưa.
    Nhận list of (service, name) tuples.
    """
    for service, name in services_with_names:
        if service is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"{name} chưa được khởi tạo",
            )


def _validate_audio(audio_bytes: bytes, min_size: int = 1024) -> None:
    """Validate audio bytes - tái sử dụng ở nhiều endpoint"""
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File audio rỗng",
        )
    if len(audio_bytes) < min_size:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File audio quá ngắn (tối thiểu {min_size} bytes)",
        )


# ========================= Endpoints =========================

@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        message="Voice Biometric API (MFCC + DFT) is running",
    )


@router.post("/enroll", response_model=EnrollResponse, status_code=201)
async def enroll_voice(
    user_id: str = Form(...),
    file: UploadFile = File(...),
):
    _check_services((biometric_service, "BiometricService"))

    uid = _parse_user_id(user_id)

    if not file.filename:
        raise HTTPException(400, "File không hợp lệ")

    audio_bytes = await file.read()
    _validate_audio(audio_bytes)

    # Gọi enroll và nhận thêm transcribed_text
    success, transcribed_text = await biometric_service.enroll_voice_with_stt(str(uid), audio_bytes)

    if success:
        return EnrollResponse(
            user_id=str(uid),
            status="success",
            message="Đăng ký giọng nói thành công (Auto STT)",
            transcribed_text=transcribed_text
        )
    raise HTTPException(500, "Không thể đăng ký giọng nói")
@router.post("/verify", response_model=VerifyResponse)
async def verify_voice(
    user_id: str = Form(...),
    file: UploadFile = File(...),
):
    _check_services((voice_service, "VoiceService"), (biometric_service, "BiometricService"))
    uid = _parse_user_id(user_id)
    
    audio_bytes = await file.read()
    _validate_audio(audio_bytes)
    
    # 1. STT
    transcribed = await voice_service.transcribe(audio_bytes)
    
    # 2. Two-Factor verify
    is_match, score, reason = await biometric_service.verify_voice(
        str(uid), audio_bytes, transcribed
    )
    
    return VerifyResponse(
        user_id=str(uid),
        is_verified=is_match,
        similarity_score=score,
        transcribed_text=transcribed,
        message=reason or "Thành công" if is_match else f"Thất bại: {reason}",
    )
@router.post("/command", response_model=CommandResponse)
async def voice_command(
    file: UploadFile = File(..., description="File audio (wav/flac/ogg/mp3)"),
    user_id: str = Form(..., description="User ID (số nguyên dương)"),
) -> CommandResponse:
    """
    Xử lý lệnh giọng nói.
    Endpoint này chỉ chạy STT - KHÔNG tự verify lại.
    Caller phải đã verify trước khi gọi endpoint này.
    """
    # ← check cả 2 service vì logic bên trong cần cả 2
    _check_services(
        (voice_service, "VoiceService"),
        (biometric_service, "BiometricService"),
    )

    uid = _parse_user_id(user_id)

    audio_bytes = await file.read()
    _validate_audio(audio_bytes)

    # Chỉ chạy STT, không verify lại
    result = await voice_service.process_command_only(audio_bytes, uid)
    return result


@router.post("/test", response_model=TestResponse)
async def test_voice(
    user_id: str = Form(...),
    file: UploadFile = File(...),
) -> TestResponse:
    """Test kết hợp: Verify + STT (verify chỉ chạy đúng 1 lần)"""
    _check_services(
        (biometric_service, "BiometricService"),
        (voice_service, "VoiceService"),
    )

    uid = _parse_user_id(user_id)

    audio_bytes = await file.read()
    _validate_audio(audio_bytes)

    # Bước 1: Verify (1 lần duy nhất)
    is_match, score = await biometric_service.verify_voice(str(uid), audio_bytes)

    # Bước 2: STT chỉ khi verify thành công
    text = ""
    if is_match:
        # ← process_command_only: chỉ STT, KHÔNG verify lại
        result = await voice_service.process_command_only(audio_bytes, uid)
        text = result.get("user_text", "")

    return TestResponse(
        user_id=str(uid),
        is_verified=is_match,
        similarity_score=float(score),
        text=text,
    )


@router.delete("/delete")
async def delete_voice(
    user_id: str = Form(..., description="User ID (số nguyên dương)"),
):
    """Xóa giọng nói"""
    _check_services((biometric_service, "BiometricService"))

    uid = _parse_user_id(user_id)
    success = await biometric_service.delete_voice(str(uid))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy giọng nói của user {uid}",
        )

    return {"status": "success", "message": f"Đã xóa giọng nói của user {uid}"}


@router.get("/enroll/status", response_model=EnrollStatusResponse)
async def enroll_status(
    user_id: int = Query(..., gt=0, description="User ID"),  # ← Query đúng cho GET
) -> EnrollStatusResponse:
    """Kiểm tra trạng thái đăng ký giọng nói"""
    _check_services((biometric_service, "BiometricService"))

    user = await UserRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User không tồn tại",
        )

    return EnrollStatusResponse(
        user_id=user_id,
        enrolled=bool(user.voice_embedding),
        embedding_size=len(user.voice_embedding) if user.voice_embedding else 0,
    )