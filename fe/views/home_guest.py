import customtkinter as ctk

class HomeGuest(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ctk.CTkLabel(self, text="Digital Asset App", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=80)
        ctk.CTkLabel(self, text="Bảo mật bằng giọng nói", font=ctk.CTkFont(size=16)).pack(pady=10)

        ctk.CTkButton(self, text="Đăng nhập", width=220, height=40,
                      command=lambda: controller.show_frame("LoginView")).pack(pady=15)

        ctk.CTkButton(self, text="Đăng ký tài khoản", width=220, height=40,
                      command=lambda: controller.show_frame("RegisterView")).pack(pady=10) 
