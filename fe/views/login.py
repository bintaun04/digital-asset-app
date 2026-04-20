import customtkinter as ctk
from services.auth_api import login_user
from tkinter import messagebox

class LoginView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ctk.CTkLabel(self, text="Đăng nhập", font=ctk.CTkFont(size=24)).pack(pady=40)

        self.email = ctk.CTkEntry(self, placeholder_text="Email", width=300)
        self.email.pack(pady=12)

        self.password = ctk.CTkEntry(self, placeholder_text="Mật khẩu", show="*", width=300)
        self.password.pack(pady=12)

        ctk.CTkButton(self, text="Đăng nhập", width=300, command=self.login).pack(pady=20)
        ctk.CTkButton(self, text="Quay lại", width=300, fg_color="gray",
                      command=lambda: controller.show_frame("HomeGuest")).pack()

    def login(self):
        try:
            data = login_user(self.email.get(), self.password.get())
            messagebox.showinfo("Thành công", "Đăng nhập thành công!")
            self.controller.login_success(data.get("user"), data.get("access_token"))
        except Exception as e:
            messagebox.showerror("Lỗi", f"Đăng nhập thất bại: {str(e)}") 
