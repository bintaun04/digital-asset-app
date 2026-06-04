import customtkinter as ctk
import sounddevice as sd
from scipy.io.wavfile import write
import tempfile
import os
from tkinter import messagebox
import numpy as np
import time
from services.voice_api import verify_voice


class VerifyVoiceView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.file_path = None
        self.user_language = "vi"

        # === THÊM MỚI ===
        self.is_recording = False
        self.recording_frames = []
        self.stream = None
        self.start_time = None
        self.timer_id = None

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

        # === NÚT GHI ÂM TOGGLE ===
        self.btn_record = ctk.CTkButton(
            self, 
            text="🎤 Bắt đầu ghi âm",
            width=320, 
            height=50, 
            font=ctk.CTkFont(size=16),
            command=self.toggle_recording
        )
        self.btn_record.pack(pady=20)

        # Timer + Waveform
        self.timer_label = ctk.CTkLabel(self, text="00:00", font=ctk.CTkFont(size=16, weight="bold"))
        self.timer_label.pack(pady=2)

        self.wave_canvas = ctk.CTkCanvas(self, height=60, width=300, bg="#1a1a2e", highlightthickness=0)
        self.wave_canvas.pack(pady=8)

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
        if self.controller.current_user:
            self.user_language = self.controller.current_user.get("voice_language", "vi")
        else:
            self.user_language = "vi"

        self._update_language_ui()
        
        # Reset trạng thái
        self._cleanup_audio()
        self._reset_recording_ui()
        self.btn_verify.configure(state="disabled")
        self.status_label.configure(text="")
        
        super().tkraise(*args, **kwargs)

    def _update_language_ui(self):
        """Cập nhật UI theo ngôn ngữ đã đăng ký"""
        if self.user_language == "vi":
            self.lang_label.configure(text="🇻🇳 Ngôn ngữ: Tiếng Việt")
            self.instruction_label.configure(
                text="Nói rõ ràng câu bạn đã đăng ký để xác thực danh tính"
            )
            self.btn_record.configure(text="🎤 Bắt đầu ghi âm")
            self.btn_verify.configure(text="✅ Xác thực giọng nói")
        else:
            self.lang_label.configure(text="🇬🇧 Language: English")
            self.instruction_label.configure(
                text="Speak clearly the sentence you registered\nto verify your identity"
            )
            self.btn_record.configure(text="🎤 Start Recording")
            self.btn_verify.configure(text="✅ Verify Voice")

    # ==================== GHI ÂM TOGGLE + TIMER + WAVEFORM ====================
    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        try:
            self.is_recording = True
            self.recording_frames = []
            self.start_time = time.time()
            self.btn_record.configure(text="⏹️ Dừng ghi âm", fg_color="#c62828")
            self.status_label.configure(text="🔴 Đang ghi âm...", text_color="orange")
            self.update()

            def callback(indata, frames, time_info, status):
                if status: print(status)
                self.recording_frames.append(indata.copy())

            self.stream = sd.InputStream(samplerate=16000, channels=1, dtype='int16', callback=callback)
            self.stream.start()
            self._update_timer_and_wave()
        except Exception as e:
            messagebox.showerror("Lỗi ghi âm", str(e))
            self._reset_recording_ui()

    def stop_recording(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if self.recording_frames:
            recording = np.concatenate(self.recording_frames, axis=0)
            self.file_path = tempfile.mktemp(suffix=".wav")
            write(self.file_path, 16000, recording)

            self.status_label.configure(text="✔ Ghi âm hoàn tất!", text_color="green")
            self.btn_verify.configure(state="normal")
        else:
            self.status_label.configure(text="Không có dữ liệu ghi âm", text_color="red")

        self._reset_recording_ui()

    def _update_timer_and_wave(self):
        if not self.is_recording:
            return
        elapsed = int(time.time() - self.start_time)
        self.timer_label.configure(text=f"{elapsed//60:02d}:{elapsed%60:02d}")

        self.wave_canvas.delete("all")
        if self.recording_frames:
            data = self.recording_frames[-1].flatten()[:300]
            for i, val in enumerate(data[::3]):
                height = int(abs(val) / 400)
                x = i * 3
                self.wave_canvas.create_line(x, 30 - height, x, 30 + height, fill="#00ff88", width=2)

        self.timer_id = self.after(50, self._update_timer_and_wave)

    def _reset_recording_ui(self):
        self.is_recording = False
        if self.timer_id:
            self.after_cancel(self.timer_id)
        self.btn_record.configure(text="🎤 Bắt đầu ghi âm" if self.user_language == "vi" else "🎤 Start Recording", 
                                 fg_color="#d32f2f")
        self.timer_label.configure(text="00:00")
        self.wave_canvas.delete("all")

    # ==================== VERIFY (GIỮ NGUYÊN) ====================
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
            result = verify_voice(
                user_id=user_id,
                file_path=self.file_path,
                token=self.controller.token,
                language=self.user_language
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