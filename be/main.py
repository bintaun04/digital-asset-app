# backend/main.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.database import create_tables
from app.api.voice     import router as voice_router,     init_voice_services
from app.api.auth      import router as auth_router
from app.api.voice_nav import router as voice_nav_router  # ← router mới

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("DigitalAssetVoice")

create_tables()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Đang khởi tạo Voice & Biometric Services…")
    voice_config = {
        "whisper": {
            "model_size":    "vinai/PhoWhisper-small",
            "device":        "cpu",
            "compute_type":  "int8",
            "language":      "vi",
            "vad_filter":    False,
        }
    }
    init_voice_services(voice_config)
    logger.info("✅ Voice & Biometric System sẵn sàng!")
    yield


app = FastAPI(
    title="Digital Asset Voice Manager",
    description="Quản lý tài sản số bằng giọng nói — MFCC + GE2E + Whisper",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router,      prefix="/auth",  tags=["Auth"])
app.include_router(voice_router,     prefix="/voice", tags=["Voice"])
app.include_router(voice_nav_router, prefix="/voice", tags=["VoiceNav"])
# → endpoint cuối cùng: POST /voice/command-nav


# ── Root / Health ─────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "version": "1.1.0", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Voice Biometric API is running"}


# ── Validation error handler ──────────────────────────────────────────────────

def _json_safe(obj):
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(i) for i in obj]
    return obj

@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": _json_safe(exc.errors())},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)