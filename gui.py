import customtkinter as ctk
import json
import threading
import webbrowser
import urllib.parse
import sounddevice as sd
from datetime import datetime
from pathlib import Path
from audio import record_audio, SAMPLE_RATE
from API_audd import (
    recognize_from_audio as recognize_audd,
    format_result as format_audd_result,
    is_configured as is_audd_configured,
)
import math
from PIL import Image




BG_ROOT      = "#12121E"   
BG_CARD      = "#1A1A2E"   
BG_CARD2     = "#16162A"   
BG_FIELD     = "#0F0F1E"   
ACCENT       = "#7C3AED"   
ACCENT_HOVER = "#6D28D9"
ACCENT_LIGHT = "#A78BFA"   
ACCENT_GLOW  = "#5B21B6"
RED          = "#DC2626"
RED_HOVER    = "#B91C1C"
SPOTIFY      = "#1DB954"
SPOTIFY_HOVER= "#17A349"
GRAY_BTN     = "#2D2D45"
GRAY_HOVER   = "#3A3A55"
TEXT_PRIMARY = "#F0EEFF"
TEXT_MUTED   = "#7B7B9E"
BORDER       = "#2A2A40"
ASSETS_DIR   = Path(__file__).with_name("assets")
HISTORY_FILE = Path(__file__).with_name("history.json")
MAX_HISTORY  = 50


def _load_icon(filename: str, size: tuple[int, int]) -> ctk.CTkImage:
    image = Image.open(ASSETS_DIR / filename).convert("RGBA")
    return ctk.CTkImage(light_image=image, dark_image=image, size=size)


class AnimatedBars(ctk.CTkCanvas):

    BAR_COUNT = 5
    BAR_W     = 6
    BAR_GAP   = 5
    HEIGHT    = 36

    def __init__(self, master, **kw):
        total_w = self.BAR_COUNT * self.BAR_W + (self.BAR_COUNT - 1) * self.BAR_GAP
        super().__init__(
            master,
            width=total_w,
            height=self.HEIGHT,
            bg=BG_CARD,
            highlightthickness=0,
            **kw,
        )
        self._running  = False
        self._frame    = 0
        self._bar_ids  = []
        self._draw_idle()

    def _draw_idle(self):
        self.delete("all")
        cx = (self.BAR_COUNT * self.BAR_W + (self.BAR_COUNT - 1) * self.BAR_GAP) / 2
        for i in range(self.BAR_COUNT):
            x0 = i * (self.BAR_W + self.BAR_GAP)
            x1 = x0 + self.BAR_W
            h  = 8
            y0 = (self.HEIGHT - h) // 2
            y1 = y0 + h
            self.create_rectangle(x0, y0, x1, y1, fill=TEXT_MUTED, outline="", width=0)

    def _animate(self):
        if not self._running:
            return
        self.delete("all")
        self._frame += 1
        for i in range(self.BAR_COUNT):
            phase = self._frame / 6 + i * 0.8
            h     = int(10 + 14 * abs(math.sin(phase)))
            x0    = i * (self.BAR_W + self.BAR_GAP)
            x1    = x0 + self.BAR_W
            y0    = (self.HEIGHT - h) // 2
            y1    = y0 + h
            color = ACCENT_LIGHT if i % 2 == 0 else ACCENT
            self.create_rectangle(x0, y0, x1, y1, fill=color, outline="", width=0)
        self.after(60, self._animate)

    def start(self):
        if not self._running:
            self._running = True
            self._animate()

    def stop(self):
        self._running = False
        self._draw_idle()


class MusicRecognizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")

        self.title("Music Recognizer")
        self.geometry("440x720")
        self.minsize(420, 620)
        self.resizable(True, True)
        self.configure(fg_color=BG_ROOT)

        self.devices       = sd.query_devices()
        self.input_devices = [
            f"{i}: {d['name']}"
            for i, d in enumerate(self.devices)
            if d["max_input_channels"] > 0
        ]

        self._youtube_query = ""
        self.history = self.load_history()
        self.history_sidebar_visible = False
        self.history_sidebar = None
        self.history_list = None
        self.history_count_label = None
        self._build_ui()

    def _build_ui(self):
        card = ctk.CTkFrame(
            self,
            fg_color=BG_CARD,
            corner_radius=28,
        )
        card.pack(side="left", fill="both", expand=True, padx=18, pady=22)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(24, 4))

        ctk.CTkLabel(
            header,
            text="♪",
            font=("Georgia", 22),
            text_color=ACCENT_LIGHT,
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text="Music Recognizer",
            font=("Georgia", 20, "bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left", padx=(8, 0))

        self._dot = ctk.CTkLabel(
            header, text="●", font=("Arial", 10), text_color=TEXT_MUTED
        )
        self._dot.pack(side="right")

        ctk.CTkFrame(card, height=1, fg_color=BORDER).pack(
            fill="x", padx=24, pady=(12, 0)
        )

        bars_row = ctk.CTkFrame(card, fg_color="transparent")
        bars_row.pack(pady=(20, 4))

        self._bars = AnimatedBars(bars_row)
        self._bars.pack(side="left", padx=(0, 12))

        self._status_label = ctk.CTkLabel(
            bars_row,
            text="Pronto para ouvir",
            font=("Courier New", 13),
            text_color=TEXT_MUTED,
        )
        self._status_label.pack(side="left")

        self.btn_recognize = ctk.CTkButton(
            card,
            text="  Ouvir Música",
            font=("Georgia", 15, "bold"),
            height=54,
            corner_radius=16,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT_PRIMARY,
            command=self.start_recognition_thread,
        )
        self.btn_recognize.pack(fill="x", padx=24, pady=(16, 6))

        self.btn_stop = ctk.CTkButton(
            card,
            text="  Parar Gravação",
            font=("Courier New", 13),
            height=40,
            corner_radius=12,
            fg_color=GRAY_BTN,
            hover_color=RED_HOVER,
            text_color=TEXT_MUTED,
            state="disabled",
            command=self.stop_recognition,
        )
        self.btn_stop.pack(fill="x", padx=24, pady=(0, 14))
        ctk.CTkFrame(card, height=1, fg_color=BORDER).pack(fill="x", padx=24)
        ctk.CTkLabel(
            card,
            text="MICROFONE",
            font=("Courier New", 10, "bold"),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=28, pady=(16, 4))

        self.device_selector = ctk.CTkComboBox(
            card,
            values=self.input_devices,
            height=38,
            corner_radius=12,
            fg_color=BG_FIELD,
            border_color=BORDER,
            border_width=1,
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            dropdown_fg_color=BG_CARD2,
            dropdown_hover_color=GRAY_BTN,
            text_color=TEXT_PRIMARY,
            dropdown_text_color=TEXT_PRIMARY,
            font=("Courier New", 12),
        )
        self.device_selector.pack(fill="x", padx=24)
        if self.input_devices:
            self.device_selector.set(self.input_devices[0])
        self.device_selector._entry.configure(state="readonly", cursor="arrow")

        ctk.CTkFrame(card, height=1, fg_color=BORDER).pack(
            fill="x", padx=24, pady=(16, 0)
        )


        ctk.CTkLabel(
            card,
            text="RESULTADO",
            font=("Courier New", 10, "bold"),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=28, pady=(16, 4))

        self.result_box = ctk.CTkTextbox(
            card,
            height=120,
            corner_radius=14,
            fg_color=BG_FIELD,
            border_color=BORDER,
            border_width=1,
            text_color=TEXT_PRIMARY,
            font=("Courier New", 13),
            scrollbar_button_color=ACCENT,
            scrollbar_button_hover_color=ACCENT_HOVER,
        )
        self.result_box.pack(fill="both", expand=True, padx=24)
        self.result_box.insert("0.0", "O resultado aparecerá aqui...")
        self.result_box.configure(state="disabled")

        #botão de limpar
        self.btn_clear = ctk.CTkButton(
            card,
            text="Limpar",
            font=("Courier New", 12),
            height=36,
            corner_radius=10,
            fg_color=GRAY_BTN,
            hover_color=GRAY_HOVER,
            text_color=TEXT_MUTED,
            command=self.clear_results,
        )
        self.btn_clear.pack(fill="x", padx=24, pady=(10, 6))

        #botões do yt e do spotify
        stream_row = ctk.CTkFrame(card, fg_color="transparent")
        stream_row.pack(fill="x", padx=24, pady=(0, 24))

        self._icon_yt      = _load_icon("youtube.png", (34, 24))
        self._icon_spotify = _load_icon("spotify.png", (28, 28))

        self.btn_youtube = ctk.CTkButton(
            stream_row,
            text="",
            image=self._icon_yt,
            width=60,
            height=44,
            corner_radius=12,
            fg_color=BG_FIELD,
            hover_color="#CC0000",
            border_color=BORDER,
            border_width=1,
            state="disabled",
            command=self.open_youtube,
        )
        self.btn_youtube.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_spotify = ctk.CTkButton(
            stream_row,
            text="",
            image=self._icon_spotify,
            width=60,
            height=44,
            corner_radius=12,
            fg_color=BG_FIELD,
            hover_color=SPOTIFY_HOVER,
            border_color=BORDER,
            border_width=1,
            state="disabled",
            command=self.open_spotify,
        )
        self.btn_spotify.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_history = ctk.CTkButton(
            stream_row,
            text="Historico",
            font=("Courier New", 11, "bold"),
            width=86,
            height=44,
            corner_radius=12,
            fg_color=BG_FIELD,
            hover_color=GRAY_HOVER,
            border_color=BORDER,
            border_width=1,
            text_color=TEXT_PRIMARY,
            command=self.toggle_history_sidebar,
        )
        self.btn_history.pack(side="left", fill="x", expand=True)
        self._build_history_sidebar()

    def open_youtube(self):
        if self._youtube_query:
            url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(self._youtube_query)
            webbrowser.open(url)

    def open_spotify(self):
        if self._youtube_query:
            url = "https://open.spotify.com/search/" + urllib.parse.quote(self._youtube_query)
            webbrowser.open(url)

    def load_history(self):
        if not HISTORY_FILE.exists():
            return []

        try:
            with HISTORY_FILE.open("r", encoding="utf-8") as file:
                history = json.load(file)
        except (OSError, json.JSONDecodeError):
            return []

        if not isinstance(history, list):
            return []
        return [entry for entry in history if isinstance(entry, dict)][:MAX_HISTORY]

    def save_history(self):
        with HISTORY_FILE.open("w", encoding="utf-8") as file:
            json.dump(self.history[:MAX_HISTORY], file, ensure_ascii=False, indent=2)

    def render_history(self):
        if not self.history_list or not self.history_list.winfo_exists():
            return

        if self.history_count_label and self.history_count_label.winfo_exists():
            total = len(self.history)
            suffix = "musica salva" if total == 1 else "musicas salvas"
            self.history_count_label.configure(text=f"{total} {suffix}")

        for child in self.history_list.winfo_children():
            child.destroy()

        if not self.history:
            empty_card = ctk.CTkFrame(
                self.history_list,
                fg_color=BG_FIELD,
                border_color=BORDER,
                border_width=1,
                corner_radius=12,
            )
            empty_card.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(
                empty_card,
                text="Nenhuma música reconhecida ainda.",
                font=("Courier New", 12),
                text_color=TEXT_MUTED,
                wraplength=230,
                justify="left",
            ).pack(anchor="w", padx=14, pady=16)
            return

        for index, entry in enumerate(self.history, 1):
            title = entry.get("title") or "Desconhecido"
            artist = entry.get("artist") or "Desconhecido"
            album = entry.get("album") or ""
            when = entry.get("when") or ""
            provider = entry.get("provider") or "AudD"

            card = ctk.CTkFrame(
                self.history_list,
                fg_color=BG_FIELD,
                border_color=BORDER,
                border_width=1,
                corner_radius=12,
            )
            card.pack(fill="x", pady=(0, 10))

            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=12, pady=(10, 0))

            ctk.CTkLabel(
                top,
                text=f"{index:02d}",
                width=32,
                height=28,
                corner_radius=9,
                fg_color=ACCENT,
                font=("Courier New", 11, "bold"),
                text_color=TEXT_PRIMARY,
            ).pack(side="left", padx=(0, 10))

            title_group = ctk.CTkFrame(top, fg_color="transparent")
            title_group.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                title_group,
                text=title,
                font=("Georgia", 15, "bold"),
                text_color=TEXT_PRIMARY,
                anchor="w",
                wraplength=190,
                justify="left",
            ).pack(anchor="w")

            ctk.CTkLabel(
                title_group,
                text=artist,
                font=("Courier New", 11),
                text_color=ACCENT_LIGHT,
                anchor="w",
                wraplength=190,
                justify="left",
            ).pack(anchor="w", pady=(2, 0))

            if album:
                ctk.CTkLabel(
                    card,
                    text=album,
                    font=("Courier New", 10),
                    text_color=TEXT_MUTED,
                    anchor="w",
                    wraplength=230,
                    justify="left",
                ).pack(anchor="w", padx=54, pady=(6, 0))

            meta = ctk.CTkFrame(card, fg_color="transparent")
            meta.pack(fill="x", padx=12, pady=(10, 12))

            ctk.CTkLabel(
                meta,
                text=when,
                font=("Courier New", 10),
                text_color=TEXT_MUTED,
            ).pack(side="left")

            ctk.CTkLabel(
                meta,
                text=provider,
                font=("Courier New", 10, "bold"),
                text_color=TEXT_PRIMARY,
                fg_color=GRAY_BTN,
                corner_radius=8,
                padx=8,
                pady=2,
            ).pack(side="right")

    def open_history_file(self):
        if not HISTORY_FILE.exists():
            self.save_history()
        webbrowser.open(HISTORY_FILE.as_uri())

    def _build_history_sidebar(self):
        self.history_sidebar = ctk.CTkFrame(
            self,
            width=300,
            fg_color=BG_CARD,
            corner_radius=18,
        )
        self.history_sidebar.pack_propagate(False)

        ctk.CTkLabel(
            self.history_sidebar,
            text="Historico",
            font=("Georgia", 18, "bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=18, pady=(16, 4))

        self.history_count_label = ctk.CTkLabel(
            self.history_sidebar,
            text=f"{len(self.history)} musicas salvas",
            font=("Courier New", 10),
            text_color=TEXT_MUTED,
            wraplength=260,
        )
        self.history_count_label.pack(anchor="w", padx=18, pady=(0, 10))

        actions = ctk.CTkFrame(self.history_sidebar, fg_color="transparent")
        actions.pack(fill="x", padx=18, pady=(0, 10))

        ctk.CTkButton(
            actions,
            text="Abrir JSON",
            font=("Courier New", 11, "bold"),
            height=32,
            corner_radius=10,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT_PRIMARY,
            command=self.open_history_file,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            actions,
            text="Limpar",
            font=("Courier New", 11),
            height=32,
            corner_radius=10,
            fg_color=GRAY_BTN,
            hover_color=GRAY_HOVER,
            text_color=TEXT_MUTED,
            command=self.clear_history,
        ).pack(side="left", fill="x", expand=True)

        self.history_list = ctk.CTkScrollableFrame(
            self.history_sidebar,
            corner_radius=14,
            fg_color=BG_FIELD,
            border_color=BORDER,
            border_width=1,
            scrollbar_button_color=ACCENT,
            scrollbar_button_hover_color=ACCENT_HOVER,
        )
        self.history_list.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.render_history()

    def toggle_history_sidebar(self):
        if not self.history_sidebar:
            return

        if self.history_sidebar_visible:
            self.history_sidebar.pack_forget()
            self.history_sidebar_visible = False
            self.minsize(420, 620)
            self.btn_history.configure(text="Historico")
            return

        self.history_sidebar.pack(side="right", fill="y", padx=(0, 18), pady=22)
        self.history_sidebar_visible = True
        self.minsize(720, 620)
        if self.winfo_width() < 720:
            self.geometry(f"760x{max(self.winfo_height(), 720)}")
        self.btn_history.configure(text="Fechar")
        self.render_history()

    def add_history_entry(self, result: dict):
        title = str(result.get("title") or "").strip()
        artist = str(result.get("artist") or "").strip()

        if not title or title == "Desconhecido":
            return

        entry = {
            "when": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "provider": str(result.get("provider") or "AudD"),
            "title": title,
            "artist": artist or "Desconhecido",
            "album": str(result.get("album") or ""),
            "query": " ".join(
                part for part in (title, artist, str(result.get("album") or "")) if part
            ),
        }

        self.history.insert(0, entry)
        self.history = self.history[:MAX_HISTORY]
        self.save_history()
        self.render_history()

    def clear_history(self):
        self.history = []
        try:
            if HISTORY_FILE.exists():
                HISTORY_FILE.unlink()
        except OSError:
            self.save_history()
        self.render_history()

    def _set_dot(self, color: str):
        self._dot.configure(text_color=color)

    def update_status(self, text: str):
        self._status_label.configure(text=text)

    def clear_results(self):
        self.result_box.configure(state="normal")
        self.result_box.delete("0.0", "end")
        self.result_box.insert("0.0", "O resultado aparecerá aqui...")
        self.result_box.configure(state="disabled")
        self._youtube_query = ""
        self.btn_youtube.configure(
            state="disabled",
            fg_color=BG_FIELD,
            border_color=BORDER,
            text_color=TEXT_MUTED,
        )
        self.btn_spotify.configure(
            state="disabled",
            fg_color=BG_FIELD,
            border_color=BORDER,
            text_color=TEXT_MUTED,
        )

    def start_recognition_thread(self):
        self.btn_recognize.configure(state="disabled")
        self.btn_stop.configure(
            state="normal",
            fg_color=RED,
            text_color=TEXT_PRIMARY,
        )
        self.update_status("Ouvindo...")
        self._set_dot(ACCENT_LIGHT)
        self._bars.start()
        thread = threading.Thread(target=self.run_recognition, daemon=True)
        thread.start()

    def run_recognition(self):
        self.result_box.configure(state="normal")
        self.result_box.delete("0.0", "end")
        try:
            selection  = self.device_selector.get()
            device_id  = int(selection.split(":")[0]) if selection else None

            audio = record_audio(device=device_id)

            result = None
            result_lines = []

            if is_audd_configured():
                self.update_status("Identificando com AudD...")
                result = recognize_audd(audio, sample_rate=SAMPLE_RATE)
                audd_text = format_audd_result(result)

                if isinstance(result, dict) and result.get("ok"):
                    raw_text = audd_text
                else:
                    result_lines.append(audd_text)
                    raw_text = "\n\n".join(result_lines)
            else:
                result_lines.append("AudD: configure AUDD_API_TOKEN=test no .env para usar o teste.")
                raw_text = "\n\n".join(result_lines)

            if not isinstance(result, dict) or not result.get("ok"):
                raw_text = f"{raw_text}\n\nMúsica não reconhecida."

            #remove linhas repetidas
            seen, unique_lines = set(), []
            for line in (raw_text or "").splitlines():
                key = line.strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    unique_lines.append(line)
            clean_text = "\n".join(unique_lines)

            self.result_box.delete("0.0", "end")
            self.result_box.insert("0.0", clean_text if clean_text else "Música não reconhecida.")

            #query do yt e spotify
            query_parts = []
            if isinstance(result, dict) and result.get("ok"):
                for key in ("title", "artist", "album"):
                    val = result.get(key) or ""
                    if val:
                        query_parts.append(str(val).strip())

            self._youtube_query = " ".join(query_parts)
            if self._youtube_query:
                self.add_history_entry(result)
                self.btn_youtube.configure(
                    state="normal",
                    fg_color=BG_FIELD,
                    border_color="#FF0000",
                    text_color=TEXT_PRIMARY,
                )
                self.btn_spotify.configure(
                    state="normal",
                    fg_color=BG_FIELD,
                    border_color=SPOTIFY,
                    text_color=TEXT_PRIMARY,
                )

        except Exception as e:
            self.result_box.delete("0.0", "end")
            self.result_box.insert("0.0", f"Erro: {e}")

        finally:
            self.result_box.configure(state="disabled")
            self._bars.stop()
            self.update_status("Pronto")
            self._set_dot(TEXT_MUTED)
            self.btn_recognize.configure(state="normal")
            self.btn_stop.configure(
                state="disabled",
                fg_color=GRAY_BTN,
                text_color=TEXT_MUTED,
            )

    def stop_recognition(self):
        sd.stop()
        self._bars.stop()
        self.update_status("Gravação interrompida.")
        self._set_dot(RED)
        self.btn_recognize.configure(state="normal")
        self.btn_stop.configure(
            state="disabled",
            fg_color=GRAY_BTN,
            text_color=TEXT_MUTED,
        )

    def on_closing(self):
        self.destroy()
if __name__ == "__main__":
    app = MusicRecognizerApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
