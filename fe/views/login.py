# fe/views/login.py
import customtkinter as ctk
from tkinter import messagebox
from services.auth_api import login_user


class LoginView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ctk.CTkLabel(
            self, text="Đăng nhập",
            font=ctk.CTkFont(size=26, weight="bold"),
        ).pack(pady=(50, 6))

        ctk.CTkLabel(
            self,
            text="Bước 1 / 2 — Xác thực mật khẩu",
            font=ctk.CTkFont(size=12), text_color="gray",
        ).pack(pady=(0, 30))

        self.email = ctk.CTkEntry(self, placeholder_text="Email", width=300)
        self.email.pack(pady=8)

        self.password = ctk.CTkEntry(
            self, placeholder_text="Mật khẩu", show="*", width=300,
        )
        self.password.pack(pady=8)
        # Nhấn Enter ở ô password cũng login luôn
        self.password.bind("<Return>", lambda _: self.login())

        self.btn_login = ctk.CTkButton(
            self, text="Tiếp tục →", width=300, height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.login,
        )
        self.btn_login.pack(pady=22)

        ctk.CTkButton(
            self, text="← Quay lại", width=300, fg_color="gray",
            command=lambda: controller.show_frame("HomeGuest"),
        ).pack()

    def tkraise(self, *args, **kwargs):
        self.email.delete(0, "end")
        self.password.delete(0, "end")
        super().tkraise(*args, **kwargs)

    def login(self):
        email    = self.email.get().strip()
        password = self.password.get()

        if not email or not password:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập email và mật khẩu!")
            return

        self.btn_login.configure(state="disabled", text="Đang xác thực…")
        self.update()

        try:
            # Gọi /auth/login-no-voice — chỉ password, không audio
            data  = login_user(email, password, voice_file_path=None)
            user  = data.get("user", {})
            token = data.get("access_token")

            # Lưu tạm vào controller, chưa gọi login_success
            self.controller.current_user = user
            self.controller.token        = token

            if not user.get("has_voice", False):
                messagebox.showinfo(
                    "Chưa đăng ký giọng nói",
                    "Tài khoản chưa có giọng nói.\n"
                    "Vui lòng đăng ký để tiếp tục.",
                )
                self.controller.show_frame("VoiceRegisterView")
            else:
                # Có giọng nói → bước 2: Challenge
                self.controller.show_frame("ChallengeVoiceView")

        except Exception as e:
            err = str(e)
            if "401" in err:
                messagebox.showerror("Sai thông tin", "Email hoặc mật khẩu không đúng!")
            else:
                messagebox.showerror("Lỗi", f"Đăng nhập thất bại:\n{err}")
        finally:
            self.btn_login.configure(state="normal", text="Tiếp tục →")