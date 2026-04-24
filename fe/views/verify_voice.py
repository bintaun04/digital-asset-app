import customtkinter as ctk
import sounddevice as sd
from scipy.io.wavfile import write
import tempfile
import os
from tkinter import messagebox
import numpy as np
from services.voice_api import verify_voice

class VerifyVoiceView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.recording = None
        self.file_path = None
        self.user_language = "vi"  # Sẽ được set từ user profile

        # Title
        ctk.CTkLabel(
            self, 
            text="Xác thực giọng nói",
            font=ctk.CTkFont(size=26, weight="bold")
        ).pack(pady=30)

        # Language indicator
        self.lang_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#4a9eff"
        )
        self.lang_label.pack(pady=5)

        # Instructions
        self.instruction_label = ctk.CTkLabel(
            self, 
            text="",
            font=ctk.CTkFont(size=14), 
            text_color="gray"
        )
        self.instruction_label.pack(pady=(0, 25))

        # Record button
        self.btn_record = ctk.CTkButton(
            self, 
            text="🎤 Bắt đầu ghi âm (5 giây)",
            width=320, 
            height=50, 
            font=ctk.CTkFont(size=16),
            command=self.start_recording
        )
        self.btn_record.pack(pady=20)

        # Verify button
        self.btn_verify = ctk.CTkButton(
            self, 
            text="✅ Xác thực giọng nói",
            width=320, 
            height=50, 
            font=ctk.CTkFont(size=16),
            fg_color="green", 
            state="disabled", 
            command=self.verify
        )
        self.btn_verify.pack(pady=15)

        # Status label
        self.status_label = ctk.CTkLabel(
            self, 
            text="", 
            font=ctk.CTkFont(size=14)
        )
        self.status_label.pack(pady=20)

        # Back button
        ctk.CTkButton(
            self, 
            text="← Quay lại trang chủ", 
            width=320, 
            fg_color="gray",
            command=lambda: controller.show_frame("HomeUserView")
        ).pack(pady=30)

    def tkraise(self, *args, **kwargs):
        """Update UI theo ngôn ngữ user khi hiển thị frame"""
        # Lấy ngôn ngữ từ user profile
        if self.controller.current_user:
            self.user_language = self.controller.current_user.get("voice_language", "vi")
        else:
            self.user_language = "vi"

        # Cập nhật UI
        self._update_language_ui()
        
        # Reset trạng thái
        self._cleanup_audio()
        self.btn_verify.configure(state="disabled")
        self.status_label.configure(text="")
        
        super().tkraise(*args, **kwargs)

    def _update_language_ui(self):
        """Cập nhật UI theo ngôn ngữ đã đăng ký"""
        if self.user_language == "vi":
            self.lang_label.configure(text="🇻🇳 Ngôn ngữ: Tiếng Việt")
            self.instruction_label.configure(
                text="Nói rõ ràng câu bạn đã đăng ký trong 5 giây\nđể xác thực danh tính"
            )
            self.btn_record.configure(text="🎤 Bắt đầu ghi âm (5 giây)")
            self.btn_verify.configure(text="✅ Xác thực giọng nói")
        else:
            self.lang_label.configure(text="🇬🇧 Language: English")
            self.instruction_label.configure(
                text="Speak clearly the sentence you registered within 5 seconds\nto verify your identity"
            )
            self.btn_record.configure(text="🎤 Start Recording (5 seconds)")
            self.btn_verify.configure(text="✅ Verify Voice")

    def start_recording(self):
        try:
            if self.user_language == "vi":
                recording_msg = "🔴 Đang ghi âm... Hãy nói rõ ràng"
                complete_title = "Hoàn tất"
                complete_msg = "Ghi âm xong!\nNhấn 'Xác thực giọng nói' để tiếp tục."
                error_title = "Lỗi ghi âm"
                fail_msg = "Ghi âm thất bại"
            else:
                recording_msg = "🔴 Recording... Please speak clearly"
                complete_title = "Complete"
                complete_msg = "Recording finished!\nClick 'Verify Voice' to continue."
                error_title = "Recording Error"
                fail_msg = "Recording failed"

            self.status_label.configure(
                text=recording_msg,
                text_color="orange"
            )
            self.btn_record.configure(state="disabled")
            self.update()

            fs = 16000
            self.recording = sd.rec(int(5 * fs), samplerate=fs, channels=1, dtype='int16')
            sd.wait()

            self._cleanup_audio()
            self.file_path = tempfile.mktemp(suffix=".wav")
            write(self.file_path, fs, self.recording)

            complete_status = "✔ Ghi âm hoàn tất" if self.user_language == "vi" else "✔ Recording completed"
            self.status_label.configure(text=complete_status, text_color="green")
            self.btn_verify.configure(state="normal")
            messagebox.showinfo(complete_title, complete_msg)

        except Exception as e:
            messagebox.showerror(error_title, str(e))
            self.status_label.configure(text=fail_msg, text_color="red")
        finally:
            self.btn_record.configure(state="normal")

    def verify(self):
        if not self.file_path:
            warning_msg = "Chưa có file ghi âm!" if self.user_language == "vi" else "No recording file!"
            warning_title = "Cảnh báo" if self.user_language == "vi" else "Warning"
            messagebox.showwarning(warning_title, warning_msg)
            return

        if not self.controller.current_user:
            error_msg = "Bạn chưa đăng nhập!" if self.user_language == "vi" else "You are not logged in!"
            error_title = "Lỗi" if self.user_language == "vi" else "Error"
            messagebox.showerror(error_title, error_msg)
            return

        user_id = str(self.controller.current_user.get("id"))
        if not user_id:
            error_msg = "Không tìm thấy user_id" if self.user_language == "vi" else "User ID not found"
            error_title = "Lỗi" if self.user_language == "vi" else "Error"
            messagebox.showerror(error_title, error_msg)
            return

        verifying_text = "Đang xác thực..." if self.user_language == "vi" else "Verifying..."
        self.btn_verify.configure(state="disabled", text=verifying_text)
        self.status_label.configure(text=verifying_text, text_color="orange")
        self.update()

        try:
            # ✅ GỬI LANGUAGE ĐẾN BACKEND
            result = verify_voice(
                user_id=user_id,
                file_path=self.file_path,
                token=self.controller.token,
                language=self.user_language  # Sử dụng ngôn ngữ đã đăng ký
            )

            score = result.get("similarity_score", 0)
            is_verified = result.get("is_verified", False)

            if is_verified:
                if self.user_language == "vi":
                    success_msg = f"✅ Xác thực thành công!\nĐiểm tương đồng: {score:.2f}"
                    info_msg = f"Xác thực giọng nói thành công!\nĐiểm tương đồng: {score:.2f}"
                    title = "Thành công"
                else:
                    success_msg = f"✅ Verification successful!\nSimilarity score: {score:.2f}"
                    info_msg = f"Voice verification successful!\nSimilarity score: {score:.2f}"
                    title = "Success"

                self.status_label.configure(text=success_msg, text_color="green")
                messagebox.showinfo(title, info_msg)
                self.controller.show_frame("HomeUserView")
            else:
                if self.user_language == "vi":
                    fail_msg = f"❌ Xác thực thất bại\nĐiểm tương đồng: {score:.2f}"
                    warning_msg = f"Xác thực giọng nói thất bại!\nĐiểm tương đồng: {score:.2f}\n\nVui lòng thử lại."
                    title = "Thất bại"
                else:
                    fail_msg = f"❌ Verification failed\nSimilarity score: {score:.2f}"
                    warning_msg = f"Voice verification failed!\nSimilarity score: {score:.2f}\n\nPlease try again."
                    title = "Failed"

                self.status_label.configure(text=fail_msg, text_color="red")
                messagebox.showwarning(title, warning_msg)

        except Exception as e:
            error_msg = "Lỗi xác thực" if self.user_language == "vi" else "Verification error"
            error_title = "Lỗi" if self.user_language == "vi" else "Error"
            self.status_label.configure(text=error_msg, text_color="red")
            
            fail_msg = f"Xác thực thất bại:\n{str(e)}" if self.user_language == "vi" else f"Verification failed:\n{str(e)}"
            messagebox.showerror(error_title, fail_msg)
        finally:
            verify_text = "✅ Xác thực giọng nói" if self.user_language == "vi" else "✅ Verify Voice"
            self.btn_verify.configure(state="normal", text=verify_text)
            self._cleanup_audio()

    def _cleanup_audio(self):
        if self.file_path and os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
            except:
                pass
        self.file_path = None