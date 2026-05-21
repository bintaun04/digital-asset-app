# views/challenge_voice_view.py
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
        self.controller = controller
        self.file_path = None
        self.challenge_id = None
        self.challenge_text = ""
        self.user_language = "vi"

        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text="🔐 Challenge Voice Authentication", 
                    font=ctk.CTkFont(size=26, weight="bold")).pack(pady=20)

        # Language Selection
        lang_frame = ctk.CTkFrame(self)
        lang_frame.pack(pady=8)

        ctk.CTkLabel(lang_frame, text="Ngôn ngữ:", font=ctk.CTkFont(size=14)).pack(side="left", padx=10)
        
        self.lang_var = ctk.StringVar(value="vi")
        ctk.CTkRadioButton(lang_frame, text="🇻🇳 Tiếng Việt", variable=self.lang_var, 
                          value="vi", command=self.change_language).pack(side="left", padx=10)
        ctk.CTkRadioButton(lang_frame, text="🇬🇧 English", variable=self.lang_var, 
                          value="en", command=self.change_language).pack(side="left", padx=10)

        # Challenge Box
        ctk.CTkLabel(self, text="Câu cần nói:", font=ctk.CTkFont(size=15)).pack(anchor="w", padx=40, pady=(15,5))
        
        self.challenge_box = ctk.CTkTextbox(self, height=120, wrap="word", font=ctk.CTkFont(size=14))
        self.challenge_box.pack(pady=8, padx=30, fill="x")

        # Buttons
        self.btn_get = ctk.CTkButton(self, text="📝 Lấy Challenge Mới", 
                                   height=45, width=320,
                                   command=self.get_challenge)
        self.btn_get.pack(pady=12)

        self.btn_record = ctk.CTkButton(self, text="🎤 Ghi âm (5 giây)", 
                                      height=50, width=320, fg_color="#d32f2f",
                                      state="disabled", command=self.start_recording)
        self.btn_record.pack(pady=8)

        self.btn_verify = ctk.CTkButton(self, text="✅ Xác thực Challenge", 
                                      height=50, width=320, fg_color="green",
                                      state="disabled", font=ctk.CTkFont(size=16, weight="bold"),
                                      command=self.verify)
        self.btn_verify.pack(pady=12)

        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=14))
        self.status_label.pack(pady=15)

        ctk.CTkButton(self, text="← Quay lại trang chủ", fg_color="gray", width=320,
                     command=lambda: self.controller.show_frame("HomeUserView")).pack(pady=20)

    def change_language(self):
        """Cập nhật ngôn ngữ khi người dùng chọn"""
        self.user_language = self.lang_var.get()
        self._reset_challenge()

    def _reset_challenge(self):
        self.challenge_id = None
        self.challenge_box.delete("1.0", "end")
        self.challenge_box.insert("1.0", "Nhấn 'Lấy Challenge Mới' để bắt đầu...")
        self.btn_record.configure(state="disabled")
        self.btn_verify.configure(state="disabled")

    def tkraise(self, *args, **kwargs):
        if self.controller.current_user:
            # Ưu tiên ngôn ngữ đã đăng ký của user
            registered_lang = self.controller.current_user.get("voice_language", "vi")
            self.lang_var.set(registered_lang)
            self.user_language = registered_lang
        self._reset_challenge()
        super().tkraise(*args, **kwargs)

    def get_challenge(self):
        if not self.controller.current_user:
            messagebox.showerror("Lỗi", "Bạn chưa đăng nhập!")
            return

        try:
            # Cách an toàn nhất - Lấy BACKEND_URL từ controller
            backend_url = getattr(self.controller, 'BACKEND_URL', "http://localhost:8000")

            resp = requests.get(
                f"{backend_url}/voice/challenge",
                params={
                    "user_id": self.controller.current_user["id"],
                    "language": self.user_language
                },
                headers={"Authorization": f"Bearer {self.controller.token}"},
                timeout=10
            )
            
            data = resp.json()

            self.challenge_id = data["challenge_id"]
            self.challenge_text = data["challenge_text"]

            self.challenge_box.delete("1.0", "end")
            self.challenge_box.insert("1.0", self.challenge_text)

            self.btn_record.configure(state="normal")
            self.status_label.configure(text="✅ Challenge đã sẵn sàng!", text_color="green")

        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lấy challenge:\n{str(e)}")
    def start_recording(self):
        try:
            self.status_label.configure(text="🔴 Đang ghi âm... Nói theo challenge", text_color="orange")
            self.btn_record.configure(state="disabled")
            self.update()

            fs = 16000
            recording = sd.rec(int(5 * fs), samplerate=fs, channels=1, dtype='int16')
            sd.wait()

            self.file_path = tempfile.mktemp(suffix=".wav")
            write(self.file_path, fs, recording)

            self.status_label.configure(text="✔ Ghi âm xong!", text_color="green")
            self.btn_verify.configure(state="normal")

        except Exception as e:
            messagebox.showerror("Lỗi ghi âm", str(e))
            self.btn_record.configure(state="normal")

    def verify(self):
        if not self.file_path or not self.challenge_id:
            messagebox.showwarning("Cảnh báo", "Chưa có challenge hoặc file ghi âm!")
            return

        user_id = str(self.controller.current_user.get("id"))

        self.btn_verify.configure(state="disabled", text="Đang xác thực...")
        self.status_label.configure(text="Đang gửi lên server...", text_color="orange")
        self.update()

        try:
            with open(self.file_path, "rb") as f:
                files = {"file": ("challenge.wav", f, "audio/wav")}
                data = {
                    "user_id": user_id,
                    "challenge_id": self.challenge_id,
                    "language": self.user_language
                }

                resp = requests.post(
                    f"{self.controller.BACKEND_URL}/voice/verify-challenge",
                    files=files,
                    data=data,
                    headers={"Authorization": f"Bearer {self.controller.token}"},
                    timeout=40
                )

            result = resp.json()

            if result.get("success"):
                messagebox.showinfo("Thành công", 
                    f"✅ Xác thực thành công!\nScore: {result.get('score', 0):.4f}")
                self.controller.show_frame("HomeUserView")
            else:
                messagebox.showerror("Thất bại", result.get("message", "Xác thực thất bại"))
                self.status_label.configure(text=f"❌ {result.get('message')}", text_color="red")

        except Exception as e:
            messagebox.showerror("Lỗi", f"Xảy ra lỗi:\n{str(e)}")
        finally:
            self.btn_verify.configure(state="normal", text="✅ Xác thực Challenge")
            self._cleanup_audio()

    def _cleanup_audio(self):
        if self.file_path and os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
            except:
                pass
        self.file_path = None