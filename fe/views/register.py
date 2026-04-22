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

        ctk.CTkLabel(self, text="Sau khi đăng ký, bạn sẽ được yêu cầu\nđăng ký giọng nói để bảo mật tài khoản",
                     font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(0, 15))

        self.full_name = ctk.CTkEntry(self, placeholder_text="Họ và tên", width=300)
        self.full_name.pack(pady=8)

        self.email = ctk.CTkEntry(self, placeholder_text="Email", width=300)
        self.email.pack(pady=8)

        self.password = ctk.CTkEntry(
            self, placeholder_text="Mật khẩu (tối thiểu 6 ký tự)",
            show="*", width=300,
        )
        self.password.pack(pady=8)

        self.btn_register = ctk.CTkButton(
            self, text="Đăng ký", width=300, height=42, command=self.register,
        )
        self.btn_register.pack(pady=20)

        ctk.CTkButton(self, text="← Quay lại", width=300, fg_color="gray",
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

            # ✅ Lưu user + token ngay sau register (không cần login lại)
            self.controller.current_user = data.get("user")
            self.controller.token = data.get("access_token")

            # Xóa form
            self.full_name.delete(0, "end")
            self.email.delete(0, "end")
            self.password.delete(0, "end")

            messagebox.showinfo(
                "Đăng ký thành công!",
                f"Chào mừng {full_name or email}!\n\n"
                "Bước tiếp theo: Đăng ký giọng nói\n"
                "để bảo mật tài khoản của bạn.",
            )
            # ✅ Chuyển thẳng sang enroll giọng nói
            self.controller.show_frame("VoiceRegisterView")

        except Exception as e:
            error = str(e)
            if "400" in error:
                messagebox.showerror("Lỗi", "Email này đã được đăng ký!")
            elif "422" in error:
                messagebox.showerror("Lỗi", "Email không hợp lệ!")
            else:
                messagebox.showerror("Lỗi", f"Đăng ký thất bại:\n{error}")
        finally:
            self.btn_register.configure(state="normal", text="Đăng ký")