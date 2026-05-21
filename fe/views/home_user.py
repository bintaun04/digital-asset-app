# fe/views/home_user.py
import customtkinter as ctk
from tkinter import messagebox


class HomeUserView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

    def tkraise(self, *args, **kwargs):
        for widget in self.winfo_children():
            widget.destroy()
        self._build()
        super().tkraise(*args, **kwargs)

    def _build(self):
        email = (
            self.controller.current_user.get("email", "")
            if self.controller.current_user
            else ""
        )

        ctk.CTkLabel(
            self, text="Trang chủ",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(pady=40)

        ctk.CTkLabel(
            self, text=f"Chào mừng, {email}",
            font=ctk.CTkFont(size=14),
        ).pack(pady=5)

        ctk.CTkButton(
            self, text="🎤 Xác thực giọng nói", width=280,
            command=lambda: self.controller.show_frame("VerifyVoiceView"),
        ).pack(pady=12)

        ctk.CTkButton(
            self, text="🔐 Xác thực Challenge Voice",
            width=280, height=46,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#7B1FA2", hover_color="#9C27B0",
            command=lambda: self.controller.show_frame("ChallengeVoiceView"),
        ).pack(pady=8)

        ctk.CTkButton(
            self, text="📊 Xem lịch sử insight giọng nói",
            width=280, height=42,
            fg_color="#1565c0", hover_color="#1976d2",
            command=lambda: self.controller.show_frame("InsightView"),
        ).pack(pady=8)

        ctk.CTkButton(
            self, text="Đăng xuất", width=280, fg_color="red",
            command=self.controller.logout,
        ).pack(pady=14)