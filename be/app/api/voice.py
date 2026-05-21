# backend/app/api/voice.py
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, status
from pydantic import BaseModel
from typing import Optional

from app.services.challenge_service import ChallengeService
from app.services.audio_service import AudioService
from app.services.voice_service import VoiceService
from app.services.biometric_service import BiometricService
from app.repository.user_repo import UserRepository
from app.repository.insight_repo import InsightRepository
logger = logging.getLogger("VoiceAPI")

router = APIRouter()

# Global services
voice_service:     VoiceService     = None
biometric_service: BiometricService = None
audio_service = AudioService()


def init_voice_services(config: dict):
    global voice_service, biometric_service
    voice_service     = VoiceService(config)
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

class VoiceInsight(BaseModel):
    """Chi tiết so sánh giọng nói gốc vs giọng vừa nói."""
    cosine_score:      float
    mfcc_score:        Optional[float] = None
    ge2e_score:        Optional[float] = None
    text_similarity:   float
    threshold:         float
    gap_to_threshold:  float
    embedding_dim:     int
    mode:              str           # "MFCC+GE2E" | "MFCC-only"
    confidence:        str           # "high" | "medium" | "low" | "very_low"

class VerifyResponse(BaseModel):
    user_id: str
    is_verified: bool
    similarity_score: float
    transcribed_text: str = ""
    message: str
    insight: Optional[VoiceInsight] = None

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
    insight: Optional[VoiceInsight] = None

class CommandResponse(BaseModel):
    status: str
    user_text: str
    ai_response: str
    score: Optional[float] = None
    message: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_user_id(raw: Optional[str], field: str = "user_id") -> int:
    if raw is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Thiếu trường '{field}'")
    try:
        uid = int(raw)
        if uid <= 0:
            raise ValueError("phải là số nguyên dương")
        return uid
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{field}' không hợp lệ: {e}")

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
    lang = lang.lower().strip()
    if lang not in ["vi", "en"]:
        raise HTTPException(400, "Language phải là 'vi' hoặc 'en'")
    return lang


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        message="Multi-language Voice Biometric API (VI/EN) is running",
    )


@router.post("/enroll", response_model=EnrollResponse, status_code=201)
async def enroll_voice(
    user_id:  str = Form(...),
    file:     UploadFile = File(...),
    language: str = Form(default="vi"),
):
    """Đăng ký giọng nói. Chỉ lưu embedding vector, không lưu file audio."""
    _check_services((biometric_service, "BiometricService"))
    uid  = _parse_user_id(user_id)
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
    user_id:  str = Form(...),
    file:     UploadFile = File(...),
    language: str = Form(default="vi"),
):
    """
    Xác thực giọng nói và trả về insight chi tiết so sánh
    giữa giọng gốc (enroll) và giọng vừa nói.
    """
    _check_services(
        (voice_service,     "VoiceService"),
        (biometric_service, "BiometricService"),
    )
    uid  = _parse_user_id(user_id)
    lang = _validate_language(language)

    audio_bytes = await file.read()
    _validate_audio(audio_bytes)

    # STT
    transcribed = await voice_service.transcribe(audio_bytes, language=lang)

    # Verify + insight
    is_match, score, reason, insight_raw = \
        await biometric_service.verify_voice_with_insight(
            str(uid), audio_bytes, transcribed
        )

    insight = VoiceInsight(
        cosine_score     = insight_raw["cosine_score"],
        mfcc_score       = insight_raw.get("mfcc_score"),
        ge2e_score       = insight_raw.get("ge2e_score"),
        text_similarity  = insight_raw["text_similarity"],
        threshold        = insight_raw["threshold"],
        gap_to_threshold = insight_raw["gap_to_threshold"],
        embedding_dim    = insight_raw["embedding_dim"],
        mode             = insight_raw["mode"],
        confidence       = insight_raw["confidence"],
    )

    return VerifyResponse(
        user_id          = str(uid),
        is_verified      = is_match,
        similarity_score = score,
        transcribed_text = transcribed,
        message          = "Thành công" if is_match else f"Thất bại: {reason}",
        insight          = insight,
    )


@router.post("/command", response_model=CommandResponse)
async def voice_command(
    file:     UploadFile = File(...),
    user_id:  str = Form(...),
    language: str = Form(default="vi"),
):
    """Xử lý lệnh giọng nói (sau khi đã verify)."""
    _check_services(
        (voice_service,     "VoiceService"),
        (biometric_service, "BiometricService"),
    )
    uid  = _parse_user_id(user_id)
    lang = _validate_language(language)

    audio_bytes = await file.read()
    _validate_audio(audio_bytes)

    result = await voice_service.process_command_only(audio_bytes, uid, language=lang)
    return result


@router.post("/test", response_model=TestResponse)
async def test_voice(
    user_id:  str = Form(...),
    file:     UploadFile = File(...),
    language: str = Form(default="vi"),
):
    """Test: STT → Verify → trả insight nếu pass."""
    _check_services(
        (voice_service,     "VoiceService"),
        (biometric_service, "BiometricService"),
    )
    uid  = _parse_user_id(user_id)
    lang = _validate_language(language)

    audio_bytes = await file.read()
    _validate_audio(audio_bytes)

    transcribed = await voice_service.transcribe(audio_bytes, language=lang)

    is_match, score, reason, insight_raw = \
        await biometric_service.verify_voice_with_insight(
            str(uid), audio_bytes, transcribed
        )

    insight = VoiceInsight(**{
        "cosine_score":     insight_raw["cosine_score"],
        "mfcc_score":       insight_raw.get("mfcc_score"),
        "ge2e_score":       insight_raw.get("ge2e_score"),
        "text_similarity":  insight_raw["text_similarity"],
        "threshold":        insight_raw["threshold"],
        "gap_to_threshold": insight_raw["gap_to_threshold"],
        "embedding_dim":    insight_raw["embedding_dim"],
        "mode":             insight_raw["mode"],
        "confidence":       insight_raw["confidence"],
    }) if is_match else None

    return TestResponse(
        user_id          = str(uid),
        is_verified      = is_match,
        similarity_score = float(score),
        text             = transcribed if is_match else "",
        insight          = insight,
    )


@router.delete("/delete")
async def delete_voice(user_id: str = Form(...)):
    """Xóa embedding giọng nói đã đăng ký."""
    _check_services((biometric_service, "BiometricService"))
    uid = _parse_user_id(user_id)

    success = await biometric_service.delete_voice(str(uid))
    if not success:
        raise HTTPException(404, f"Không tìm thấy giọng nói của user {uid}")

    return {"status": "success", "message": f"Đã xóa giọng nói của user {uid}"}


@router.get("/enroll/status", response_model=EnrollStatusResponse)
async def enroll_status(user_id: int = Query(..., gt=0)):
    """Kiểm tra trạng thái đăng ký giọng nói."""
    _check_services((biometric_service, "BiometricService"))

    user = UserRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(404, "User không tồn tại")

    return EnrollStatusResponse(
        user_id        = user_id,
        enrolled       = bool(user.voice_embedding),
        embedding_size = len(user.voice_embedding) if user.voice_embedding else 0,
        language       = getattr(user, "voice_language", None),
    )


@router.get("/challenge")
async def get_challenge(user_id: int):
    """Lấy challenge ngẫu nhiên."""
    return ChallengeService.generate_challenge(user_id)


@router.post("/verify-challenge")
async def verify_challenge(
    user_id:      int = Form(...),
    challenge_id: str = Form(...),
    language:     str = Form("vi"),
    file:         UploadFile = File(...),
):
    """Xác thực với Challenge (anti-replay)."""
    _check_services((biometric_service, "BiometricService"))

    audio_bytes = await file.read()
    if len(audio_bytes) < 1024:
        raise HTTPException(400, "Audio quá ngắn")

    success, score, message = await biometric_service.verify_with_challenge(
        user_id=user_id,
        audio_bytes=audio_bytes,
        challenge_id=challenge_id,
        language=language,
    )

    return {
        "success":      success,
        "score":        score,
        "message":      message,
        "challenge_id": challenge_id,
    }

@router.get("/insights")
async def get_voice_insights(
    user_id: int = Query(..., gt=0),
    action_type: str = Query(None, description="enroll | verify | challenge"),
    limit: int = Query(20, ge=1, le=100),
):
    """Lấy lịch sử insight xác thực giọng nói của user."""
    rows = InsightRepository.get_by_user(user_id, action_type, limit)
    return {"user_id": user_id, "insights": rows, "count": len(rows)}
 
 
@router.get("/insights/stats")
async def get_voice_insight_stats(user_id: int = Query(..., gt=0)):
    """Thống kê tổng hợp: tỉ lệ thành công, điểm trung bình..."""
    stats = InsightRepository.get_stats(user_id)
    return {"user_id": user_id, "stats": stats}
 