import customtkinter as ctk
from tkinter import messagebox

class HomeUserView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ctk.CTkLabel(self, text="Trang chủ", font=ctk.CTkFont(size=24)).pack(pady=40)
        ctk.CTkLabel(self, text=f"Chào mừng, {controller.current_user.get('email', '') if controller.current_user else ''}").pack()

        ctk.CTkButton(self, text="Xác thực giọng nói", width=250, command=lambda: controller.show_frame("VerifyVoice")).pack(pady=15)
        ctk.CTkButton(self, text="Đăng xuất", width=250, fg_color="red", command=controller.logout).pack(pady=10) 
