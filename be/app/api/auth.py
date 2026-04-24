# backend/app/api/auth.py
"""
Luồng:
  1. POST /auth/register        – JSON  → tạo tài khoản
  2. POST /voice/enroll         – form-data + file → lưu giọng nói
  3. POST /auth/login           – form-data + file audio → password + voice (2 bước)
  4. POST /auth/login-no-voice  – form-data → chỉ password (trước khi enroll)
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..services.auth_service import AuthService
from ..services.biometric_service import BiometricService

# ← Import voice_service toàn cục (được init từ main.py qua voice.py)
from . import voice as voice_router

router = APIRouter()
security = HTTPBearer(auto_error=False)
logger = logging.getLogger("AuthAPI")


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = ""

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = ""
    has_voice: bool = False

    class Config:
        from_attributes = True

class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"

class MessageResponse(BaseModel):
    message: str


# ── Dependency ────────────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập",
                            headers={"WWW-Authenticate": "Bearer"})
    user = AuthService(db).get_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Token không hợp lệ hoặc đã hết hạn",
                            headers={"WWW-Authenticate": "Bearer"})
    return user


def _build_user_response(user) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name or "",
        has_voice=user.voice_embedding is not None,
    )


def _get_biometric_service() -> BiometricService:
    """
    Trả về BiometricService đã inject voice_service toàn cục.
    voice_service được khởi tạo từ init_voice_services() trong main.py.
    """
    vs = voice_router.voice_service
    if vs is None:
        raise HTTPException(
            status_code=500,
            detail="VoiceService chưa được khởi tạo. Kiểm tra init_voice_services()."
        )
    return BiometricService(voice_service=vs)


# ── 1. REGISTER (JSON) ────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    svc = AuthService(db)
    if svc.get_user_by_email(body.email):
        raise HTTPException(400, "Email đã được đăng ký")
    if len(body.password) < 6:
        raise HTTPException(400, "Mật khẩu phải có ít nhất 6 ký tự")

    user = svc.create_user(
        email=body.email,
        password=body.password,
        full_name=body.full_name,
    )
    return AuthResponse(
        user=_build_user_response(user),
        access_token=svc.create_token(user),
    )


# ── 2. LOGIN CHỈ PASSWORD (dùng trước khi enroll voice) ──────────────────────

@router.post("/login-no-voice", response_model=AuthResponse)
async def login_no_voice(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    svc = AuthService(db)
    user = svc.authenticate(email, password)
    if not user:
        raise HTTPException(401, "Email hoặc mật khẩu không đúng")
    return AuthResponse(
        user=_build_user_response(user),
        access_token=svc.create_token(user),
    )


# ── 3. LOGIN ĐẦY ĐỦ: password + voice (2-factor) ─────────────────────────────

@router.post("/login", response_model=AuthResponse)
async def login(
    email: str = Form(...),
    password: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """
    Luồng xác thực 2 bước:
      Bước 1 – Password:   kiểm tra email + password
      Bước 2 – Voice:      STT audio → so sánh text key → so sánh embedding
                           (chỉ bắt buộc nếu user đã enroll)
    """
    svc = AuthService(db)

    # ── Bước 1: Password ──────────────────────────────────────────────────────
    user = svc.authenticate(email, password)
    if not user:
        raise HTTPException(401, "Email hoặc mật khẩu không đúng")

    # ── Bước 2: Voice (chỉ khi đã enroll) ────────────────────────────────────
    if user.voice_embedding is not None:
        if file is None:
            raise HTTPException(
                400,
                "Tài khoản này yêu cầu xác thực giọng nói. "
                "Vui lòng ghi âm và gửi kèm file audio."
            )

        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(400, "File audio rỗng")

        try:
            bio_svc = _get_biometric_service()
            vs      = voice_router.voice_service

            # 2a. STT để lấy text người dùng vừa nói
            transcribed_text = await vs.transcribe(audio_bytes)
            logger.info(f"[Login STT] {email} → '{transcribed_text}'")

            # 2b. Two-factor verify: text match + embedding match
            is_match, score, reason = await bio_svc.verify_voice(
                str(user.id), audio_bytes, transcribed_text
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Lỗi verify voice login: {e}")
            raise HTTPException(500, f"Lỗi xử lý giọng nói: {str(e)}")

        if not is_match:
            logger.warning(f"❌ Voice FAIL – {email} | score={score:.4f} | {reason}")
            raise HTTPException(
                401,
                f"Xác thực giọng nói thất bại: {reason or f'score={score:.4f}'}"
            )

        logger.info(f"✅ Voice OK – {email} | score={score:.4f}")

    return AuthResponse(
        user=_build_user_response(user),
        access_token=svc.create_token(user),
    )


# ── 4. ME ─────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return _build_user_response(current_user)


# ── 5. LOGOUT ─────────────────────────────────────────────────────────────────

@router.post("/logout", response_model=MessageResponse)
async def logout(current_user=Depends(get_current_user)):
    return MessageResponse(message=f"Đã đăng xuất {current_user.email}")


# ── 6. ĐỔI MẬT KHẨU ──────────────────────────────────────────────────────────

@router.put("/change-password", response_model=MessageResponse)
async def change_password(
    old_password: str = Form(...),
    new_password: str = Form(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if len(new_password) < 6:
        raise HTTPException(400, "Mật khẩu mới phải có ít nhất 6 ký tự")
    if not AuthService(db).change_password(current_user, old_password, new_password):
        raise HTTPException(400, "Mật khẩu cũ không đúng")
    return MessageResponse(message="Đổi mật khẩu thành công")