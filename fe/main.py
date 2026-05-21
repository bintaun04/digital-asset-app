# fe/main.py
import customtkinter as ctk

from views.home_guest import HomeGuest
from views.home_user import HomeUserView
from views.login import LoginView
from views.register import RegisterView
from views.verify_voice import VerifyVoiceView
from views.voice_register import VoiceRegisterView
from views.challenge_voice_view import ChallengeVoiceView
from views.insight_view import InsightView

class App(ctk.CTk):
    BACKEND_URL = "http://localhost:8000"     # Class attribute

    def __init__(self):
        super().__init__()
        self.title("Digital Asset App - Voice Biometric")
        self.geometry("500x680")
        self.resizable(False, False)

        self.current_user = None
        self.token = None



        # Container chứa tất cả frame
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Khởi tạo tất cả frame
        self.frames = {}
        frame_classes = {
            "HomeGuest":        HomeGuest,
            "HomeUserView":     HomeUserView,
            "LoginView":        LoginView,
            "RegisterView":     RegisterView,
            "VerifyVoiceView":  VerifyVoiceView,
            "VoiceRegisterView": VoiceRegisterView,
            "ChallengeVoiceView": ChallengeVoiceView,
            "InsightView":         InsightView,
        }

        for name, FrameClass in frame_classes.items():
            try:
                frame = FrameClass(self.container, self)
                self.frames[name] = frame
                frame.grid(row=0, column=0, sticky="nsew")
                print(f"✅ Loaded: {name}")
            except Exception as e:
                print(f"❌ FAILED {name}: {e}")
        self.show_frame("HomeGuest")

    def show_frame(self, name: str):
        """Hiển thị frame theo tên"""
        frame = self.frames.get(name)
        if frame:
            frame.tkraise()
        else:
            print(f"[WARN] Không tìm thấy frame: {name}")

    def login_success(self, user: dict, token: str):
        """Gọi sau khi đăng nhập thành công"""
        self.current_user = user
        self.token = token
        self.show_frame("HomeUserView")

    def logout(self):
        """Đăng xuất - xóa trạng thái và về trang chủ guest"""
        self.current_user = None
        self.token = None
        self.show_frame("HomeGuest")


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()