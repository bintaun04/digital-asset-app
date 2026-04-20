import customtkinter as ctk
import sounddevice as sd
from scipy.io.wavfile import write
from services.voice_api import enroll_voice
from tkinter import messagebox
import tempfile
import os

class VoiceRegisterView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.recording = None
        self.file_path = None

        ctk.CTkLabel(self, text="Đăng ký giọng nói", font=ctk.CTkFont(size=24)).pack(pady=30)
        ctk.CTkLabel(self, text="Nói rõ ràng một câu bất kỳ trong 5 giây").pack(pady=10)

        self.btn_record = ctk.CTkButton(self, text="🎤 Bắt đầu ghi âm", width=300, command=self.start_record)
        self.btn_record.pack(pady=20)

        self.btn_upload = ctk.CTkButton(self, text="Đăng ký giọng nói", width=300, state="disabled", command=self.enroll)
        self.btn_upload.pack(pady=10)

        ctk.CTkButton(self, text="Quay lại", fg_color="gray", command=lambda: controller.show_frame("HomeGuest")).pack(pady=30)

    def start_record(self):
        try:
            fs = 16000
            duration = 5
            self.recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
            sd.wait()

            # Lưu tạm
            self.file_path = tempfile.mktemp(suffix=".wav")
            write(self.file_path, fs, self.recording)

            self.btn_upload.configure(state="normal")
            messagebox.showinfo("Hoàn tất", "Ghi âm xong! Nhấn nút Đăng ký giọng nói.")
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def enroll(self):
        if not self.file_path or not self.controller.current_user:
            messagebox.showwarning("Cảnh báo", "Vui lòng đăng nhập và ghi âm trước")
            return

        try:
            result = enroll_voice(self.controller.current_user["id"], self.file_path)
            messagebox.showinfo("Thành công", "Đăng ký giọng nói thành công!")
            self.controller.show_frame("HomeUser")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Đăng ký giọng nói thất bại: {str(e)}")
        finally:
            if os.path.exists(self.file_path):
                os.remove(self.file_path) 
