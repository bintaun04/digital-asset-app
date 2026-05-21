# fe/views/insight_view.py
import customtkinter as ctk
from tkinter import messagebox
import requests


ACTION_LABELS = {
    "enroll":    ("📝 Enroll",    "#1565c0"),
    "verify":    ("🎤 Verify",    "#2e7d32"),
    "challenge": ("🔐 Challenge", "#6a1b9a"),
}

CONFIDENCE_COLORS = {
    "high":     "#2e7d32",
    "medium":   "#f9a825",
    "low":      "#e65100",
    "very_low": "#c62828",
}

QUALITY_COLORS = {
    "good": "#4caf50",
    "fair": "#ffb74d",
    "poor": "#ef5350",
}

QUALITY_LABELS = {
    "good": "🟢 Tốt",
    "fair": "🟡 TB",
    "poor": "🔴 Kém",
}


def _fmt(v, decimals=3, suffix="") -> str:
    if v is None:
        return "–"
    return f"{float(v):.{decimals}f}{suffix}"


class InsightView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._build_skeleton()

    # ── Skeleton ──────────────────────────────────────────────────────────────

    def _build_skeleton(self):
        ctk.CTkLabel(
            self, text="📊 Lịch sử xác thực giọng nói",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(pady=(20, 4))

        self.subtitle_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=12), text_color="gray",
        )
        self.subtitle_label.pack(pady=(0, 10))

        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=30, pady=(0, 10))

        self.scroll = ctk.CTkScrollableFrame(self, label_text="")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=4)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=12)

        ctk.CTkButton(
            btn_frame, text="🔄 Làm mới", width=140,
            command=self._load_data,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_frame, text="← Trang chủ", width=140, fg_color="gray",
            command=lambda: self.controller.show_frame("HomeUserView"),
        ).pack(side="left", padx=8)

    def tkraise(self, *args, **kwargs):
        super().tkraise(*args, **kwargs)
        self._load_data()

    # ── Load ──────────────────────────────────────────────────────────────────

    def _load_data(self):
        if not self.controller.current_user:
            messagebox.showerror("Lỗi", "Bạn chưa đăng nhập!")
            return

        self.subtitle_label.configure(text="Đang tải dữ liệu…")
        self._clear(self.stats_frame)
        self._clear(self.scroll)
        self.update()

        try:
            backend = getattr(self.controller, "BACKEND_URL", "http://localhost:8000")
            token   = self.controller.token
            uid     = self.controller.current_user["id"]
            headers = {"Authorization": f"Bearer {token}"}

            resp = requests.get(
                f"{backend}/voice/insights",
                params={"user_id": uid, "limit": 30},
                headers=headers, timeout=10,
            )
            resp.raise_for_status()
            body  = resp.json()
            items = body.get("insights", body) if isinstance(body, dict) else body

            stats = {}
            try:
                sr = requests.get(
                    f"{backend}/voice/insights/stats",
                    params={"user_id": uid},
                    headers=headers, timeout=10,
                )
                if sr.ok:
                    raw   = sr.json()
                    stats = raw.get("stats", raw) if isinstance(raw, dict) else raw
            except Exception:
                pass

            self._render_stats(stats)
            self._render_list(items)
            email = self.controller.current_user.get("email", "")
            self.subtitle_label.configure(text=f"{email} — {len(items)} bản ghi gần nhất")

        except requests.HTTPError as e:
            self.subtitle_label.configure(text=f"Lỗi HTTP {e.response.status_code}")
            messagebox.showerror("Lỗi", f"Server trả về lỗi:\n{e}")
        except Exception as e:
            self.subtitle_label.configure(text="Không thể tải dữ liệu")
            messagebox.showerror("Lỗi", f"Không thể tải insight:\n{e}")

    def _clear(self, frame):
        for w in frame.winfo_children():
            w.destroy()

    # ── Stats bar ─────────────────────────────────────────────────────────────

    def _render_stats(self, stats: dict):
        self._clear(self.stats_frame)
        if not stats or stats.get("total", 0) == 0:
            ctk.CTkLabel(self.stats_frame, text="Chưa có dữ liệu thống kê",
                         text_color="gray", font=ctk.CTkFont(size=12)).pack()
            return

        items = [
            ("Tổng",       str(stats.get("total", 0)),               "white"),
            ("Thành công", str(stats.get("success", 0)),              "#81c784"),
            ("Thất bại",   str(stats.get("failed", 0)),               "#e57373"),
            ("Tỉ lệ",      f"{stats.get('success_rate', 0)*100:.0f}%","#4fc3f7"),
            ("Score TB",   f"{stats.get('avg_score', 0):.3f}",        "#ffb74d"),
        ]
        for label, value, color in items:
            box = ctk.CTkFrame(self.stats_frame, corner_radius=8)
            box.pack(side="left", padx=6, pady=4)
            ctk.CTkLabel(box, text=value, font=ctk.CTkFont(size=18, weight="bold"),
                         text_color=color).pack(padx=14, pady=(6, 0))
            ctk.CTkLabel(box, text=label, font=ctk.CTkFont(size=11),
                         text_color="gray").pack(padx=14, pady=(0, 6))

    # ── List ──────────────────────────────────────────────────────────────────

    def _render_list(self, items: list):
        self._clear(self.scroll)
        if not items:
            ctk.CTkLabel(self.scroll, text="Chưa có lịch sử xác thực nào.",
                         font=ctk.CTkFont(size=14), text_color="gray").pack(pady=40)
            return
        for record in items:
            self._render_card(record)

    # ── Card ──────────────────────────────────────────────────────────────────

    def _render_card(self, r: dict):
        action   = r.get("action_type", "verify")
        is_ok    = r.get("is_match", False)
        score    = r.get("cosine_score") or 0.0
        mfcc     = r.get("mfcc_score")
        ge2e     = r.get("ge2e_score")
        conf     = r.get("confidence", "")
        lang     = r.get("language", "vi")
        text     = r.get("transcribed_text", "")
        gap      = r.get("gap_to_threshold")
        created  = (r.get("created_at", "")[:19].replace("T", " ")
                    if r.get("created_at") else "")

        # Acoustic
        duration  = r.get("duration_sec")
        pitch     = r.get("pitch_mean")
        pitch_std = r.get("pitch_std")
        spk_rate  = r.get("speaking_rate")
        snr       = r.get("snr_db")
        silence   = r.get("silence_ratio")
        quality   = r.get("voice_quality")

        action_label, action_color = ACTION_LABELS.get(action, ("❓", "gray"))
        status_text  = "✅ Thành công" if is_ok else "❌ Thất bại"
        status_color = "#81c784" if is_ok else "#e57373"
        conf_color   = CONFIDENCE_COLORS.get(conf, "gray")
        lang_flag    = "🇻🇳" if lang == "vi" else "🇬🇧"

        card = ctk.CTkFrame(self.scroll, corner_radius=10)
        card.pack(fill="x", padx=6, pady=5)

        # ── Row 1: action | status | confidence | time ────────────────────────
        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=(8, 2))

        ctk.CTkLabel(row1, text=action_label,
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=action_color).pack(side="left")
        ctk.CTkLabel(row1, text=f"  {status_text}",
                     font=ctk.CTkFont(size=13),
                     text_color=status_color).pack(side="left")
        ctk.CTkLabel(row1, text=f"  {lang_flag}",
                     font=ctk.CTkFont(size=12)).pack(side="left")
        if conf:
            ctk.CTkLabel(row1, text=f"  [{conf}]",
                         font=ctk.CTkFont(size=11),
                         text_color=conf_color).pack(side="left")
        ctk.CTkLabel(row1, text=created,
                     font=ctk.CTkFont(size=11),
                     text_color="gray").pack(side="right")

        # ── Row 2: embedding scores ────────────────────────────────────────────
        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=2)

        scores_txt = f"Score: {score:.4f}"
        if mfcc is not None:
            scores_txt += f"   MFCC: {mfcc:.4f}"
        if ge2e is not None:
            scores_txt += f"   GE2E: {ge2e:.4f}"

        ctk.CTkLabel(row2, text=scores_txt,
                     font=ctk.CTkFont(size=12),
                     text_color="#90caf9").pack(side="left")

        if gap is not None:
            gap_str   = f"+{gap:.4f}" if gap >= 0 else f"{gap:.4f}"
            gap_color = "#81c784" if gap >= 0 else "#e57373"
            ctk.CTkLabel(row2, text=f"Gap: {gap_str}",
                         font=ctk.CTkFont(size=12),
                         text_color=gap_color).pack(side="right")

        # ── Row 3: acoustic features ──────────────────────────────────────────
        has_acoustic = any(v is not None for v in [duration, pitch, snr, silence, spk_rate])
        if has_acoustic:
            row3 = ctk.CTkFrame(card, fg_color="#1a1a2e", corner_radius=6)
            row3.pack(fill="x", padx=12, pady=(2, 4))

            def _chip(parent, label, value, color="#aaaacc"):
                f = ctk.CTkFrame(parent, fg_color="transparent")
                f.pack(side="left", padx=8, pady=4)
                ctk.CTkLabel(f, text=label,
                             font=ctk.CTkFont(size=10), text_color="gray").pack()
                ctk.CTkLabel(f, text=value,
                             font=ctk.CTkFont(size=12, weight="bold"),
                             text_color=color).pack()

            if duration is not None:
                _chip(row3, "Dài", f"{duration:.1f}s", "#e0e0e0")
            if pitch is not None:
                _chip(row3, "Pitch", f"{pitch:.0f}Hz", "#ce93d8")
            if pitch_std is not None:
                _chip(row3, "±Pitch", f"{pitch_std:.0f}Hz", "#b39ddb")
            if spk_rate is not None:
                _chip(row3, "Tốc độ nói", f"{spk_rate:.1f}/s", "#80deea")
            if snr is not None:
                snr_color = "#4caf50" if snr >= 15 else "#ffb74d" if snr >= 8 else "#ef5350"
                _chip(row3, "SNR", f"{snr:.1f}dB", snr_color)
            if silence is not None:
                sil_pct   = silence * 100
                sil_color = "#4caf50" if sil_pct <= 30 else "#ffb74d" if sil_pct <= 50 else "#ef5350"
                _chip(row3, "Im lặng", f"{sil_pct:.0f}%", sil_color)
            if quality is not None:
                _chip(row3, "Chất lượng",
                      QUALITY_LABELS.get(quality, quality),
                      QUALITY_COLORS.get(quality, "gray"))

        # ── Row 4: STT text ────────────────────────────────────────────────────
        if text:
            row4 = ctk.CTkFrame(card, fg_color="transparent")
            row4.pack(fill="x", padx=12, pady=(2, 8))
            short = text if len(text) <= 80 else text[:77] + "…"
            ctk.CTkLabel(row4, text=f'💬 "{short}"',
                         font=ctk.CTkFont(size=11),
                         text_color="gray", anchor="w").pack(fill="x")
        else:
            card.pack_configure(pady=(5, 8))

        # Click để xem chi tiết
        for widget in [card] + card.winfo_children():
            widget.bind("<Button-1>", lambda e, d=r: self._show_detail(d))

    # ── Detail popup ──────────────────────────────────────────────────────────

    def _show_detail(self, r: dict):
        win = ctk.CTkToplevel(self)
        win.title("Chi tiết Insight")
        win.geometry("520x680")
        win.grab_set()

        is_ok  = r.get("is_match", False)
        action = r.get("action_type", "verify")
        score  = r.get("cosine_score") or 0.0
        thresh = r.get("threshold") or 0.75

        result_txt = "✅ XÁC THỰC THÀNH CÔNG" if is_ok else "❌ XÁC THỰC THẤT BẠI"
        result_col = "#4caf50" if is_ok else "#ef5350"
        action_label, action_color = ACTION_LABELS.get(action, ("❓", "gray"))

        ctk.CTkLabel(win, text=result_txt,
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=result_col).pack(pady=(20, 4))

        created = (r.get("created_at", "")[:19].replace("T", " ")
                   if r.get("created_at") else "")
        ctk.CTkLabel(win,
                     text=f"{action_label}  |  {created}",
                     font=ctk.CTkFont(size=12), text_color="gray").pack()

        scroll = ctk.CTkScrollableFrame(win)
        scroll.pack(fill="both", expand=True, padx=16, pady=10)

        def section(title):
            ctk.CTkLabel(scroll, text=title,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color="#90caf9").pack(anchor="w", pady=(12, 2))

        def row(label, value, color="white"):
            f = ctk.CTkFrame(scroll, fg_color="transparent")
            f.pack(fill="x", pady=1)
            ctk.CTkLabel(f, text=label, width=190,
                         font=ctk.CTkFont(size=12), text_color="gray",
                         anchor="w").pack(side="left")
            ctk.CTkLabel(f, text=str(value),
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=color, anchor="w").pack(side="left")

        # ── Embedding section ──────────────────────────────────────────────────
        section("🔬 So sánh Embedding")
        gap = r.get("gap_to_threshold")
        row("Score tổng (cosine):",
            _fmt(score, 4),
            "#4caf50" if score >= thresh else "#ef5350")
        row("MFCC score (vocal tract):",
            _fmt(r.get("mfcc_score"), 4), "#90caf9")
        row("GE2E score (voice identity):",
            _fmt(r.get("ge2e_score"), 4), "#ce93d8")
        row("Text similarity:",
            _fmt(r.get("text_similarity"), 4), "#fff176")
        row("Threshold:",           f"{thresh:.2f}")
        row("Gap to threshold:",
            f"{gap:+.4f}" if gap is not None else "–",
            "#4caf50" if (gap or 0) >= 0 else "#ef5350")
        row("Confidence:",
            r.get("confidence") or "–",
            CONFIDENCE_COLORS.get(r.get("confidence"), "gray"))
        row("Mode:",                r.get("mode") or "–")
        row("Embedding dim:",       str(r.get("embedding_dim") or "–"))

        # ── Acoustic section ───────────────────────────────────────────────────
        section("🎙️ Acoustic — Giọng vừa nói")

        quality = r.get("voice_quality")
        row("Chất lượng audio:",
            QUALITY_LABELS.get(quality, quality or "–"),
            QUALITY_COLORS.get(quality, "gray"))
        row("Độ dài audio:",
            _fmt(r.get("duration_sec"), 2, "s"), "#e0e0e0")
        row("SNR (Signal-to-Noise):",
            _fmt(r.get("snr_db"), 1, " dB"),
            "#4caf50" if (r.get("snr_db") or 0) >= 15
            else "#ffb74d" if (r.get("snr_db") or 0) >= 8
            else "#ef5350")
        row("Tỉ lệ im lặng:",
            _fmt((r.get("silence_ratio") or 0) * 100, 1, "%"),
            "#4caf50" if (r.get("silence_ratio") or 1) <= 0.30
            else "#ffb74d" if (r.get("silence_ratio") or 1) <= 0.50
            else "#ef5350")

        section("🎵 Đặc trưng giọng nói")
        pitch = r.get("pitch_mean")
        pstd  = r.get("pitch_std")
        pitch_txt = (f"{pitch:.0f} Hz (±{pstd:.0f})" if pitch and pstd
                     else _fmt(pitch, 0, " Hz"))
        row("Pitch trung bình (F0):", pitch_txt, "#ce93d8")
        row("Tốc độ nói:",
            _fmt(r.get("speaking_rate"), 2, " onset/s"), "#80deea")
        row("Năng lượng trung bình:", _fmt(r.get("energy_mean"), 5), "#ffcc80")
        row("Độ lệch năng lượng:",    _fmt(r.get("energy_std"),  5), "#ffcc80")

        # ── Interpretation hints ───────────────────────────────────────────────
        hints = _build_hints(r)
        if hints:
            section("💡 Gợi ý")
            for hint in hints:
                ctk.CTkLabel(scroll, text=f"• {hint}",
                             font=ctk.CTkFont(size=12),
                             text_color="#ffe082",
                             anchor="w", wraplength=460).pack(
                    anchor="w", pady=2, padx=4)

        # STT
        section("💬 Nội dung STT nhận được")
        stt_box = ctk.CTkTextbox(scroll, height=55, font=ctk.CTkFont(size=12))
        stt_box.pack(fill="x", pady=(2, 8))
        stt_box.insert("1.0", r.get("transcribed_text") or "(không có)")
        stt_box.configure(state="disabled")

        ctk.CTkButton(win, text="Đóng", command=win.destroy).pack(pady=8)


# ── Interpretation hints ──────────────────────────────────────────────────────

def _build_hints(r: dict) -> list[str]:
    hints = []

    score  = r.get("cosine_score") or 0.0
    thresh = r.get("threshold")    or 0.75
    snr    = r.get("snr_db")
    sil    = r.get("silence_ratio")
    dur    = r.get("duration_sec")
    spk    = r.get("speaking_rate")
    text_s = r.get("text_similarity")

    if not r.get("is_match"):
        if text_s is not None and text_s < 0.6:
            hints.append("Nội dung nói chưa khớp câu đăng ký — hãy đọc đúng câu gốc.")
        if score < thresh - 0.15:
            hints.append("Score cách xa ngưỡng — giọng nói khác biệt nhiều so với lúc đăng ký.")
        elif score < thresh:
            hints.append("Score gần ngưỡng — thử lại ở nơi yên tĩnh hơn hoặc nói rõ hơn.")

    if snr is not None and snr < 8:
        hints.append(f"SNR thấp ({snr:.1f} dB) — môi trường ồn, hãy thử lại ở nơi yên tĩnh hơn.")
    if sil is not None and sil > 0.5:
        hints.append(f"Tỉ lệ im lặng cao ({sil*100:.0f}%) — nói đủ dài và liên tục hơn.")
    if dur is not None and dur < 2.0:
        hints.append(f"Audio chỉ {dur:.1f}s — cần ít nhất 3–5 giây để nhận dạng chính xác.")
    if spk is not None and spk < 1.5:
        hints.append("Tốc độ nói chậm — hãy nói với tốc độ bình thường.")
    if spk is not None and spk > 8:
        hints.append("Tốc độ nói nhanh — hãy nói chậm và rõ ràng hơn.")

    return hints