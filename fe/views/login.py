# fe/views/login.py
import customtkinter as ctk
from tkinter import messagebox
from services.auth_api import login_user

class LoginView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ctk.CTkLabel(self, text="Đăng nhập",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(pady=40)

        self.email = ctk.CTkEntry(self, placeholder_text="Email", width=300)
        self.email.pack(pady=12)

        self.password = ctk.CTkEntry(self, placeholder_text="Mật khẩu", show="*", width=300)
        self.password.pack(pady=12)

        self.btn_login = ctk.CTkButton(self, text="Đăng nhập", width=300, command=self.login)
        self.btn_login.pack(pady=20)

        ctk.CTkButton(self, text="Quay lại", width=300, fg_color="gray",
                      command=lambda: controller.show_frame("HomeGuest")).pack()

    def login(self):
        email = self.email.get().strip()
        password = self.password.get()

        if not email or not password:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập đầy đủ email và mật khẩu!")
            return

        self.btn_login.configure(state="disabled", text="Đang đăng nhập...")
        self.update()

        try:
            data = login_user(email, password)
            self.password.delete(0, "end")  # Xóa mật khẩu khỏi ô nhập
            self.controller.login_success(data.get("user"), data.get("access_token"))
        except Exception as e:
            error = str(e)
            if "401" in error:
                messagebox.showerror("Lỗi", "Email hoặc mật khẩu không đúng!")
            else:
                messagebox.showerror("Lỗi", f"Đăng nhập thất bại:\n{error}")
        finally:
            self.btn_login.configure(state="normal", text="Đăng nhập")