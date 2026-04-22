# backend/app/api/auth.py
"""
Luồng:
  1. POST /auth/register        – JSON  → tạo tài khoản
  2. POST /voice/enroll         – form-data + file → lưu giọng nói
  3. POST /auth/login           – form-data + file audio → password + voice
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


# ── 1. REGISTER (JSON) ────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    svc = AuthService(db)
    if svc.get_user_by_email(body.email):
        raise HTTPException(400, "Email đã được đăng ký")
    if len(body.password) < 6:
        raise HTTPException(400, "Mật khẩu phải có ít nhất 6 ký tự")

    user = svc.create_user(email=body.email, password=body.password,
                           full_name=body.full_name)
    return AuthResponse(user=_build_user_response(user),
                        access_token=svc.create_token(user))


# ── 2. LOGIN CHỈ PASSWORD – form-data (dùng trước khi enroll voice) ──────────

@router.post("/login-no-voice", response_model=AuthResponse)
async def login_no_voice(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """FE gửi: data={'email':..., 'password':...}  (KHÔNG phải json=)"""
    user = AuthService(db).authenticate(email, password)
    if not user:
        raise HTTPException(401, "Email hoặc mật khẩu không đúng")
    svc = AuthService(db)
    return AuthResponse(user=_build_user_response(user),
                        access_token=svc.create_token(user))


# ── 3. LOGIN ĐẦY ĐỦ – form-data + file audio ─────────────────────────────────

@router.post("/login", response_model=AuthResponse)
async def login(
    email: str = Form(...),
    password: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """
    FE gửi multipart/form-data:
      data={'email':..., 'password':...}
      files={'file': <audio.wav>}   (bắt buộc nếu user đã enroll)
    """
    svc = AuthService(db)
    user = svc.authenticate(email, password)
    if not user:
        raise HTTPException(401, "Email hoặc mật khẩu không đúng")

    # Nếu đã enroll voice → bắt buộc verify
    if user.voice_embedding is not None:
        if file is None:
            raise HTTPException(
                400,
                "Tài khoản này yêu cầu xác thực giọng nói. Vui lòng ghi âm trước khi đăng nhập."
            )
        audio_bytes = await file.read()
        try:
            is_match, score = await BiometricService().verify_voice(user.id, audio_bytes)
        except Exception as e:
            logger.error(f"Lỗi verify voice login: {e}")
            raise HTTPException(500, "Lỗi xử lý giọng nói")

        if not is_match:
            raise HTTPException(401, f"Giọng nói không khớp (score={score:.4f}). Vui lòng thử lại.")

        logger.info(f"✅ Voice OK – {user.email} score={score:.4f}")

    return AuthResponse(user=_build_user_response(user),
                        access_token=svc.create_token(user))


# ── 4. ME ─────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return _build_user_response(current_user)


# ── 5. LOGOUT ────────────────────────────────────────────────────────────────

@router.post("/logout", response_model=MessageResponse)
async def logout(current_user=Depends(get_current_user)):
    return MessageResponse(message=f"Đã đăng xuất {current_user.email}")


# ── 6. ĐỔI MẬT KHẨU ─────────────────────────────────────────────────────────

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