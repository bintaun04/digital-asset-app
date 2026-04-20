import sys
import os
import customtkinter as ctk

from views.home_guest import HomeGuest
from views.login import LoginView
from views.register import RegisterView
from views.voice_register import VoiceRegisterView
from views.home_user import HomeUserView
from views.verify_voice import VerifyVoiceView


# ==================== HỖ TRỢ CHẠY .EXE ====================
def resource_path(relative_path):
    """
    Hỗ trợ đường dẫn khi:
    - chạy Python bình thường
    - chạy file .exe sau khi build bằng PyInstaller
    """
    try:
        base_path = sys._MEIPASS  # PyInstaller temp folder
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# Ví dụ dùng logo nếu cần
LOGO_PATH = resource_path("assets/images/logo.png")


# ==================== CẤU HÌNH GIAO DIỆN ====================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ==================== APP CHÍNH ====================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Digital Asset App")
        self.geometry("900x650")
        self.minsize(900, 650)

        # dữ liệu user sau login
        self.current_user = None
        self.token = None

        # container chứa các frame
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}

        self.create_frames()
        self.show_frame("HomeGuest")

    def create_frames(self):
        """
        Tạo toàn bộ giao diện
        """
        pages = (
            HomeGuest,
            LoginView,
            RegisterView,
            VoiceRegisterView,
            HomeUserView,
            VerifyVoiceView,
        )

        for Page in pages:
            frame = Page(parent=self.container, controller=self)
            self.frames[Page.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

    def show_frame(self, page_name):
        """
        Hiển thị frame theo tên class
        """
        frame = self.frames.get(page_name)
        if frame:
            frame.tkraise()

    def login_success(self, user_data, token):
        """
        Gọi sau khi đăng nhập thành công
        """
        self.current_user = user_data
        self.token = token

        # cập nhật giao diện nếu cần
        home_user = self.frames.get("HomeUserView")
        if home_user and hasattr(home_user, "refresh_user_info"):
            home_user.refresh_user_info()

        self.show_frame("HomeUserView")

    def logout(self):
        """
        Đăng xuất
        """
        self.current_user = None
        self.token = None
        self.show_frame("HomeGuest")


# ==================== RUN APP ====================
if __name__ == "__main__":
    app = App()
    app.mainloop()