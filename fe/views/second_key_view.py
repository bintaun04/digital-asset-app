# fe/views/second_key_view.py
import customtkinter as ctk
from tkinter import messagebox
import requests


class SecondKeySetupView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(self, text="🔑 Thiết lập 2nd Key (PIN)", 
                    font=ctk.CTkFont(size=24, weight="bold")).pack(pady=30)

        ctk.CTkLabel(self, text="PIN chỉ gồm số, dài 6-8 ký tự", 
                    text_color="gray", font=ctk.CTkFont(size=13)).pack(pady=(0,20))

        self.pin_entry = ctk.CTkEntry(self, placeholder_text="Nhập PIN", width=300, show="*")
        self.pin_entry.pack(pady=8)

        self.confirm_entry = ctk.CTkEntry(self, placeholder_text="Xác nhận PIN lại", width=300, show="*")
        self.confirm_entry.pack(pady=8)

        self.enable_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(self, text="Bật sử dụng 2nd Key khi voice fail", 
                       variable=self.enable_var).pack(pady=15)

        ctk.CTkButton(self, text="💾 Lưu 2nd Key", height=50, width=300,
                     fg_color="#8e24aa", command=self.save_2ndkey).pack(pady=20)

        ctk.CTkButton(self, text="← Quay lại", width=300, fg_color="gray",
                     command=lambda: self.controller.show_frame("HomeUserView")).pack()

    def save_2ndkey(self):
        pin = self.pin_entry.get().strip()
        confirm = self.confirm_entry.get().strip()

        if not pin or not confirm:
            messagebox.showwarning("Lỗi", "Vui lòng nhập đầy đủ PIN!")
            return
        if pin != confirm:
            messagebox.showwarning("Lỗi", "PIN xác nhận không khớp!")
            return
        if not pin.isdigit() or not (6 <= len(pin) <= 8):
            messagebox.showwarning("Lỗi", "PIN phải là số và có độ dài 6-8 ký tự!")
            return

        try:
            backend = getattr(self.controller, "BACKEND_URL", "http://localhost:8000")
            resp = requests.post(
                f"{backend}/auth/setup-2ndkey",
                json={"pin": pin, "enable_2ndkey": self.enable_var.get()},
                headers={"Authorization": f"Bearer {self.controller.token}"},
                timeout=10
            )
            result = resp.json()

            if result.get("success"):
                messagebox.showinfo("Thành công", "✅ Đã thiết lập 2nd Key thành công!")
                self.controller.show_frame("HomeUserView")
            else:
                messagebox.showerror("Lỗi", result.get("message", "Không thể lưu"))
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể kết nối server:\n{str(e)}")