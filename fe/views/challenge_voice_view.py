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
        self.controller = controller
        self.file_path = None
        self.challenge_id = None
        self.user_language = "vi"
        self.fail_count = 0
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(self, text="🔐 Xác thực Bước 2", 
                    font=ctk.CTkFont(size=26, weight="bold")).pack(pady=20)

        self.lang_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=13, weight="bold"))
        self.lang_label.pack(pady=5)

        ctk.CTkLabel(self, text="Câu cần nói:", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=40, pady=(10,5))
        
        self.challenge_box = ctk.CTkTextbox(self, height=110, wrap="word", font=ctk.CTkFont(size=14))
        self.challenge_box.pack(pady=8, padx=30, fill="x")

        # Buttons Voice
        self.btn_get = ctk.CTkButton(self, text="📝 Lấy Challenge Mới", height=45, width=320,
                                   command=self.get_challenge)
        self.btn_get.pack(pady=12)

        self.btn_record = ctk.CTkButton(self, text="🎤 Ghi âm (5 giây)", height=50, width=320,
                                      fg_color="#d32f2f", state="disabled", command=self.start_recording)
        self.btn_record.pack(pady=8)

        self.btn_verify = ctk.CTkButton(self, text="✅ Xác thực Voice", height=50, width=320,
                                      fg_color="green", state="disabled", command=self.verify)
        self.btn_verify.pack(pady=8)

        # === 2ND KEY SECTION ===
        ctk.CTkLabel(self, text="─ Hoặc dùng Khóa phụ ─", text_color="gray", font=ctk.CTkFont(size=12)).pack(pady=10)

        self.pin_entry = ctk.CTkEntry(self, placeholder_text="Nhập PIN 6-8 số", width=320, show="*")
        self.pin_entry.pack(pady=5)

        self.btn_pin_verify = ctk.CTkButton(self, text="🔑 Xác thực bằng 2nd Key", height=45, width=320,
                                           fg_color="#8e24aa", command=self.verify_2ndkey)
        self.btn_pin_verify.pack(pady=8)

        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=13))
        self.status_label.pack(pady=15)

        ctk.CTkButton(self, text="← Huỷ & Quay lại", fg_color="gray", width=320,
                     command=self._cancel).pack(pady=10)

    def tkraise(self, *args, **kwargs):
        if self.controller.current_user:
            self.user_language = self.controller.current_user.get("voice_language", "vi")
            flag = "🇻🇳 Tiếng Việt" if self.user_language == "vi" else "🇬🇧 English"
            self.lang_label.configure(text=f"Ngôn ngữ: {flag}")

        self._reset()
        super().tkraise(*args, **kwargs)

    def _reset(self):
        self.challenge_id = None
        self.fail_count = 0
        self.challenge_box.delete("1.0", "end")
        self.challenge_box.insert("1.0", "Nhấn 'Lấy Challenge Mới' để bắt đầu...")
        self.btn_record.configure(state="disabled")
        self.btn_verify.configure(state="disabled")
        self.pin_entry.delete(0, "end")
        self.status_label.configure(text="")

    def _cancel(self):
        self.controller.current_user = None
        self.controller.token = None
        self._reset()
        self.controller.show_frame("LoginView")

    # ==================== GET CHALLENGE ====================
    def get_challenge(self):
        try:
            backend_url = getattr(self.controller, 'BACKEND_URL', "http://localhost:8000")
            resp = requests.get(
                f"{backend_url}/voice/challenge",
                params={"user_id": self.controller.current_user["id"], "language": self.user_language},
                headers={"Authorization": f"Bearer {self.controller.token}"},
                timeout=10
            )
            data = resp.json()

            self.challenge_id = data["challenge_id"]
            self.challenge_box.delete("1.0", "end")
            self.challenge_box.insert("1.0", data["challenge_text"])

            self.btn_record.configure(state="normal")
            self.status_label.configure(text="✅ Challenge sẵn sàng!", text_color="green")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không lấy được challenge:\n{str(e)}")

    # ==================== RECORDING ====================
    def start_recording(self):
        try:
            self.status_label.configure(text="🔴 Đang ghi âm... Đọc theo challenge", text_color="orange")
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
            messagebox.showerror("Lỗi", str(e))
            self.btn_record.configure(state="normal")

    # ==================== VOICE VERIFY ====================
    def verify(self):
        if not self.file_path or not self.challenge_id:
            messagebox.showwarning("Cảnh báo", "Chưa có file ghi âm!")
            return

        self.btn_verify.configure(state="disabled", text="Đang xác thực...")
        self.status_label.configure(text="Đang gửi lên server...", text_color="orange")
        self.update()

        try:
            with open(self.file_path, "rb") as f:
                files = {"file": ("challenge.wav", f, "audio/wav")}
                data = {"user_id": str(self.controller.current_user["id"]),
                        "challenge_id": self.challenge_id,
                        "language": self.user_language}

                resp = requests.post(
                    f"{self.controller.BACKEND_URL}/voice/verify-challenge",
                    files=files, data=data,
                    headers={"Authorization": f"Bearer {self.controller.token}"},
                    timeout=40
                )

            result = resp.json()

            if result.get("success"):
                messagebox.showinfo("Thành công", f"✅ Đăng nhập thành công!\nScore: {result.get('score', 0):.4f}")
                self.controller.login_success(self.controller.current_user, self.controller.token)
            else:
                self.fail_count += 1
                self.status_label.configure(text=f"❌ Thất bại lần {self.fail_count}/3", text_color="red")
                
                if self.fail_count >= 3:
                    messagebox.showwarning("Cảnh báo", "Đã thất bại 3 lần. Vui lòng dùng 2nd Key!")
                else:
                    messagebox.showerror("Thất bại", result.get("message", "Xác thực thất bại"))

        except Exception as e:
            messagebox.showerror("Lỗi", str(e))
        finally:
            self.btn_verify.configure(state="normal", text="✅ Xác thực Voice")
            self._cleanup_audio()

    # ==================== 2ND KEY VERIFY ====================
    def verify_2ndkey(self):
        pin = self.pin_entry.get().strip()
        if not pin or not pin.isdigit() or len(pin) < 6:
            messagebox.showwarning("Lỗi", "PIN phải là số và có ít nhất 6 chữ số!")
            return

        try:
            resp = requests.post(
                f"{self.controller.BACKEND_URL}/auth/verify-2ndkey",
                json={"pin": pin},
                headers={"Authorization": f"Bearer {self.controller.token}"},
                timeout=10
            )
            result = resp.json()

            if result.get("success"):
                messagebox.showinfo("Thành công", "✅ Xác thực 2nd Key thành công!")
                self.controller.login_success(self.controller.current_user, self.controller.token)
            else:
                messagebox.showerror("Thất bại", result.get("message", "PIN không đúng"))
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def _cleanup_audio(self):
        if self.file_path and os.path.exists(self.file_path):
            try: 
                os.remove(self.file_path)
            except:
                pass
        self.file_path = None