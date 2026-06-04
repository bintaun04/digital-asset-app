# fe/views/voice_register.py
import customtkinter as ctk
import sounddevice as sd
from scipy.io.wavfile import write
from tkinter import messagebox
import tempfile
import os
import numpy as np
import time
from services.voice_api import enroll_voice


class VoiceRegisterView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.file_path = None
        self.selected_language = "vi"  

        # === THÊM MỚI ===
        self.is_recording = False
        self.recording_frames = []
        self.stream = None
        self.start_time = None
        self.timer_id = None

        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(self, text="Đăng ký giọng nói",
                    font=ctk.CTkFont(size=24, weight="bold")).pack(pady=25)
        
        ctk.CTkLabel(self,
            text="Đây là bước bảo mật bắt buộc.\n"
                 "Giọng nói sẽ được dùng để xác thực khi đăng nhập.",
            font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(0, 15))

        # ── Language Selection Frame ──────────────────────────────────────────
        lang_frame = ctk.CTkFrame(self, fg_color="transparent")
        lang_frame.pack(pady=10)

        ctk.CTkLabel(
            lang_frame,
            text="Chọn ngôn ngữ đăng ký:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(side="left", padx=10)

        self.lang_var = ctk.StringVar(value="vi")
        
        radio_vi = ctk.CTkRadioButton(
            lang_frame,
            text="🇻🇳 Tiếng Việt",
            variable=self.lang_var,
            value="vi",
            font=ctk.CTkFont(size=12),
            command=self._on_language_change
        )
        radio_vi.pack(side="left", padx=10)

        radio_en = ctk.CTkRadioButton(
            lang_frame,
            text="🇬🇧 English",
            variable=self.lang_var,
            value="en",
            font=ctk.CTkFont(size=12),
            command=self._on_language_change
        )
        radio_en.pack(side="left", padx=10)

        self.lang_info = ctk.CTkLabel(
            self,
            text="Sử dụng model: PhoWhisper (Tiếng Việt)",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.lang_info.pack(pady=5)

        # === NÚT GHI ÂM TOGGLE ===
        self.btn_record = ctk.CTkButton(
            self, 
            text="🎤 Bắt đầu ghi âm",
            width=300, 
            height=45, 
            fg_color="#d32f2f",
            command=self.toggle_recording
        )
        self.btn_record.pack(pady=15)

        # === Timer + Waveform ===
        self.timer_label = ctk.CTkLabel(self, text="00:00", font=ctk.CTkFont(size=16, weight="bold"))
        self.timer_label.pack(pady=2)

        self.wave_canvas = ctk.CTkCanvas(self, height=60, width=300, bg="#1a1a2e", highlightthickness=0)
        self.wave_canvas.pack(pady=8)

        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=13))
        self.status_label.pack(pady=8)

        self.btn_enroll = ctk.CTkButton(
            self, 
            text="✅ Lưu giọng nói",
            width=300, 
            height=45, 
            fg_color="green",
            state="disabled", 
            command=self.enroll,
        )
        self.btn_enroll.pack(pady=10)

        ctk.CTkButton(
            self, 
            text="Bỏ qua (không khuyến khích)", 
            fg_color="gray", 
            width=300,
            command=self._skip,
        ).pack(pady=10)

    # ==================== GHI ÂM TOGGLE ====================
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

            self.status_label.configure(text="✔ Ghi âm hoàn tất – nhấn Lưu để tiếp tục", text_color="green")
            self.btn_enroll.configure(state="normal")
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
                self.wave_canvas.create_line(x, 30-height, x, 30+height, fill="#00ff88", width=2)

        self.timer_id = self.after(50, self._update_timer_and_wave)

    def _reset_recording_ui(self):
        self.is_recording = False
        if self.timer_id:
            self.after_cancel(self.timer_id)
        self.btn_record.configure(text="🎤 Bắt đầu ghi âm", fg_color="#d32f2f")
        self.timer_label.configure(text="00:00")
        self.wave_canvas.delete("all")

    # ==================== GIỮ NGUYÊN PHẦN CÒN LẠI ====================
    def _on_language_change(self):
        self.selected_language = self.lang_var.get()
        
        if self.selected_language == "vi":
            model_info = "Sử dụng model: PhoWhisper (Tiếng Việt)"
            instruction = "Hãy nói một câu bất kỳ bằng tiếng Việt"
        else:
            model_info = "Sử dụng model: OpenAI Whisper (English)"
            instruction = "Please speak any sentence in English"
        
        self.lang_info.configure(text=model_info)
        
        if self.file_path:
            self._cleanup_audio()
            self.btn_enroll.configure(state="disabled")
            self.status_label.configure(
                text=f"⚠ Đã đổi ngôn ngữ - vui lòng ghi âm lại\n{instruction}",
                text_color="orange"
            )

    def tkraise(self, *args, **kwargs):
        self._cleanup_audio()
        self.lang_var.set("vi")
        self.selected_language = "vi"
        self._on_language_change()
        self.btn_enroll.configure(state="disabled", text="✅ Lưu giọng nói")
        self.status_label.configure(text="")
        self._reset_recording_ui()      # ← Reset waveform khi vào lại
        super().tkraise(*args, **kwargs)

    def enroll(self):
        if not self.file_path:
            warning_msg = "Vui lòng ghi âm trước!" if self.selected_language == "vi" else "Please record first!"
            messagebox.showwarning("Cảnh báo" if self.selected_language == "vi" else "Warning", warning_msg)
            return
            
        if not self.controller.current_user:
            error_msg = ("Không tìm thấy thông tin người dùng!\nVui lòng đăng ký lại." 
                        if self.selected_language == "vi" 
                        else "User information not found!\nPlease register again.")
            messagebox.showerror("Lỗi" if self.selected_language == "vi" else "Error", error_msg)
            self.controller.show_frame("RegisterView")
            return

        user_id = str(self.controller.current_user.get("id"))
        token = self.controller.token

        self.btn_enroll.configure(state="disabled", text="Đang lưu..." if self.selected_language == "vi" else "Saving...")
        uploading_msg = "Đang gửi lên server..." if self.selected_language == "vi" else "Uploading to server..."
        self.status_label.configure(text=uploading_msg, text_color="orange")
        self.update()

        try:
            enroll_voice(user_id, self.file_path, token, language=self.selected_language)
            self._cleanup_audio()

            if self.controller.current_user:
                self.controller.current_user["has_voice"] = True
                self.controller.current_user["voice_language"] = self.selected_language

            lang_name = "Tiếng Việt" if self.selected_language == "vi" else "English"
            
            if self.selected_language == "vi":
                success_msg = (
                    f"Đăng ký giọng nói thành công! ({lang_name})\n\n"
                    f"Từ lần sau, hãy ghi âm giọng nói bằng {lang_name} khi đăng nhập."
                )
                title = "Thành công!"
            else:
                success_msg = (
                    f"Voice registration successful! ({lang_name})\n\n"
                    f"Next time, please record your voice in {lang_name} when logging in."
                )
                title = "Success!"

            messagebox.showinfo(title, success_msg)
            self.controller.show_frame("HomeUserView")

        except Exception as e:
            error_title = "Lỗi" if self.selected_language == "vi" else "Error"
            error_msg = (f"Đăng ký giọng nói thất bại:\n{str(e)}" 
                        if self.selected_language == "vi" 
                        else f"Voice registration failed:\n{str(e)}")
            messagebox.showerror(error_title, error_msg)
            
            fail_msg = "Đăng ký thất bại - thử lại" if self.selected_language == "vi" else "Registration failed – try again"
            self.status_label.configure(text=fail_msg, text_color="red")
        finally:
            save_text = "✅ Lưu giọng nói" if self.selected_language == "vi" else "✅ Save voice"
            self.btn_enroll.configure(state="normal", text=save_text)

    def _skip(self):
        if self.selected_language == "vi":
            skip_msg = (
                "Bạn chưa đăng ký giọng nói.\n"
                "Tài khoản sẽ kém bảo mật hơn.\n\n"
                "Tiếp tục mà không đăng ký giọng nói?"
            )
            title = "Bỏ qua?"
        else:
            skip_msg = (
                "You haven't registered your voice.\n"
                "Your account will be less secure.\n\n"
                "Continue without voice registration?"
            )
            title = "Skip?"

        if messagebox.askyesno(title, skip_msg):
            self._cleanup_audio()
            self.controller.show_frame("HomeUserView")

    def _cleanup_audio(self):
        if self.file_path and os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
            except Exception:
                pass
        self.file_path = None