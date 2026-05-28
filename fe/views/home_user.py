# fe/views/home_user.py
import customtkinter as ctk


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
        user  = self.controller.current_user or {}
        email = user.get("email", "")
        lang  = user.get("voice_language", "vi")
        flag  = "🇻🇳" if lang == "vi" else "🇬🇧"

        ctk.CTkLabel(
            self, text="Trang chủ",
            font=ctk.CTkFont(size=26, weight="bold"),
        ).pack(pady=(55, 4))

        ctk.CTkLabel(
            self, text=f"Chào mừng, {email}",
            font=ctk.CTkFont(size=14), text_color="gray",
        ).pack()

        ctk.CTkLabel(
            self,
            text=f"{flag} {'Tiếng Việt' if lang == 'vi' else 'English'}",
            font=ctk.CTkFont(size=12), text_color="#4a9eff",
        ).pack(pady=(2, 36))

        ctk.CTkButton(
            self,
            text="🎙️ Voice Command Center",
            width=280, height=50,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#00695c", hover_color="#00796b",
            command=lambda: self.controller.show_frame("OutsideView"),
        ).pack(pady=8)

        ctk.CTkButton(
            self,
            text="📊 Lịch sử Insight giọng nói",
            width=280, height=46,
            font=ctk.CTkFont(size=14),
            fg_color="#1565c0", hover_color="#1976d2",
            command=lambda: self.controller.show_frame("InsightView"),
        ).pack(pady=8)

        ctk.CTkButton(
            self,
            text="Đăng xuất",
            width=280, height=42,
            fg_color="#c62828", hover_color="#b71c1c",
            command=self.controller.logout,
        ).pack(pady=8)