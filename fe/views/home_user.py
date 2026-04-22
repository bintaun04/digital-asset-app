# fe/views/home_user.py
import customtkinter as ctk
from tkinter import messagebox

class HomeUserView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

    def tkraise(self, *args, **kwargs):
        # Làm mới label chào mừng mỗi khi frame được hiển thị
        for widget in self.winfo_children():
            widget.destroy()
        self._build()
        super().tkraise(*args, **kwargs)

    def _build(self):
        email = self.controller.current_user.get("email", "") if self.controller.current_user else ""

        ctk.CTkLabel(self, text="Trang chủ",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(pady=40)
        ctk.CTkLabel(self, text=f"Chào mừng, {email}",
                     font=ctk.CTkFont(size=14)).pack(pady=5)

        ctk.CTkButton(self, text="🎤 Xác thực giọng nói", width=250,
                      command=lambda: self.controller.show_frame("VerifyVoiceView")).pack(pady=15)
        ctk.CTkButton(self, text="Đăng xuất", width=250, fg_color="red",
                      command=self.controller.logout).pack(pady=10)