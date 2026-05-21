# main.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.database import create_tables
from app.api.voice import router as voice_router, init_voice_services
from app.api.auth import router as auth_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("DigitalAssetVoice")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Reset DB và tạo lại tables
    create_tables()

    # 2. Khởi tạo voice services
    logger.info("🚀 Đang khởi tạo Voice & Biometric Services...")
    voice_config = {
        "whisper": {
            "model_size": "vinai/PhoWhisper-small",
            "device": "cpu",
            "compute_type": "int8",
            "language": "vi",
            "vad_filter": False,
        }
    }
    init_voice_services(voice_config)
    logger.info("✅ Voice & Biometric System đã sẵn sàng!")
    yield


app = FastAPI(
    title="Digital Asset Voice Manager",
    description="Quản lý tài sản số bằng giọng nói với MFCC + DFT + Whisper",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(voice_router, prefix="/voice", tags=["Voice"])
app.include_router(auth_router,  prefix="/auth",  tags=["Auth"])


@app.get("/")
async def root():
    return {"message": "Digital Asset Voice API đang chạy!", "status": "ok", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Voice Biometric API is running"}


def _make_json_safe(obj):
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    elif isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_safe(item) for item in obj]
    return obj


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": _make_json_safe(exc.errors())},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)