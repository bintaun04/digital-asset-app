from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, status
from pydantic import BaseModel
from typing import Optional

from app.services.voice_service import VoiceService
from app.services.biometric_service import BiometricService
from app.repository.user_repo import UserRepository

router = APIRouter()

# Global services
voice_service: VoiceService = None
biometric_service: BiometricService = None


def init_voice_services(config: dict):
    global voice_service, biometric_service
    voice_service = VoiceService(config)
    biometric_service = BiometricService(voice_service)
    print("✅ Multi-language Voice Services ready!")


# ── Schemas ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    message: str

class EnrollResponse(BaseModel):
    user_id: str
    status: str
    message: str
    transcribed_text: str = ""
    language: str = ""

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
    language: Optional[str] = None

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


def _validate_language(lang: str) -> str:
    """Validate và chuẩn hóa language code"""
    lang = lang.lower().strip()
    if lang not in ["vi", "en"]:
        raise HTTPException(400, "Language phải là 'vi' hoặc 'en'")
    return lang


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        message="Multi-language Voice Biometric API (VI/EN) is running"
    )


@router.post("/enroll", response_model=EnrollResponse, status_code=201)
async def enroll_voice(
    user_id: str = Form(...),
    file: UploadFile = File(...),
    language: str = Form(default="vi"),  # Mặc định tiếng Việt
):
    """
    Đăng ký giọng nói với hỗ trợ đa ngôn ngữ
    
    Args:
        user_id: ID người dùng
        file: File audio
        language: Ngôn ngữ ('vi' hoặc 'en')
    """
    _check_services((biometric_service, "BiometricService"))
    uid = _parse_user_id(user_id)
    lang = _validate_language(language)

    if not file.filename:
        raise HTTPException(400, "File không hợp lệ")

    audio_bytes = await file.read()
    _validate_audio(audio_bytes)

    success, transcribed_text = await biometric_service.enroll_voice_with_stt(
        str(uid), audio_bytes, language=lang
    )

    if not success:
        raise HTTPException(500, "Không thể đăng ký giọng nói")

    lang_name = "Tiếng Việt" if lang == "vi" else "English"
    
    return EnrollResponse(
        user_id=str(uid),
        status="success",
        message=f"Đăng ký giọng nói thành công ({lang_name})",
        transcribed_text=transcribed_text,
        language=lang,
    )


@router.post("/verify", response_model=VerifyResponse)
async def verify_voice(
    user_id: str = Form(...),
    file: UploadFile = File(...),
    language: str = Form(default="vi"),
):
    """
    Xác thực giọng nói với ngôn ngữ được chỉ định
    
    Args:
        user_id: ID người dùng
        file: File audio
        language: Ngôn ngữ ('vi' hoặc 'en')
    """
    _check_services(
        (voice_service, "VoiceService"),
        (biometric_service, "BiometricService"),
    )
    uid = _parse_user_id(user_id)
    lang = _validate_language(language)

    audio_bytes = await file.read()
    _validate_audio(audio_bytes)

    # 1. STT với ngôn ngữ chỉ định
    transcribed = await voice_service.transcribe(audio_bytes, language=lang)

    # 2. Two-factor verify
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
    language: str = Form(default="vi"),
):
    """
    Xử lý lệnh giọng nói (sau khi đã verify)
    
    Args:
        file: File audio
        user_id: ID người dùng
        language: Ngôn ngữ ('vi' hoặc 'en')
    """
    _check_services(
        (voice_service, "VoiceService"),
        (biometric_service, "BiometricService"),
    )
    uid = _parse_user_id(user_id)
    lang = _validate_language(language)

    audio_bytes = await file.read()
    _validate_audio(audio_bytes)

    result = await voice_service.process_command_only(
        audio_bytes, uid, language=lang
    )
    return result


@router.post("/test", response_model=TestResponse)
async def test_voice(
    user_id: str = Form(...),
    file: UploadFile = File(...),
    language: str = Form(default="vi"),
):
    """
    Test: Verify → STT nếu pass
    
    Args:
        user_id: ID người dùng
        file: File audio
        language: Ngôn ngữ ('vi' hoặc 'en')
    """
    _check_services(
        (voice_service, "VoiceService"),
        (biometric_service, "BiometricService"),
    )
    uid = _parse_user_id(user_id)
    lang = _validate_language(language)

    audio_bytes = await file.read()
    _validate_audio(audio_bytes)

    # 1. STT
    transcribed = await voice_service.transcribe(audio_bytes, language=lang)

    # 2. Verify
    is_match, score, reason = await biometric_service.verify_voice(
        str(uid), audio_bytes, transcribed
    )

    # 3. Trả text nếu pass
    text = transcribed if is_match else ""

    return TestResponse(
        user_id=str(uid),
        is_verified=is_match,
        similarity_score=float(score),
        text=text,
    )


@router.delete("/delete")
async def delete_voice(user_id: str = Form(...)):
    """Xóa giọng nói đã đăng ký"""
    _check_services((biometric_service, "BiometricService"))
    uid = _parse_user_id(user_id)

    success = await biometric_service.delete_voice(str(uid))
    if not success:
        raise HTTPException(404, f"Không tìm thấy giọng nói của user {uid}")

    return {"status": "success", "message": f"Đã xóa giọng nói của user {uid}"}


@router.get("/enroll/status", response_model=EnrollStatusResponse)
async def enroll_status(user_id: int = Query(..., gt=0)):
    """Kiểm tra trạng thái đăng ký giọng nói"""
    _check_services((biometric_service, "BiometricService"))

    user = UserRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(404, "User không tồn tại")

    return EnrollStatusResponse(
        user_id=user_id,
        enrolled=bool(user.voice_embedding),
        embedding_size=len(user.voice_embedding) if user.voice_embedding else 0,
        language=getattr(user, 'voice_language', None),  # Nếu DB có lưu
    )