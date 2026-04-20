import customtkinter as ctk
from services.auth_api import register_user
from tkinter import messagebox

class RegisterView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ctk.CTkLabel(self, text="Đăng ký tài khoản", font=ctk.CTkFont(size=24)).pack(pady=30)

        self.full_name = ctk.CTkEntry(self, placeholder_text="Họ và tên", width=300)
        self.full_name.pack(pady=8)

        self.email = ctk.CTkEntry(self, placeholder_text="Email", width=300)
        self.email.pack(pady=8)

        self.password = ctk.CTkEntry(self, placeholder_text="Mật khẩu", show="*", width=300)
        self.password.pack(pady=8)

        ctk.CTkButton(self, text="Đăng ký", width=300, command=self.register).pack(pady=20)
        ctk.CTkButton(self, text="Quay lại", width=300, fg_color="gray",
                      command=lambda: controller.show_frame("HomeGuest")).pack()

    def register(self):
        try:
            data = register_user(self.email.get(), self.password.get(), self.full_name.get())
            messagebox.showinfo("Thành công", "Đăng ký thành công!\nVui lòng đăng ký giọng nói.")
            self.controller.show_frame("VoiceRegisterView")   # Chuyển sang đăng ký giọng nói
        except Exception as e:
            messagebox.showerror("Lỗi", f"Đăng ký thất bại: {str(e)}")