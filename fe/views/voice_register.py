# fe/views/voice_register.py
import customtkinter as ctk
import sounddevice as sd
from scipy.io.wavfile import write
from tkinter import messagebox
import tempfile
import os

from services.voice_api import enroll_voice

class VoiceRegisterView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.recording = None
        self.file_path = None

        ctk.CTkLabel(self, text="Đăng ký giọng nói",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(pady=30)
        ctk.CTkLabel(self, text="Nói rõ ràng một câu bất kỳ trong 5 giây",
                     font=ctk.CTkFont(size=13), text_color="gray").pack(pady=5)

        self.btn_record = ctk.CTkButton(self, text="🎤 Bắt đầu ghi âm (5 giây)",
                                        width=300, height=45, command=self.start_record)
        self.btn_record.pack(pady=20)

        self.btn_enroll = ctk.CTkButton(self, text="✅ Đăng ký giọng nói",
                                        width=300, height=45, fg_color="green",
                                        state="disabled", command=self.enroll)
        self.btn_enroll.pack(pady=10)

        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=13))
        self.status_label.pack(pady=15)

        ctk.CTkButton(self, text="Quay lại", fg_color="gray", width=300,
                      command=lambda: controller.show_frame("HomeGuest")).pack(pady=10)

    def start_record(self):
        try:
            self.status_label.configure(text="🔴 Đang ghi âm... Hãy nói rõ ràng",
                                        text_color="orange")
            self.btn_record.configure(state="disabled")
            self.update()

            fs = 16000
            self.recording = sd.rec(int(5 * fs), samplerate=fs, channels=1, dtype='float32')
            sd.wait()

            self.file_path = tempfile.mktemp(suffix=".wav")
            write(self.file_path, fs, self.recording)

            self.status_label.configure(text="✔ Ghi âm hoàn tất", text_color="green")
            self.btn_enroll.configure(state="normal")
            messagebox.showinfo("Hoàn tất", "Ghi âm xong!\nNhấn 'Đăng ký giọng nói' để tiếp tục.")

        except Exception as e:
            messagebox.showerror("Lỗi ghi âm", str(e))
            self.status_label.configure(text="Ghi âm thất bại", text_color="red")
        finally:
            self.btn_record.configure(state="normal")

    def enroll(self):
        if not self.file_path:
            messagebox.showwarning("Cảnh báo", "Vui lòng ghi âm trước!")
            return

        if not self.controller.current_user:
            messagebox.showerror("Lỗi", "Không tìm thấy thông tin người dùng!")
            return

        user_id = str(self.controller.current_user.get("id"))
        token = self.controller.token

        self.btn_enroll.configure(state="disabled", text="Đang đăng ký...")
        self.status_label.configure(text="Đang gửi lên server...", text_color="orange")
        self.update()

        try:
            enroll_voice(user_id, self.file_path, token)  # ✅ truyền token
            messagebox.showinfo("Thành công", "Đăng ký giọng nói thành công!\nBạn có thể đăng nhập bằng giọng nói.")
            self.controller.show_frame("HomeUserView")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Đăng ký giọng nói thất bại:\n{str(e)}")
            self.status_label.configure(text="Đăng ký thất bại", text_color="red")
        finally:
            self.btn_enroll.configure(state="normal", text="✅ Đăng ký giọng nói")
            if self.file_path and os.path.exists(self.file_path):
                try:
                    os.remove(self.file_path)
                except:
                    pass
            self.file_path = None