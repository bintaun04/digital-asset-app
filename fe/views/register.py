# fe/views/register.py
import customtkinter as ctk
from tkinter import messagebox
from services.auth_api import register_user

class RegisterView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ctk.CTkLabel(self, text="Đăng ký tài khoản",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(pady=30)

        self.full_name = ctk.CTkEntry(self, placeholder_text="Họ và tên", width=300)
        self.full_name.pack(pady=8)

        self.email = ctk.CTkEntry(self, placeholder_text="Email", width=300)
        self.email.pack(pady=8)

        self.password = ctk.CTkEntry(self, placeholder_text="Mật khẩu (tối thiểu 6 ký tự)",
                                     show="*", width=300)
        self.password.pack(pady=8)

        self.btn_register = ctk.CTkButton(self, text="Đăng ký", width=300, command=self.register)
        self.btn_register.pack(pady=20)

        ctk.CTkButton(self, text="Quay lại", width=300, fg_color="gray",
                      command=lambda: controller.show_frame("HomeGuest")).pack()

    def register(self):
        full_name = self.full_name.get().strip()
        email = self.email.get().strip()
        password = self.password.get()

        if not email or not password:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập đầy đủ email và mật khẩu!")
            return

        if len(password) < 6:
            messagebox.showwarning("Cảnh báo", "Mật khẩu phải có ít nhất 6 ký tự!")
            return

        self.btn_register.configure(state="disabled", text="Đang đăng ký...")
        self.update()

        try:
            data = register_user(email, password, full_name)

            # ✅ Lưu user + token vào controller ngay sau đăng ký
            self.controller.current_user = data.get("user")
            self.controller.token = data.get("access_token")

            messagebox.showinfo("Thành công",
                                "Đăng ký thành công!\nBây giờ hãy đăng ký giọng nói của bạn.")
            self.controller.show_frame("VoiceRegisterView")

        except Exception as e:
            error = str(e)
            if "400" in error:
                messagebox.showerror("Lỗi", "Email này đã được đăng ký!")
            else:
                messagebox.showerror("Lỗi", f"Đăng ký thất bại:\n{error}")
        finally:
            self.btn_register.configure(state="normal", text="Đăng ký")