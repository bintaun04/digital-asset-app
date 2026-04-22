import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.database import create_tables, get_db 
# Import routers
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.api.voice import router as voice_router, init_voice_services
from app.api.auth import router as auth_router
app = FastAPI()

# Tạo tables khi startup
create_tables()

app.include_router(auth_router)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("DigitalAssetVoice")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo các service khi app startup"""
    logger.info("🚀 Đang khởi tạo Voice & Biometric Services (MFCC + DFT)...")
    
    voice_config = {
        "whisper": {
            "model_size": "vinai/PhoWhisper-small",
            "device": "cpu",
            "compute_type": "int8",
            "language": "vi",
            "vad_filter": False
        }
    }
    
    # Khởi tạo VoiceService và BiometricService
    init_voice_services(voice_config)
    
    logger.info("✅ Voice & Biometric System đã sẵn sàng!")
    yield
    # Code sau yield sẽ chạy khi app shutdown (nếu cần dọn dẹp)


# Tạo FastAPI app
app = FastAPI(
    title="Digital Asset Voice Manager",
    description="Quản lý tài sản số bằng giọng nói với MFCC + DFT + Whisper",
    version="1.0.0",
    lifespan=lifespan
)

# CORS - Cho phép FE Tkinter gọi API (dùng "*" trong dev, nên giới hạn sau)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Thay bằng ["http://localhost", ...] khi production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký routers
app.include_router(voice_router, prefix="/voice", tags=["Voice"])
app.include_router(auth_router, prefix="/auth", tags=["Auth"])   

@app.get("/")
async def root():
    return {
        "message": "Digital Asset Voice API đang chạy thành công!",
        "status": "ok",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "message": "Voice Biometric API is running"
    }
def _make_json_safe(obj):
    """
    Đệ quy chuyển đổi object thành JSON-safe,
    xử lý bytes không decode được bằng UTF-8.
    """
    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            # Thay thế byte lỗi bằng ký tự placeholder
            return obj.decode("utf-8", errors="replace")
    elif isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_safe(item) for item in obj]
    return obj


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    """
    Custom handler: tránh crash khi error details chứa binary data
    không decode được bằng UTF-8.
    """
    safe_errors = _make_json_safe(exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": safe_errors},
    )
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)