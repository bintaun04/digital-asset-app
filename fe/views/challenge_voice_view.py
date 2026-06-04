# fe/views/challenge_voice_view.py
import customtkinter as ctk
from tkinter import messagebox
import sounddevice as sd
from scipy.io.wavfile import write
import tempfile
import os
import numpy as np
import time
import requests
import pygame

class ChallengeVoiceView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.file_path = None
        self.challenge_id = None
        self.user_language = "vi"
        self.fail_count = 0

        pygame.mixer.init()
        # Recording vars
        self.is_recording = False
        self.recording_frames = []
        self.stream = None
        self.start_time = None
        self.timer_id = None

        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(self, text=" Xác thực Bước 2", 
                    font=ctk.CTkFont(size=26, weight="bold")).pack(pady=20)

        self.lang_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=13, weight="bold"))
        self.lang_label.pack(pady=5)

        ctk.CTkLabel(self, text="Câu cần nói:", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=40, pady=(10,5))
        
        self.challenge_box = ctk.CTkTextbox(self, height=100, wrap="word", font=ctk.CTkFont(size=14))
        self.challenge_box.pack(pady=8, padx=30, fill="x")

        self.btn_get = ctk.CTkButton(self, text=" Lấy Challenge Mới", height=45, width=320,
                                   command=self.get_challenge)
        self.btn_get.pack(pady=12)

        # Toggle Record Button
        self.btn_record = ctk.CTkButton(self, text=" Bắt đầu ghi âm", height=50, width=320,
                                      fg_color="#d32f2f", command=self.toggle_recording)
        self.btn_record.pack(pady=8)

        # Timer + Waveform
        self.timer_label = ctk.CTkLabel(self, text="00:00", font=ctk.CTkFont(size=16, weight="bold"))
        self.timer_label.pack(pady=2)

        self.wave_canvas = ctk.CTkCanvas(self, height=60, width=300, bg="#1a1a2e", highlightthickness=0)
        self.wave_canvas.pack(pady=5)
        #replay button
        self.btn_play = ctk.CTkButton(self, text=" Nghe lại ghi âm", height=40, width=320,
                                    fg_color="#1976d2", state="disabled", command=self.play_audio)
        self.btn_play.pack(pady=5)

        self.btn_verify = ctk.CTkButton(self, text="✅ Xác thực Voice", height=50, width=320,
                                      fg_color="green", state="disabled", command=self.verify)
        self.btn_verify.pack(pady=10)
        # 2ND KEY SECTION
        ctk.CTkLabel(self, text="─ Hoặc dùng Khóa phụ ─", text_color="gray", font=ctk.CTkFont(size=12)).pack(pady=10)
        self.pin_entry = ctk.CTkEntry(self, placeholder_text="Nhập PIN 6-8 số", width=320, show="*")
        self.pin_entry.pack(pady=5)
        self.btn_pin_verify = ctk.CTkButton(self, text=" Xác thực bằng 2nd Key", height=45, width=320,
                                           fg_color="#8e24aa", command=self.verify_2ndkey)
        self.btn_pin_verify.pack(pady=8)

        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=13))
        self.status_label.pack(pady=15)

        ctk.CTkButton(self, text="← Huỷ & Quay lại", fg_color="gray", width=320,
                     command=self._cancel).pack(pady=10)

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

            def callback(indata, frames, time_info, status):
                if status: print(status)
                self.recording_frames.append(indata.copy())

            self.stream = sd.InputStream(samplerate=16000, channels=1, dtype='int16', callback=callback)
            self.stream.start()

            self._update_timer_wave()
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))
            self._reset_recording_ui()
    def play_audio(self):
        if not self.file_path or not os.path.exists(self.file_path):
            messagebox.showwarning("Lỗi", "Không tìm thấy file ghi âm!")
            return
        try:
            pygame.mixer.music.load(self.file_path)
            pygame.mixer.music.play()
        except Exception as e:
            messagebox.showerror("Lỗi phát âm thanh", str(e))
    def stop_recording(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if self.recording_frames:
            recording = np.concatenate(self.recording_frames, axis=0)
            self.file_path = tempfile.mktemp(suffix=".wav")
            write(self.file_path, 16000, recording)
            self.status_label.configure(text=" Ghi âm xong!", text_color="green")
            self.btn_verify.configure(state="normal")
            self.btn_play.configure(state="normal")
        else:
            self.status_label.configure(text="Không có dữ liệu", text_color="red")

        self._reset_recording_ui()

    def _update_timer_wave(self):
        if not self.is_recording:
            return
        elapsed = int(time.time() - self.start_time)
        self.timer_label.configure(text=f"{elapsed//60:02d}:{elapsed%60:02d}")

        self.wave_canvas.delete("all")
        if self.recording_frames:
            data = self.recording_frames[-1].flatten()[:300]
            for i, val in enumerate(data[::4]):
                height = int(abs(val) / 400)
                x = i * 4
                self.wave_canvas.create_line(x, 30-height, x, 30+height, fill="#00ff88", width=2)

        self.timer_id = self.after(50, self._update_timer_wave)

    def _reset_recording_ui(self):
        self.is_recording = False
        if hasattr(self, 'timer_id') and self.timer_id:
            self.after_cancel(self.timer_id)
        self.btn_record.configure(text=" Bắt đầu ghi âm", fg_color="#d32f2f")
        self.timer_label.configure(text="00:00")
        self.wave_canvas.delete("all")

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
        self.btn_record.configure(state="normal")
        self.btn_verify.configure(state="disabled")
        self.btn_play.configure(state="disabled")
        self.pin_entry.delete(0, "end")
        self.status_label.configure(text="")
        self._reset_recording_ui()

    def _cancel(self):
        self._reset_recording_ui()
        pygame.mixer.music.stop()
        self.controller.current_user = None
        self.controller.token = None
        self.controller.show_frame("LoginView")

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
            self.status_label.configure(text=" Challenge sẵn sàng!", text_color="green")
            self.btn_record.configure(state="normal")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không lấy được challenge:\n{str(e)}")

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
                messagebox.showinfo("Thành công", f" Đăng nhập thành công!\nScore: {result.get('score', 0):.4f}")
                self.controller.login_success(self.controller.current_user, self.controller.token)
            else:
                self.fail_count += 1
                self.status_label.configure(text=f" Thất bại lần {self.fail_count}/3", text_color="red")
                if self.fail_count >= 3:
                    messagebox.showwarning("Cảnh báo", "Đã thất bại 3 lần. Vui lòng dùng 2nd Key!")
                else:
                    messagebox.showerror("Thất bại", result.get("message", "Xác thực thất bại"))
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))
        finally:
            self.btn_verify.configure(state="normal", text=" Xác thực Voice")
            self._cleanup_audio()

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
                messagebox.showinfo("Thành công", " Xác thực 2nd Key thành công!")
                self.controller.login_success(self.controller.current_user, self.controller.token)
            else:
                messagebox.showerror("Thất bại", "PIN không đúng")
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def _cleanup_audio(self):
        if self.file_path and os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
            except:
                pass
        self.file_path = None