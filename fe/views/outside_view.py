# fe/views/outside_view.py
"""
OutsideView — Frame đầy đủ 500x680.
- 5 button điều hướng đến các frame thật trong app
- Micro luôn mở: ghi âm 3s liên tục → STT → thực thi lệnh điều hướng
- Không dùng MFCC/GE2E, chỉ STT keyword matching
"""

import customtkinter as ctk
from tkinter import messagebox
import threading
import queue
import requests
import tempfile
import os

try:
    import sounddevice as sd
    from scipy.io.wavfile import write as wav_write
    _AUDIO_OK = True
except ImportError:
    _AUDIO_OK = False

FS        = 16000
CHUNK_SEC = 3

# Map action từ BE → frame name trong app
_ACTION_FRAME = {
    "trang_chu":  "HomeUserView",
    "thi_truong": "MarketView",       # placeholder nếu chưa có frame
    "thong_bao":  "NotificationView", # placeholder
    "cai_dat":    "SettingView",      # placeholder
    "tro_giup":   "HelpView",         # placeholder
    "insight":    "InsightView",
}

# (label, frame_name, color, hover_color)
_BUTTONS_DEF = [
    ("🏠  Trang chủ",   "HomeUserView",       "#1a237e", "#283593"),
    ("📊  Insight",     "InsightView",         "#1565c0", "#1976d2"),
    ("🔔  Thông báo",   "NotificationView",    "#4a148c", "#6a1b9a"),
    ("⚙️  Cài đặt",    "SettingView",         "#37474f", "#455a64"),
    ("❓  Trợ giúp",    "HelpView",            "#bf360c", "#d84315"),
]


class OutsideView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._running   = False
        self._thread    = None
        self._q         = queue.Queue()
        self._btn_refs  = []   # list of (btn_widget, default_fg_color)

        self._build_ui()
        self._poll()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="🎙️ Voice Command Center",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(pady=(28, 4))

        ctk.CTkLabel(
            self,
            text="Nói tên chức năng để điều hướng tự động",
            font=ctk.CTkFont(size=12), text_color="gray",
        ).pack(pady=(0, 10))

        # ── Mic status ────────────────────────────────────────────────────────
        self.mic_label = ctk.CTkLabel(
            self,
            text="⚪ Micro chưa bật" if _AUDIO_OK else "❌ Cần cài: pip install sounddevice scipy",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="gray",
        )
        self.mic_label.pack(pady=(0, 6))

        # ── STT result ────────────────────────────────────────────────────────
        self.stt_label = ctk.CTkLabel(
            self, text='💬 "…"',
            font=ctk.CTkFont(size=13),
            text_color="#90caf9",
            wraplength=420,
        )
        self.stt_label.pack(pady=(0, 18))

        # ── 5 Navigation buttons ───────────────────────────────────────────────
        for label, frame_name, color, hover in _BUTTONS_DEF:
            btn = ctk.CTkButton(
                self,
                text=label,
                height=48, width=340,
                corner_radius=10,
                fg_color=color,
                hover_color=hover,
                anchor="w",
                font=ctk.CTkFont(size=14),
                command=lambda fn=frame_name: self._navigate(fn),
            )
            btn.pack(pady=5)
            self._btn_refs.append((btn, color))

        # ── Mic toggle ────────────────────────────────────────────────────────
        self.btn_mic = ctk.CTkButton(
            self,
            text="🎙️ Bật Micro",
            width=340, height=42,
            fg_color="#00695c", hover_color="#00796b",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._toggle_mic,
            state="normal" if _AUDIO_OK else "disabled",
        )
        self.btn_mic.pack(pady=(16, 6))

        ctk.CTkButton(
            self,
            text="← Trang chủ", width=340,
            fg_color="gray",
            command=lambda: self.controller.show_frame("HomeUserView"),
        ).pack(pady=4)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def tkraise(self, *args, **kwargs):
        super().tkraise(*args, **kwargs)
        if _AUDIO_OK and not self._running:
            self._start_mic()

    def on_hide(self):
        self._stop_mic()

    # ── Mic control ───────────────────────────────────────────────────────────

    def _toggle_mic(self):
        if self._running:
            self._stop_mic()
        else:
            self._start_mic()

    def _start_mic(self):
        if not _AUDIO_OK or self._running:
            return
        self._running = True
        self.mic_label.configure(text="🔴 Đang lắng nghe…", text_color="#ef5350")
        self.btn_mic.configure(
            text="⏹ Tắt Micro", fg_color="#c62828", hover_color="#b71c1c",
        )
        self._thread = threading.Thread(target=self._mic_loop, daemon=True)
        self._thread.start()

    def _stop_mic(self):
        self._running = False
        self.mic_label.configure(text="⚪ Micro đã tắt", text_color="gray")
        self.btn_mic.configure(
            text="🎙️ Bật Micro", fg_color="#00695c", hover_color="#00796b",
        )

    # ── Background loop ───────────────────────────────────────────────────────

    def _mic_loop(self):
        while self._running:
            try:
                rec = sd.rec(
                    int(CHUNK_SEC * FS), samplerate=FS,
                    channels=1, dtype="int16",
                )
                sd.wait()
                if not self._running:
                    break

                tmp = tempfile.mktemp(suffix=".wav")
                wav_write(tmp, FS, rec)

                try:
                    backend = getattr(self.controller, "BACKEND_URL", "http://localhost:8000")
                    token   = self.controller.token or ""
                    uid     = (self.controller.current_user or {}).get("id", 0)

                    with open(tmp, "rb") as f:
                        resp = requests.post(
                            f"{backend}/voice/command-nav",
                            files={"file": ("nav.wav", f, "audio/wav")},
                            data={"user_id": str(uid)},
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=15,
                        )
                    if resp.ok:
                        self._q.put(resp.json())
                    else:
                        self._q.put({"error": f"HTTP {resp.status_code}"})
                except Exception as e:
                    self._q.put({"error": str(e)})
                finally:
                    try:
                        os.remove(tmp)
                    except Exception:
                        pass

            except Exception as e:
                self._q.put({"error": str(e)})
                break

    # ── Poll queue → update UI ────────────────────────────────────────────────

    def _poll(self):
        try:
            while True:
                result = self._q.get_nowait()
                self._handle(result)
        except queue.Empty:
            pass
        self.after(400, self._poll)

    def _handle(self, result: dict):
        if "error" in result:
            self.stt_label.configure(
                text=f"⚠ {result['error']}", text_color="#ffb74d",
            )
            return

        text   = result.get("text", "").strip()
        action = result.get("action", "")

        # Cập nhật STT text (chỉ khi có nội dung)
        if text:
            self.stt_label.configure(text=f'💬 "{text}"', text_color="#90caf9")

        # Highlight button + điều hướng nếu nhận ra lệnh
        if action:
            self._highlight(action)
            frame_name = _ACTION_FRAME.get(action, "")
            if frame_name:
                self._navigate(frame_name)

    def _highlight(self, action: str):
        """Highlight button tương ứng 1.5s rồi reset màu."""
        action_idx = {
            "trang_chu":  0,
            "insight":    1,
            "thong_bao":  2,
            "cai_dat":    3,
            "tro_giup":   4,
        }
        idx = action_idx.get(action)
        for i, (btn, default_color) in enumerate(self._btn_refs):
            btn.configure(fg_color="#f9a825" if i == idx else default_color)
        # Reset sau 1.5s
        self.after(1500, self._reset_colors)

    def _reset_colors(self):
        for btn, default_color in self._btn_refs:
            btn.configure(fg_color=default_color)

    def _navigate(self, frame_name: str):
        """Điều hướng — nếu frame chưa tồn tại thì báo."""
        if frame_name in self.controller.frames:
            self.controller.show_frame(frame_name)
        else:
            messagebox.showinfo(
                "Chức năng đang phát triển",
                f"Màn hình '{frame_name}' chưa được xây dựng.",
            )