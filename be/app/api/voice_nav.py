# backend/app/api/voice_nav.py
"""
POST /voice/command-nav
Form: file (audio/wav), user_id

Flow: STT → keyword match → trả action
Không dùng MFCC/GE2E — chỉ nhận diện lệnh điều hướng bằng text.

Action values:
  "trang_chu" | "insight" | "thong_bao" | "cai_dat" | "tro_giup" | ""
"""

import logging
from difflib import SequenceMatcher
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("VoiceNavAPI")
router = APIRouter()

# ── Keyword map ───────────────────────────────────────────────────────────────
_KEYWORDS: dict[str, list[str]] = {
    "trang_chu": [
        "trang chủ", "trang chu", "home", "màn hình chính",
        "quay lại", "về nhà", "trang chính",
    ],
    "insight": [
        "insight", "lịch sử", "lich su", "xem lịch sử",
        "lịch sử giọng nói", "thống kê", "thong ke",
    ],
    "thong_bao": [
        "thông báo", "thong bao", "notification",
        "tin tức", "tin tuc", "cảnh báo", "canh bao",
    ],
    "cai_dat": [
        "cài đặt", "cai dat", "setting", "settings",
        "thiết lập", "thiet lap", "cấu hình", "cau hinh",
    ],
    "tro_giup": [
        "trợ giúp", "tro giup", "help", "hỗ trợ", "ho tro",
        "hướng dẫn", "huong dan", "giúp đỡ", "giup do",
    ],
}

# ── Schema ────────────────────────────────────────────────────────────────────

class NavResponse(BaseModel):
    text:       str    # STT output
    action:     str    # action nhận diện được, "" nếu không khớp
    confidence: float  # 0.0–1.0
    message:    str


# ── Matching ──────────────────────────────────────────────────────────────────

def _match(text: str) -> tuple[str, float]:
    t = text.lower().strip()
    if not t:
        return "", 0.0

    best_action = ""
    best_score  = 0.0

    for action, keywords in _KEYWORDS.items():
        for kw in keywords:
            kw_l = kw.lower()
            # Exact substring → trả ngay
            if kw_l in t:
                return action, 1.0
            # Fuzzy
            ratio = SequenceMatcher(None, kw_l, t).ratio()
            if ratio > best_score:
                best_score  = ratio
                best_action = action

    # Chỉ trả kết quả nếu đủ tự tin (≥ 0.65)
    if best_score >= 0.65:
        return best_action, round(best_score, 3)
    return "", 0.0


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/command-nav", response_model=NavResponse)
async def command_nav(
    file:    UploadFile = File(...),
    user_id: str        = Form(default="0"),
):
    audio_bytes = await file.read()
    if not audio_bytes or len(audio_bytes) < 512:
        raise HTTPException(400, "Audio quá ngắn hoặc rỗng")

    # Lấy voice_service toàn cục từ voice.py (đã init khi startup)
    from app.api.voice import voice_service

    text = ""
    if voice_service is not None:
        try:
            # STT thuần — không cần language cố định, để "vi" là mặc định
            text = await voice_service.transcribe(audio_bytes, language="vi")
        except Exception as e:
            logger.warning(f"[NavSTT] STT lỗi: {e}")
    else:
        logger.warning("[NavSTT] VoiceService chưa khởi tạo")

    action, confidence = _match(text)

    logger.info(
        f"[NavCmd] user={user_id} | stt='{text}' "
        f"| action={action or 'none'} | conf={confidence:.2f}"
    )

    if action:
        readable = action.replace("_", " ").title()
        msg = f"✅ Nhận lệnh: {readable}"
    elif text:
        msg = f"Không nhận ra lệnh từ: '{text}'"
    else:
        msg = "Không nhận diện được giọng nói"

    return NavResponse(
        text       = text,
        action     = action,
        confidence = confidence,
        message    = msg,
    )