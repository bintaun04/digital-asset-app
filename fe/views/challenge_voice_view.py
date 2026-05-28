# fe/views/challenge_voice_view.py
import customtkinter as ctk
from tkinter import messagebox
import sounddevice as sd
from scipy.io.wavfile import write
import tempfile
import os
import requests


class ChallengeVoiceView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller    = controller
        self.file_path     = None
        self.challenge_id  = None
        self.user_language = "vi"

        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="🔐 Xác thực giọng nói",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(pady=(28, 4))

        ctk.CTkLabel(
            self,
            text="Bước 2 / 2 — Đọc to câu bên dưới để xác minh danh tính",
            font=ctk.CTkFont(size=12), text_color="gray",
        ).pack(pady=(0, 16))

        # Ngôn ngữ hiển thị (không cho user chọn — lấy từ profile)
        self.lang_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#4a9eff",
        )
        self.lang_label.pack(pady=(0, 8))

        # Challenge text box
        ctk.CTkLabel(
            self, text="Câu cần đọc:", font=ctk.CTkFont(size=13),
        ).pack(anchor="w", padx=40)

        self.challenge_box = ctk.CTkTextbox(
            self, height=100, wrap="word", font=ctk.CTkFont(size=14),
        )
        self.challenge_box.pack(pady=6, padx=30, fill="x")

        # Buttons
        self.btn_get = ctk.CTkButton(
            self, text="📝 Lấy Challenge", height=42, width=300,
            command=self.get_challenge,
        )
        self.btn_get.pack(pady=10)

        self.btn_record = ctk.CTkButton(
            self, text="🎤 Ghi âm (5 giây)", height=46, width=300,
            fg_color="#d32f2f", hover_color="#b71c1c",
            state="disabled", command=self.start_recording,
        )
        self.btn_record.pack(pady=6)

        self.btn_verify = ctk.CTkButton(
            self, text="✅ Xác thực & Đăng nhập",
            height=50, width=300,
            fg_color="#2e7d32", hover_color="#1b5e20",
            state="disabled",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.verify,
        )
        self.btn_verify.pack(pady=10)

        self.status_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=13),
        )
        self.status_label.pack(pady=8)

        ctk.CTkButton(
            self, text="← Huỷ / Quay lại đăng nhập",
            fg_color="gray", width=300, command=self._cancel,
        ).pack(pady=4)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def tkraise(self, *args, **kwargs):
        if self.controller.current_user:
            self.user_language = self.controller.current_user.get("voice_language", "vi")
        flag = "🇻🇳 Tiếng Việt" if self.user_language == "vi" else "🇬🇧 English"
        self.lang_label.configure(text=f"Ngôn ngữ đăng ký: {flag}")
        self._reset()
        super().tkraise(*args, **kwargs)

    def _reset(self):
        self.challenge_id = None
        self.challenge_box.delete("1.0", "end")
        self.challenge_box.insert("1.0", "Nhấn 'Lấy Challenge' để bắt đầu…")
        self.btn_record.configure(state="disabled")
        self.btn_verify.configure(state="disabled")
        self.status_label.configure(text="")
        self._cleanup_audio()

    def _cancel(self):
        """Huỷ toàn bộ phiên, xoá session tạm, về Login."""
        self.controller.current_user = None
        self.controller.token        = None
        self._reset()
        self.controller.show_frame("LoginView")

    # ── Get challenge ─────────────────────────────────────────────────────────

    def get_challenge(self):
        if not self.controller.current_user:
            messagebox.showerror("Lỗi", "Phiên không hợp lệ! Vui lòng đăng nhập lại.")
            self.controller.show_frame("LoginView")
            return

        self.btn_get.configure(state="disabled", text="Đang lấy…")
        self.update()
        try:
            backend = getattr(self.controller, "BACKEND_URL", "http://localhost:8000")
            resp = requests.get(
                f"{backend}/voice/challenge",
                params={
                    "user_id":  self.controller.current_user["id"],
                    "language": self.user_language,
                },
                headers={"Authorization": f"Bearer {self.controller.token}"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            self.challenge_id = data["challenge_id"]
            self.challenge_box.delete("1.0", "end")
            self.challenge_box.insert("1.0", data["challenge_text"])

            self.btn_record.configure(state="normal")
            self.status_label.configure(
                text=f"✅ Challenge sẵn sàng (hết hạn sau {data.get('expires_in', 90)}s)",
                text_color="green",
            )
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lấy challenge:\n{e}")
        finally:
            self.btn_get.configure(state="normal", text="📝 Lấy Challenge")

    # ── Record ────────────────────────────────────────────────────────────────

    def start_recording(self):
        try:
            self.status_label.configure(
                text="🔴 Đang ghi âm… Đọc to câu phía trên", text_color="orange",
            )
            self.btn_record.configure(state="disabled")
            self.update()

            fs = 16000
            recording = sd.rec(int(5 * fs), samplerate=fs, channels=1, dtype="int16")
            sd.wait()

            self._cleanup_audio()
            self.file_path = tempfile.mktemp(suffix=".wav")
            write(self.file_path, fs, recording)

            self.status_label.configure(text="✔ Ghi âm xong!", text_color="green")
            self.btn_verify.configure(state="normal")

        except Exception as e:
            messagebox.showerror("Lỗi ghi âm", str(e))
            self.status_label.configure(text="Ghi âm thất bại", text_color="red")
        finally:
            self.btn_record.configure(state="normal")

    # ── Verify → hoàn tất đăng nhập ──────────────────────────────────────────

    def verify(self):
        if not self.file_path or not self.challenge_id:
            messagebox.showwarning("Cảnh báo", "Chưa có challenge hoặc file ghi âm!")
            return

        user_id = str(self.controller.current_user.get("id"))
        self.btn_verify.configure(state="disabled", text="Đang xác thực…")
        self.status_label.configure(text="Đang gửi lên server…", text_color="orange")
        self.update()

        try:
            with open(self.file_path, "rb") as f:
                resp = requests.post(
                    f"{self.controller.BACKEND_URL}/voice/verify-challenge",
                    files={"file": ("challenge.wav", f, "audio/wav")},
                    data={
                        "user_id":      user_id,
                        "challenge_id": self.challenge_id,
                        "language":     self.user_language,
                    },
                    headers={"Authorization": f"Bearer {self.controller.token}"},
                    timeout=40,
                )
            result = resp.json()

            if result.get("success"):
                score = result.get("score", 0)
                messagebox.showinfo(
                    "Đăng nhập thành công",
                    f"✅ Xác thực giọng nói thành công!\nScore: {score:.4f}",
                )
                # Gọi login_success — giữ current_user/token đã có, chuyển HomeUserView
                self.controller.login_success(
                    self.controller.current_user,
                    self.controller.token,
                )
            else:
                msg = result.get("message", "Xác thực thất bại")
                messagebox.showerror(
                    "Xác thực thất bại",
                    f"❌ {msg}\n\nVui lòng nhấn 'Lấy Challenge' để thử lại.",
                )
                self.status_label.configure(text=f"❌ {msg}", text_color="red")
                # Reset để thử lại — không xoá session
                self.challenge_id = None
                self.btn_record.configure(state="disabled")
                self.btn_verify.configure(state="disabled")

        except Exception as e:
            messagebox.showerror("Lỗi", f"Xảy ra lỗi:\n{e}")
        finally:
            self.btn_verify.configure(state="normal", text="✅ Xác thực & Đăng nhập")
            self._cleanup_audio()

    def _cleanup_audio(self):
        if self.file_path and os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
            except Exception:
                pass
        self.file_path = None