#be/api/auth.py
import logging
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy.orm import Session
 
from ..core.database import get_db
from ..services.auth_service import AuthService
from ..services.biometric_service import BiometricService
from . import voice as voice_router
 
router   = APIRouter()
security = HTTPBearer(auto_error=False)
logger   = logging.getLogger("AuthAPI")
 
 
# ── Schemas ───────────────────────────────────────────────────────────────────
 
class RegisterRequest(BaseModel):
    email:     EmailStr
    password:  str
    full_name: Optional[str] = ""
 
class UserResponse(BaseModel):
    id:            int
    email:         str
    full_name:     Optional[str] = ""
    has_voice:     bool = False
    voice_language: Optional[str] = "vi"
 
    class Config:
        from_attributes = True
 
class AuthResponse(BaseModel):
    user:         UserResponse
    access_token: str
    token_type:   str = "bearer"
 
class MessageResponse(BaseModel):
    message: str
 
 
# ── Helpers ───────────────────────────────────────────────────────────────────
 
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    if not credentials:
        raise HTTPException(401, "Chưa đăng nhập",
                            headers={"WWW-Authenticate": "Bearer"})
    user = AuthService(db).get_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(401, "Token không hợp lệ hoặc đã hết hạn",
                            headers={"WWW-Authenticate": "Bearer"})
    return user
 
 
def _user_resp(user) -> UserResponse:
    return UserResponse(
        id             = user.id,
        email          = user.email,
        full_name      = user.full_name or "",
        has_voice      = user.voice_embedding is not None,
        voice_language = getattr(user, "voice_language", "vi") or "vi",
    )
 
 
def _get_biometric() -> BiometricService:
    vs = voice_router.voice_service
    if vs is None:
        raise HTTPException(500, "VoiceService chưa được khởi tạo")
    return BiometricService(voice_service=vs)
 
 
# ── 1. REGISTER ───────────────────────────────────────────────────────────────
 
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
    logger.info(f"✅ Registered: {body.email}")
    return AuthResponse(user=_user_resp(user), access_token=svc.create_token(user))
 
 
# ── 2. LOGIN BƯỚC 1: chỉ password ────────────────────────────────────────────
 
@router.post("/login-no-voice", response_model=AuthResponse)
async def login_no_voice(
    email:    str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Bước 1 của luồng đăng nhập 2 bước.
    Chỉ xác thực email + password.
    Trả về token tạm để FE dùng gọi /voice/challenge (bước 2).
    """
    svc  = AuthService(db)
    user = svc.authenticate(email, password)
    if not user:
        raise HTTPException(401, "Email hoặc mật khẩu không đúng")
 
    logger.info(f"✅ Login step-1 OK: {email} | has_voice={user.voice_embedding is not None}")
    return AuthResponse(user=_user_resp(user), access_token=svc.create_token(user))
 
 
# ── 3. LOGIN CŨ: password + audio (giữ để backward-compat) ───────────────────
 
@router.post("/login", response_model=AuthResponse)
async def login(
    email:    str = Form(...),
    password: str = Form(...),
    file:     Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """
    Endpoint cũ — password + audio trong 1 request.
    Vẫn hoạt động bình thường; không dùng trong flow mới.
    """
    svc  = AuthService(db)
    user = svc.authenticate(email, password)
    if not user:
        raise HTTPException(401, "Email hoặc mật khẩu không đúng")
 
    if user.voice_embedding is not None:
        if file is None:
            raise HTTPException(
                400,
                "Tài khoản yêu cầu xác thực giọng nói. Vui lòng gửi kèm file audio.",
            )
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(400, "File audio rỗng")
 
        try:
            vs          = voice_router.voice_service
            bio         = _get_biometric()
            transcribed = await vs.transcribe(audio_bytes)
            is_match, score, reason = await bio.verify_voice(
                str(user.id), audio_bytes, transcribed
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Voice login error: {e}")
            raise HTTPException(500, f"Lỗi xử lý giọng nói: {e}")
 
        if not is_match:
            raise HTTPException(
                401,
                f"Xác thực giọng nói thất bại: {reason or f'score={score:.4f}'}",
            )
 
    return AuthResponse(user=_user_resp(user), access_token=svc.create_token(user))
 
 
# ── 4. ME ─────────────────────────────────────────────────────────────────────
 
@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return _user_resp(current_user)
 
 
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
@router.post("/setup-2ndkey")
async def setup_2ndkey(
    data: dict,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pin = data.get("pin")
    enable = data.get("enable_2ndkey", True)
    
    if not pin or not pin.isdigit() or not (6 <= len(pin) <= 8):
        raise HTTPException(400, "PIN không hợp lệ")
    
    current_user.second_key = pin
    current_user.enable_2ndkey = enable
    db.commit()
    return {"success": True, "message": "Đã lưu 2nd Key"}

@router.post("/verify-2ndkey")
async def verify_2ndkey(
    data: dict,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pin = data.get("pin")
    if not pin or current_user.second_key != pin or not current_user.enable_2ndkey:
        raise HTTPException(401, "PIN không đúng")
    
    # Reset fail count
    current_user.voice_fail_count = 0
    db.commit()
    return {"success": True}