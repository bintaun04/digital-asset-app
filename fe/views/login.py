# fe/views/login.py
import customtkinter as ctk
import sounddevice as sd
from scipy.io.wavfile import write
from tkinter import messagebox
import tempfile
import os

from services.auth_api import login_user


class LoginView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.file_path = None  # file ghi âm tạm

        ctk.CTkLabel(self, text="Đăng nhập",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(pady=30)

        self.email = ctk.CTkEntry(self, placeholder_text="Email", width=300)
        self.email.pack(pady=10)

        self.password = ctk.CTkEntry(self, placeholder_text="Mật khẩu",
                                     show="*", width=300)
        self.password.pack(pady=10)

        # Ghi âm giọng nói
        self.btn_record = ctk.CTkButton(
            self, text="🎤 Ghi âm giọng nói (5 giây)",
            width=300, height=40, fg_color="#1f6aa5",
            command=self.record_voice,
        )
        self.btn_record.pack(pady=10)

        self.voice_status = ctk.CTkLabel(
            self, text="Chưa ghi âm – bỏ qua nếu chưa đăng ký giọng nói",
            font=ctk.CTkFont(size=12), text_color="gray",
        )
        self.voice_status.pack(pady=4)

        self.btn_login = ctk.CTkButton(
            self, text="Đăng nhập", width=300, height=42,
            command=self.login,
        )
        self.btn_login.pack(pady=18)

        ctk.CTkButton(self, text="← Quay lại", width=300, fg_color="gray",
                      command=lambda: controller.show_frame("HomeGuest")).pack()

    # ── Ghi âm ────────────────────────────────────────────────────────────────
    def record_voice(self):
        try:
            self.voice_status.configure(text="🔴 Đang ghi âm... Hãy nói rõ ràng",
                                        text_color="orange")
            self.btn_record.configure(state="disabled")
            self.update()

            fs = 16000
            recording = sd.rec(int(5 * fs), samplerate=fs, channels=1, dtype="float32")
            sd.wait()

            # Xóa file cũ nếu có
            self._cleanup_audio()

            self.file_path = tempfile.mktemp(suffix=".wav")
            write(self.file_path, fs, recording)

            self.voice_status.configure(text="✔ Ghi âm hoàn tất – sẽ dùng để xác thực",
                                        text_color="green")
        except Exception as e:
            messagebox.showerror("Lỗi ghi âm", str(e))
            self.voice_status.configure(text="Ghi âm thất bại", text_color="red")
        finally:
            self.btn_record.configure(state="normal")

    # ── Đăng nhập ─────────────────────────────────────────────────────────────
    def login(self):
        email = self.email.get().strip()
        password = self.password.get()

        if not email or not password:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập đầy đủ email và mật khẩu!")
            return

        self.btn_login.configure(state="disabled", text="Đang đăng nhập...")
        self.update()

        try:
            # Nếu có file ghi âm → login đầy đủ, không có → login chỉ password
            data = login_user(email, password, self.file_path)

            user = data.get("user", {})
            token = data.get("access_token")
            has_voice = user.get("has_voice", False)

            self.password.delete(0, "end")
            self._cleanup_audio()

            # Nếu login thành công nhưng chưa enroll giọng → nhắc enroll
            if not has_voice:
                self.controller.current_user = user
                self.controller.token = token
                messagebox.showinfo(
                    "Đăng nhập thành công",
                    "Bạn chưa đăng ký giọng nói.\n"
                    "Hãy đăng ký giọng nói để bảo mật tài khoản!",
                )
                self.controller.show_frame("VoiceRegisterView")
            else:
                self.controller.login_success(user, token)

        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg:
                if "Giọng nói không khớp" in error_msg:
                    messagebox.showerror("Lỗi", "Giọng nói không khớp!\nVui lòng ghi âm lại.")
                else:
                    messagebox.showerror("Lỗi", "Email hoặc mật khẩu không đúng!")
            elif "400" in error_msg and "audio" in error_msg.lower():
                messagebox.showerror(
                    "Cần giọng nói",
                    "Tài khoản này yêu cầu xác thực giọng nói.\n"
                    "Nhấn 'Ghi âm giọng nói' trước khi đăng nhập!",
                )
            else:
                messagebox.showerror("Lỗi", f"Đăng nhập thất bại:\n{error_msg}")
        finally:
            self.btn_login.configure(state="normal", text="Đăng nhập")

    def _cleanup_audio(self):
        if self.file_path and os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
            except Exception:
                pass
        self.file_path = None

    def destroy(self):
        self._cleanup_audio()
        super().destroy()