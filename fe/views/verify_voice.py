import customtkinter as ctk
import sounddevice as sd
from scipy.io.wavfile import write
import tempfile
import os
from tkinter import messagebox

from services.voice_api import verify_voice


class VerifyVoiceView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.recording = None
        self.file_path = None

        # Tiêu đề
        title = ctk.CTkLabel(self, text="Xác thực giọng nói", 
                            font=ctk.CTkFont(size=26, weight="bold"))
        title.pack(pady=40)

        ctk.CTkLabel(self, text="Nói rõ ràng một câu bất kỳ trong 5 giây\nđể xác thực danh tính",
                    font=ctk.CTkFont(size=14), text_color="gray").pack(pady=(0, 30))

        # Nút ghi âm
        self.btn_record = ctk.CTkButton(
            self,
            text="🎤 Bắt đầu ghi âm (5 giây)",
            width=320,
            height=50,
            font=ctk.CTkFont(size=16),
            command=self.start_recording
        )
        self.btn_record.pack(pady=20)

        # Nút xác thực (ban đầu disabled)
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

        # Trạng thái
        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=14))
        self.status_label.pack(pady=20)

        # Nút quay lại
        ctk.CTkButton(
            self,
            text="← Quay lại trang chủ",
            width=320,
            fg_color="gray",
            command=lambda: controller.show_frame("HomeUser")
        ).pack(pady=30)

    def start_recording(self):
        """Ghi âm 5 giây"""
        try:
            self.status_label.configure(text="Đang ghi âm... Hãy nói rõ ràng", text_color="orange")
            self.update()

            fs = 16000
            duration = 5

            self.recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
            sd.wait()  # Chờ ghi âm xong

            # Lưu file tạm
            self.file_path = tempfile.mktemp(suffix=".wav")
            write(self.file_path, fs, self.recording)

            self.status_label.configure(text="Ghi âm hoàn tất ✓", text_color="green")
            self.btn_verify.configure(state="normal")

            messagebox.showinfo("Hoàn tất", "Ghi âm đã xong!\nNhấn nút 'Xác thực giọng nói' để tiếp tục.")

        except Exception as e:
            messagebox.showerror("Lỗi ghi âm", f"Không thể ghi âm:\n{str(e)}")
            self.status_label.configure(text="Ghi âm thất bại", text_color="red")

    def verify(self):
        """Gọi API xác thực giọng nói"""
        if not self.file_path:
            messagebox.showwarning("Cảnh báo", "Chưa có file ghi âm!")
            return

        if not self.controller.current_user:
            messagebox.showerror("Lỗi", "Bạn chưa đăng nhập!")
            return

        user_id = self.controller.current_user.get("id")
        if not user_id:
            messagebox.showerror("Lỗi", "Không tìm thấy user_id")
            return

        try:
            self.status_label.configure(text="Đang xác thực...", text_color="orange")
            self.btn_verify.configure(state="disabled")
            self.update()

            # Gọi API verify
            result = verify_voice(
                user_id=user_id,
                file_path=self.file_path,
                token=self.controller.token
            )

            score = result.get("similarity_score", 0)
            is_verified = result.get("is_verified", False)

            if is_verified:
                self.status_label.configure(
                    text=f"✅ Xác thực thành công!\nĐiểm tương đồng: {score:.2f}",
                    text_color="green"
                )
                messagebox.showinfo("Thành công", 
                    f"Xác thực giọng nói thành công!\n\nĐiểm tương đồng: {score:.2f}")
                
                # Có thể chuyển về trang chủ hoặc mở tính năng khác
                self.controller.show_frame("HomeUser")
            else:
                self.status_label.configure(
                    text=f"❌ Xác thực thất bại\nĐiểm tương đồng: {score:.2f}",
                    text_color="red"
                )
                messagebox.showwarning("Thất bại", 
                    f"Xác thực giọng nói thất bại!\nĐiểm tương đồng: {score:.2f}\n\nVui lòng thử lại.")

        except Exception as e:
            error_msg = str(e)
            self.status_label.configure(text="Lỗi xác thực", text_color="red")
            messagebox.showerror("Lỗi", f"Xác thực thất bại:\n{error_msg}")

        finally:
            # Dọn dẹp file tạm
            if self.file_path and os.path.exists(self.file_path):
                try:
                    os.remove(self.file_path)
                except:
                    pass
            self.btn_verify.configure(state="normal")
