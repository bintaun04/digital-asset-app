# fe/views/voice_register.py
import customtkinter as ctk
import sounddevice as sd
from scipy.io.wavfile import write
from tkinter import messagebox
import tempfile
import os
import numpy as np 
from services.voice_api import enroll_voice


class VoiceRegisterView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.file_path = None

        ctk.CTkLabel(self, text="Đăng ký giọng nói",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(pady=25)
        ctk.CTkLabel(
            self,
            text="Đây là bước bảo mật bắt buộc.\n"
                 "Giọng nói sẽ được dùng để xác thực khi đăng nhập.",
            font=ctk.CTkFont(size=12), text_color="gray",
        ).pack(pady=(0, 20))

        self.btn_record = ctk.CTkButton(
            self, text="🎤 Bắt đầu ghi âm (5 giây)",
            width=300, height=45, command=self.start_record,
        )
        self.btn_record.pack(pady=15)

        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=13))
        self.status_label.pack(pady=8)

        self.btn_enroll = ctk.CTkButton(
            self, text="✅ Lưu giọng nói",
            width=300, height=45, fg_color="green",
            state="disabled", command=self.enroll,
        )
        self.btn_enroll.pack(pady=10)

        ctk.CTkButton(
            self, text="Bỏ qua (không khuyến khích)", fg_color="gray", width=300,
            command=self._skip,
        ).pack(pady=10)

    def tkraise(self, *args, **kwargs):
        """Reset trạng thái mỗi khi frame được hiển thị lại."""
        self._cleanup_audio()
        self.btn_enroll.configure(state="disabled", text="✅ Lưu giọng nói")
        self.status_label.configure(text="")
        super().tkraise(*args, **kwargs)

    # ── Ghi âm ────────────────────────────────────────────────────────────────
    def start_record(self):
        try:
            self.status_label.configure(text="🔴 Đang ghi âm... Hãy nói rõ ràng",
                                        text_color="orange")
            self.btn_record.configure(state="disabled")
            self.btn_enroll.configure(state="disabled")
            self.update()

            fs = 16000
            recording = sd.rec(int(5 * fs), samplerate=fs, channels=1, dtype="int16")
            sd.wait()

            self._cleanup_audio()
            self.file_path = tempfile.mktemp(suffix=".wav")
            write(self.file_path, fs, recording)

            self.status_label.configure(text="✔ Ghi âm hoàn tất – nhấn Lưu để tiếp tục",
                                        text_color="green")
            self.btn_enroll.configure(state="normal")

        except Exception as e:
            messagebox.showerror("Lỗi ghi âm", str(e))
            self.status_label.configure(text="Ghi âm thất bại", text_color="red")
        finally:
            self.btn_record.configure(state="normal")

    # ── Enroll ────────────────────────────────────────────────────────────────
    def enroll(self):
        if not self.file_path:
            messagebox.showwarning("Cảnh báo", "Vui lòng ghi âm trước!")
            return
        if not self.controller.current_user:
            messagebox.showerror("Lỗi", "Không tìm thấy thông tin người dùng!\nVui lòng đăng ký lại.")
            self.controller.show_frame("RegisterView")
            return

        user_id = str(self.controller.current_user.get("id"))
        token = self.controller.token

        self.btn_enroll.configure(state="disabled", text="Đang lưu...")
        self.status_label.configure(text="Đang gửi lên server...", text_color="orange")
        self.update()

        try:
            enroll_voice(user_id, self.file_path, token)
            self._cleanup_audio()

            # ✅ Cập nhật has_voice trong controller
            if self.controller.current_user:
                self.controller.current_user["has_voice"] = True

            messagebox.showinfo(
                "Thành công!",
                "Đăng ký giọng nói thành công!\n\n"
                "Từ lần sau, hãy ghi âm giọng nói khi đăng nhập.",
            )
            self.controller.show_frame("HomeUserView")

        except Exception as e:
            messagebox.showerror("Lỗi", f"Đăng ký giọng nói thất bại:\n{str(e)}")
            self.status_label.configure(text="Đăng ký thất bại – thử lại", text_color="red")
        finally:
            self.btn_enroll.configure(state="normal", text="✅ Lưu giọng nói")

    def _skip(self):
        """Cho phép bỏ qua enroll (vào HomeUser với has_voice=False)."""
        if messagebox.askyesno(
            "Bỏ qua?",
            "Bạn chưa đăng ký giọng nói.\n"
            "Tài khoản sẽ kém bảo mật hơn.\n\n"
            "Tiếp tục mà không đăng ký giọng nói?",
        ):
            self._cleanup_audio()
            self.controller.show_frame("HomeUserView")

    def _cleanup_audio(self):
        if self.file_path and os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
            except Exception:
                pass
        self.file_path = None