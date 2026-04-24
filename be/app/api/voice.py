# backend/app/api/voice.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, status
from pydantic import BaseModel
from typing import Optional

from ..services.voice_service import VoiceService
from ..services.biometric_service import BiometricService
from ..repository.user_repo import UserRepository

router = APIRouter()

# Global services – khởi tạo từ main.py qua init_voice_services()
voice_service: VoiceService = None
biometric_service: BiometricService = None


def init_voice_services(config: dict):
    global voice_service, biometric_service
    voice_service     = VoiceService(config)
    biometric_service = BiometricService(voice_service)   # ← inject STT
    print("✅ Services ready!")


# ── Schemas ───────────────────────────────────────────────────────────────────

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
    transcribed_text: str = ""
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_user_id(raw: Optional[str], field: str = "user_id") -> int:
    if raw is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"Thiếu trường '{field}'")
    try:
        uid = int(raw)
        if uid <= 0:
            raise ValueError("phải là số nguyên dương")
        return uid
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"'{field}' không hợp lệ: {e}")


def _check_services(*pairs):
    for svc, name in pairs:
        if svc is None:
            raise HTTPException(500, f"{name} chưa được khởi tạo")


def _validate_audio(audio_bytes: bytes, min_size: int = 1024):
    if not audio_bytes:
        raise HTTPException(400, "File audio rỗng")
    if len(audio_bytes) < min_size:
        raise HTTPException(422, f"File audio quá ngắn (tối thiểu {min_size} bytes)")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="healthy",
                          message="Voice Biometric API (MFCC + DFT) is running")


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

    success, transcribed_text = await biometric_service.enroll_voice_with_stt(
        str(uid), audio_bytes
    )

    if not success:
        raise HTTPException(500, "Không thể đăng ký giọng nói")

    return EnrollResponse(
        user_id=str(uid),
        status="success",
        message="Đăng ký giọng nói thành công (Auto STT)",
        transcribed_text=transcribed_text,
    )


@router.post("/verify", response_model=VerifyResponse)
async def verify_voice(
    user_id: str = Form(...),
    file: UploadFile = File(...),
):
    _check_services(
        (voice_service,     "VoiceService"),
        (biometric_service, "BiometricService"),
    )
    uid = _parse_user_id(user_id)

    audio_bytes = await file.read()
    _validate_audio(audio_bytes)

    # 1. STT
    transcribed = await voice_service.transcribe(audio_bytes)

    # 2. Two-factor verify: text + embedding
    is_match, score, reason = await biometric_service.verify_voice(
        str(uid), audio_bytes, transcribed
    )

    return VerifyResponse(
        user_id=str(uid),
        is_verified=is_match,
        similarity_score=score,
        transcribed_text=transcribed,
        message="Thành công" if is_match else f"Thất bại: {reason}",
    )


@router.post("/command", response_model=CommandResponse)
async def voice_command(
    file: UploadFile = File(...),
    user_id: str = Form(...),
):
    """Chỉ chạy STT lệnh — KHÔNG verify lại (caller đã verify trước)."""
    _check_services(
        (voice_service,     "VoiceService"),
        (biometric_service, "BiometricService"),
    )
    uid = _parse_user_id(user_id)

    audio_bytes = await file.read()
    _validate_audio(audio_bytes)

    result = await voice_service.process_command_only(audio_bytes, uid)
    return result


@router.post("/test", response_model=TestResponse)
async def test_voice(
    user_id: str = Form(...),
    file: UploadFile = File(...),
):
    """Test: Verify (1 lần) → STT nếu pass."""
    _check_services(
        (voice_service,     "VoiceService"),
        (biometric_service, "BiometricService"),
    )
    uid = _parse_user_id(user_id)

    audio_bytes = await file.read()
    _validate_audio(audio_bytes)

    # 1. STT trước (dùng chung cho cả verify lẫn command)
    transcribed = await voice_service.transcribe(audio_bytes)

    # 2. Verify 1 lần duy nhất, truyền đủ 3 args
    is_match, score, reason = await biometric_service.verify_voice(
        str(uid), audio_bytes, transcribed
    )

    # 3. Nếu pass thì dùng lại transcribed, không chạy STT lần 2
    text = transcribed if is_match else ""

    return TestResponse(
        user_id=str(uid),
        is_verified=is_match,
        similarity_score=float(score),
        text=text,
    )


@router.delete("/delete")
async def delete_voice(user_id: str = Form(...)):
    _check_services((biometric_service, "BiometricService"))
    uid = _parse_user_id(user_id)

    success = await biometric_service.delete_voice(str(uid))
    if not success:
        raise HTTPException(404, f"Không tìm thấy giọng nói của user {uid}")

    return {"status": "success", "message": f"Đã xóa giọng nói của user {uid}"}


@router.get("/enroll/status", response_model=EnrollStatusResponse)
async def enroll_status(user_id: int = Query(..., gt=0)):
    _check_services((biometric_service, "BiometricService"))

    user = UserRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(404, "User không tồn tại")

    return EnrollStatusResponse(
        user_id=user_id,
        enrolled=bool(user.voice_embedding),
        embedding_size=len(user.voice_embedding) if user.voice_embedding else 0,
    )