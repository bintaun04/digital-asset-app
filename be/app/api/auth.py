# backend/app/api/auth.py
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..services.auth_service import AuthService

router = APIRouter()
security = HTTPBearer(auto_error=False)

# ========================= Schemas =========================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = ""

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = ""

    class Config:
        from_attributes = True

class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"

class MessageResponse(BaseModel):
    message: str

class MeResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = ""

# ========================= Dependency =========================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chưa đăng nhập",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    auth_service = AuthService(db)
    user = auth_service.get_user_from_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# ========================= Endpoints =========================

@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """
    Đăng ký tài khoản mới.
    - **email**: địa chỉ email hợp lệ, không trùng lặp
    - **password**: mật khẩu tối thiểu 6 ký tự
    - **full_name**: họ và tên (tùy chọn)
    """
    auth_service = AuthService(db)

    if auth_service.get_user_by_email(body.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã được đăng ký"
        )

    if len(body.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu phải có ít nhất 6 ký tự"
        )

    user = auth_service.create_user(
        email=body.email,
        password=body.password,
        full_name=body.full_name
    )
    token = auth_service.create_token(user)

    return AuthResponse(
        user=UserResponse(id=user.id, email=user.email, full_name=user.full_name),
        access_token=token
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    """
    Đăng nhập bằng email và mật khẩu.
    Trả về JWT token dùng cho các request sau.
    """
    auth_service = AuthService(db)
    user = auth_service.authenticate(body.email, body.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không đúng"
        )

    token = auth_service.create_token(user)

    return AuthResponse(
        user=UserResponse(id=user.id, email=user.email, full_name=user.full_name),
        access_token=token
    )


@router.get("/me", response_model=MeResponse)
async def get_me(current_user=Depends(get_current_user)):
    """
    Lấy thông tin người dùng hiện tại.
    Yêu cầu Bearer token hợp lệ trong header.
    """
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user=Depends(get_current_user)):
    """
    Đăng xuất (phía client xóa token).
    JWT là stateless nên server chỉ xác nhận token hợp lệ.
    """
    return MessageResponse(message=f"Đã đăng xuất tài khoản {current_user.email}")


@router.put("/change-password", response_model=MessageResponse)
async def change_password(
    old_password: str,
    new_password: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Đổi mật khẩu.
    Yêu cầu mật khẩu cũ đúng và mật khẩu mới tối thiểu 6 ký tự.
    """
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới phải có ít nhất 6 ký tự"
        )

    auth_service = AuthService(db)
    success = auth_service.change_password(current_user, old_password, new_password)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu cũ không đúng"
        )

    return MessageResponse(message="Đổi mật khẩu thành công")