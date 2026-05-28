# fe/main.py
import customtkinter as ctk

from views.home_guest           import HomeGuest
from views.home_user            import HomeUserView
from views.login                import LoginView
from views.register             import RegisterView
from views.voice_register       import VoiceRegisterView
from views.challenge_voice_view import ChallengeVoiceView
from views.insight_view         import InsightView
from views.outside_view         import OutsideView

try:
    from views.verify_voice import VerifyVoiceView
    _HAS_VERIFY = True
except Exception:
    _HAS_VERIFY = False
    
_AUTH_FRAMES = {"HomeUserView", "InsightView", "OutsideView",
                "ChallengeVoiceView", "VoiceRegisterView"}


class App(ctk.CTk):
    BACKEND_URL = "http://localhost:8000"

    def __init__(self):
        super().__init__()
        self.title("Digital Asset App - Voice Biometric")
        self.geometry("500x680")
        self.resizable(False, False)

        self.current_user = None
        self.token        = None

        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        frame_classes = {
            "HomeGuest":          HomeGuest,
            "HomeUserView":       HomeUserView,
            "LoginView":          LoginView,
            "RegisterView":       RegisterView,
            "VoiceRegisterView":  VoiceRegisterView,
            "ChallengeVoiceView": ChallengeVoiceView,
            "InsightView":        InsightView,
            "OutsideView":        OutsideView,
        }
        if _HAS_VERIFY:
            frame_classes["VerifyVoiceView"] = VerifyVoiceView

        self.frames = {}
        for name, FrameClass in frame_classes.items():
            try:
                frame = FrameClass(self.container, self)
                self.frames[name] = frame
                frame.grid(row=0, column=0, sticky="nsew")
                print(f"✅ Frame: {name}")
            except Exception as e:
                print(f"❌ Frame FAILED '{name}': {e}")

        self._current_frame_name = None
        self.show_frame("HomeGuest")

    # ── Navigation ────────────────────────────────────────────────────────────

    def show_frame(self, name: str):
        frame = self.frames.get(name)
        if not frame:
            print(f"[WARN] Không tìm thấy frame: {name}")
            return

        # Dừng mic ở frame cũ nếu là OutsideView
        old = self.frames.get(self._current_frame_name)
        if old and hasattr(old, "on_hide"):
            old.on_hide()

        self._current_frame_name = name
        frame.tkraise()

    def login_success(self, user: dict, token: str):
        self.current_user = user
        self.token        = token
        self.show_frame("HomeUserView")

    def logout(self):
        # Dừng mic nếu đang ở OutsideView
        ov = self.frames.get("OutsideView")
        if ov and hasattr(ov, "_stop_mic"):
            ov._stop_mic()
        self.current_user = None
        self.token        = None
        self.show_frame("HomeGuest")


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()