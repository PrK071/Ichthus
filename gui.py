import customtkinter as ctk
import io
import json
import re
import tkinter as tk
import tkinter.font as tkfont
import threading
import webbrowser
import urllib.parse
import requests
import sounddevice as sd
from datetime import datetime
from pathlib import Path
from audio import record_audio, SAMPLE_RATE
from API_shazam import (
    recognize_from_audio as recognize_shazam,
    format_result as format_shazam_result,
)
import math
from PIL import Image, ImageOps, ImageTk




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
CORRECTIONS_FILE = Path(__file__).with_name("corrections.json")
REPORTS_FILE = Path(__file__).with_name("correction_reports.json")
MAX_HISTORY  = 50
COVER_SIZE   = 72
COVER_CARD_HEIGHT = 92
HISTORY_THUMB_SIZE = 52
FONT_FAMILY  = "Segoe UI"
DEFAULT_CORRECTIONS = [
    {
        "match": {
            "artist": "Spacetoon TV",
            "contains": ["gaara"],
        },
        "replace": {
            "title": "Gaara",
            "artist": "7 Minutoz",
            "album": "",
        },
        "note": "Correcao local conhecida para esta faixa.",
    }
]
#aqui ele só muda o idioma msm
LANGUAGE_ORDER = ("pt", "en")
UI_TEXT = {
    "pt": {
        "language_button": "EN",
        "ready_to_listen": "Pronto para ouvir",
        "ready": "Pronto",
        "listening": "Ouvindo...",
        "identifying_shazam": "Identificando...",
        "recording_stopped": "Gravação interrompida.",
        "listen_music": "Ouvir Música",
        "stop_recording": "Parar Gravação",
        "microphone": "MICROFONE",
        "result": "RESULTADO",
        "placeholder": "O resultado aparecerá aqui...",
        "clear": "Limpar",
        "clear_result": "Limpar resultado",
        "clear_history": "Limpar histórico",
        "history_cleared": "Histórico limpo.",
        "history": "Histórico",
        "close": "Fechar",
        "open_json": "Abrir JSON",
        "history_count_one": "música salva",
        "history_count_many": "músicas salvas",
        "no_history": "Nenhuma música reconhecida ainda.",
        "unknown": "Desconhecido",
        "report": "Reportar",
        "report_saved": "Report salvo.",
        "report_hint": "Adicione uma regra em corrections.json se este resultado tiver artista/título errado.",
        "local_correction": "Correção local aplicada por corrections.json.",
        "no_music": "Música não reconhecida.",
        "error_prefix": "Erro",
    },
    "en": {
        "language_button": "PT",
        "ready_to_listen": "Ready to listen",
        "ready": "Ready",
        "listening": "Listening...",
        "identifying_shazam": "Identifying...",
        "recording_stopped": "Recording stopped.",
        "listen_music": "Listen",
        "stop_recording": "Stop Recording",
        "microphone": "MICROPHONE",
        "result": "RESULT",
        "placeholder": "The result will appear here...",
        "clear": "Clear",
        "clear_result": "Clear result",
        "clear_history": "Clear history",
        "history_cleared": "History cleared.",
        "history": "History",
        "close": "Close",
        "open_json": "Open JSON",
        "history_count_one": "song saved",
        "history_count_many": "songs saved",
        "no_history": "No recognized songs yet.",
        "unknown": "Unknown",
        "report": "Report",
        "report_saved": "Report saved.",
        "report_hint": "Add a rule to corrections.json if this result has the wrong artist/title.",
        "local_correction": "Local correction applied from corrections.json.",
        "no_music": "Song not recognized.",
        "error_prefix": "Error",
    },
}


def _load_icon(filename: str, size: tuple[int, int]) -> ctk.CTkImage:
    image = Image.open(ASSETS_DIR / filename).convert("RGBA")
    return ctk.CTkImage(light_image=image, dark_image=image, size=size)


def _normalize_text(value) -> str:
    return " ".join(str(value or "").casefold().split())


def _read_json_list(path: Path) -> list:
    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return []

    return data if isinstance(data, list) else []


def _write_json_list(path: Path, data: list):
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_correction_rules() -> list[dict]:
    rules = _read_json_list(CORRECTIONS_FILE)
    if not rules:
        rules = DEFAULT_CORRECTIONS
        _write_json_list(CORRECTIONS_FILE, rules)
    return [rule for rule in rules if isinstance(rule, dict)]


def _rule_matches(result: dict, rule: dict) -> bool:
    match = rule.get("match", {})
    if not isinstance(match, dict):
        return False

    title = _normalize_text(result.get("title"))
    artist = _normalize_text(result.get("artist"))
    album = _normalize_text(result.get("album"))
    haystack = f"{title} {artist} {album}"

    for key, value in match.items():
        if key == "contains":
            values = value if isinstance(value, list) else [value]
            if not all(_normalize_text(item) in haystack for item in values):
                return False
        elif _normalize_text(result.get(key)) != _normalize_text(value):
            return False

    return True


def apply_known_corrections(result: dict) -> tuple[dict, bool]:
    if not isinstance(result, dict) or not result.get("ok"):
        return result, False

    for rule in load_correction_rules():
        if not _rule_matches(result, rule):
            continue
        replacement = rule.get("replace", {})
        if not isinstance(replacement, dict):
            continue
        corrected = dict(result)
        corrected.update(replacement)
        corrected["corrected"] = True
        corrected["corrected_from"] = (
            result.get("title") or result.get("artist") or "resultado Shazam"
        )
        return corrected, True

    return result, False


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

        self.title("Ichthus")
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
        self.language = "pt"
        self._status_key = "ready_to_listen"
        self._result_mode = "placeholder"
        self._last_result = None
        self._last_result_corrected = False
        self._last_result_configured = True
        self._last_error = ""
        self._cover_image = None
        self._cover_request_id = 0
        self._cover_animation_job = None
        self._cover_content_visible = False
        self._cover_url_cache = {}
        self._history_thumbnail_cache = {}
        self._history_thumbnail_loading = set()
        self._history_thumbnail_failures = set()
        self._history_images = []
        self.history = self.load_history()
        self.history_sidebar_visible = False
        self.history_sidebar = None
        self.history_canvas = None
        self.history_count_label = None
        self._history_redraw_job = None
        self._history_report_items = {}
        self._build_ui()

    def tr(self, key: str) -> str:
        return UI_TEXT.get(self.language, UI_TEXT["pt"]).get(key, key)

    def _history_count_text(self) -> str:
        total = len(self.history)
        key = "history_count_one" if total == 1 else "history_count_many"
        return f"{total} {self.tr(key)}"

    def _dedupe_lines(self, text: str) -> str:
        seen, unique_lines = set(), []
        for line in (text or "").splitlines():
            key = line.strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique_lines.append(line)
        return "\n".join(unique_lines)

    def _format_recognition_text(
        self,
        result: dict | None,
        corrected: bool = False,
        configured: bool = True,
    ) -> str:
        raw_text = format_shazam_result(result, self.language, show_source=False)
        if isinstance(result, dict) and result.get("ok") and corrected:
            raw_text = f"{raw_text}\n{self.tr('local_correction')}"
        if not isinstance(result, dict) or not result.get("ok"):
            raw_text = f"{raw_text}\n\n{self.tr('no_music')}"
        return self._dedupe_lines(raw_text)

    def _set_result_text(self, _text: str):
        return

    def _fetch_image_bytes(self, url: str) -> bytes | None:
        if not url:
            return None

        try:
            response = requests.get(
                url,
                timeout=8,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException:
            return None

    def _cover_search_queries(self, result: dict, query: str) -> list[str]:
        title = str(result.get("title") or "").strip()
        artist = str(result.get("artist") or "").strip()
        album = str(result.get("album") or "").strip()

        def join_unique(*parts: str) -> str:
            seen_parts = set()
            clean_parts = []
            for part in parts:
                key = _normalize_text(part)
                if not key or key in seen_parts:
                    continue
                seen_parts.add(key)
                clean_parts.append(part)
            return " ".join(clean_parts)

        candidates = [
            join_unique(title, artist, album),
            join_unique(title, artist),
            join_unique(artist, title),
            join_unique(title, album),
            query,
        ]

        seen = set()
        clean = []
        for candidate in candidates:
            key = _normalize_text(candidate)
            if not key or key in seen:
                continue
            seen.add(key)
            clean.append(candidate)
        return clean

    def _normalize_artwork_url(self, url: str) -> str:
        return (
            str(url or "")
            .replace("100x100bb", "600x600bb")
            .replace("100x100cc", "600x600cc")
            .replace("60x60bb", "600x600bb")
        )

    def _find_itunes_artwork_url(self, query: str) -> str:
        if not query:
            return ""

        try:
            response = requests.get(
                "https://itunes.apple.com/search",
                params={
                    "term": query,
                    "media": "music",
                    "entity": "song",
                    "country": "BR",
                    "limit": 5,
                },
                timeout=4,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
            data = response.json()
        except (requests.exceptions.RequestException, ValueError):
            return ""

        for item in data.get("results", []):
            if isinstance(item, dict) and item.get("artworkUrl100"):
                return self._normalize_artwork_url(item["artworkUrl100"])
        return ""

    def _find_deezer_artwork_url(self, query: str) -> str:
        if not query:
            return ""

        try:
            response = requests.get(
                "https://api.deezer.com/search",
                params={"q": query, "limit": 5},
                timeout=4,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
            data = response.json()
        except (requests.exceptions.RequestException, ValueError):
            return ""

        for item in data.get("data", []):
            album = item.get("album") if isinstance(item, dict) else None
            if not isinstance(album, dict):
                continue
            for key in ("cover_xl", "cover_big", "cover_medium"):
                if album.get(key):
                    return str(album[key])
        return ""

    def _find_youtube_thumbnail_url(self, query: str) -> str:
        if not query:
            return ""

        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
        try:
            response = requests.get(
                url,
                timeout=4,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
        except requests.exceptions.RequestException:
            return ""

        match = re.search(r'"videoId":"([A-Za-z0-9_-]{11})"', response.text)
        if not match:
            return ""
        return f"https://img.youtube.com/vi/{match.group(1)}/hqdefault.jpg"

    def _cover_url_candidates(self, result: dict, query: str) -> list[str]:
        urls = []
        normalized_query = _normalize_text(query)
        direct_url = "" if result.get("corrected") else str(result.get("cover_url") or "").strip()
        if direct_url:
            urls.append(direct_url)

        cached_url = self._cover_url_cache.get(normalized_query)
        if cached_url:
            urls.append(cached_url)

        queries = self._cover_search_queries(result, query)
        for search_query in queries[:3]:
            url = self._find_itunes_artwork_url(search_query)
            if url:
                urls.append(url)

        for search_query in queries[:3]:
            url = self._find_deezer_artwork_url(search_query)
            if url:
                urls.append(url)

        youtube_query = queries[0] if queries else query
        youtube_url = self._find_youtube_thumbnail_url(youtube_query)
        if youtube_url:
            urls.append(youtube_url)

        seen = set()
        unique_urls = []
        for url in urls:
            if not url or url in seen:
                continue
            seen.add(url)
            unique_urls.append(url)
        return unique_urls

    def _cancel_cover_animation(self):
        if not self._cover_animation_job:
            return

        try:
            self.after_cancel(self._cover_animation_job)
        except tk.TclError:
            pass
        self._cover_animation_job = None

    def _set_cover_content_visible(self, visible: bool):
        if visible:
            if not self.cover_art_label.winfo_manager():
                self.cover_art_label.pack(side="left", padx=(10, 12), pady=10)
            if not self.cover_text.winfo_manager():
                self.cover_text.pack(
                    side="left",
                    fill="both",
                    expand=True,
                    padx=(0, 12),
                    pady=12,
                )
        else:
            self.cover_art_label.pack_forget()
            self.cover_text.pack_forget()
        self._cover_content_visible = visible

    def _animate_cover_entry(self, step: int = 0):
        if not hasattr(self, "cover_frame") or not self.cover_slot.winfo_manager():
            self._cover_animation_job = None
            return

        total_steps = 34
        progress = min(step / total_steps, 1)
        eased = progress * progress * (3 - 2 * progress)
        height = max(6, int(COVER_CARD_HEIGHT * eased))
        relwidth = 0.68 + (0.32 * eased)
        self.cover_frame.configure(height=height)
        self.cover_frame.place_configure(
            relx=0.5,
            rely=0.5,
            anchor="center",
            relwidth=relwidth,
        )

        if step >= total_steps:
            self.cover_frame.configure(height=COVER_CARD_HEIGHT)
            self.cover_frame.place_configure(
                relx=0.5,
                rely=0.5,
                anchor="center",
                relwidth=1,
            )
            self._set_cover_content_visible(True)
            self._cover_animation_job = None
            return

        self._cover_animation_job = self.after(
            12, self._animate_cover_entry, step + 1
        )

    def _hide_cover(self):
        self._cover_image = None
        if not hasattr(self, "cover_frame"):
            return

        self._cancel_cover_animation()
        self.cover_slot.configure(height=COVER_CARD_HEIGHT)
        self._set_cover_content_visible(False)
        self.cover_frame.place_forget()
        self.cover_art_label.configure(
            image=None,
            text="",
            fg_color="transparent",
        )
        self.cover_title_label.configure(text="")
        self.cover_artist_label.configure(text="")
        self.cover_slot.pack_forget()

    def _show_cover_card(self, title: str, artist: str):
        if not hasattr(self, "cover_frame"):
            return

        self.cover_title_label.configure(text=title or self.tr("unknown"))
        self.cover_artist_label.configure(text=artist or "")
        if not self._cover_image:
            self.cover_art_label.configure(
                image=None,
                text="♪",
                font=(FONT_FAMILY, 30, "bold"),
                text_color=TEXT_MUTED,
                fg_color=BG_CARD2,
            )
        was_hidden = not self.cover_slot.winfo_manager()
        if was_hidden:
            if hasattr(self, "stream_row"):
                self.cover_slot.pack(
                    fill="x",
                    padx=24,
                    pady=(0, 6),
                    before=self.stream_row,
                )
            else:
                self.cover_slot.pack(fill="x", padx=24, pady=(0, 6))
            self._cancel_cover_animation()
            self.cover_slot.configure(height=COVER_CARD_HEIGHT)
            self._set_cover_content_visible(False)
            self.cover_frame.configure(height=6)
            self.cover_frame.place(
                relx=0.5,
                rely=0.5,
                anchor="center",
                relwidth=0.68,
            )
            self._animate_cover_entry()
        elif not self._cover_animation_job:
            self.cover_slot.configure(height=COVER_CARD_HEIGHT)
            self.cover_frame.configure(height=COVER_CARD_HEIGHT)
            self.cover_frame.place_configure(
                relx=0.5,
                rely=0.5,
                anchor="center",
                relwidth=1,
            )
            self._set_cover_content_visible(True)

    def _show_cover_from_bytes(
        self,
        request_id: int,
        image_bytes: bytes | None,
        title: str,
        artist: str,
    ):
        if request_id != self._cover_request_id:
            return
        if not image_bytes:
            return

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            image = ImageOps.fit(image, (COVER_SIZE, COVER_SIZE), method=Image.LANCZOS)
        except (OSError, ValueError):
            return

        self._cover_image = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=(COVER_SIZE, COVER_SIZE),
        )
        self.cover_art_label.configure(
            image=self._cover_image,
            text="",
            fg_color="transparent",
        )
        self._show_cover_card(title, artist)

    def _remember_history_image_url(self, query: str, image_url: str):
        query_key = _normalize_text(query)
        if not query_key or not image_url:
            return

        changed = False
        for entry in self.history:
            if _normalize_text(entry.get("query")) != query_key:
                continue
            if entry.get("image_url") != image_url:
                entry["image_url"] = image_url
                changed = True

        if changed:
            self.save_history()
            self.render_history()

    def _load_cover_async(self, result: dict, query: str):
        self._cover_request_id += 1
        request_id = self._cover_request_id
        title = str(result.get("title") or self.tr("unknown")).strip()
        artist = str(result.get("artist") or "").strip()
        try:
            self.after(0, self._show_cover_card, title, artist)
        except tk.TclError:
            pass

        def worker():
            image_bytes = None
            successful_url = ""
            for url in self._cover_url_candidates(result, query):
                image_bytes = self._fetch_image_bytes(url)
                if image_bytes:
                    successful_url = url
                    break
            if successful_url:
                self._cover_url_cache[_normalize_text(query)] = successful_url
                try:
                    self.after(0, self._remember_history_image_url, query, successful_url)
                except tk.TclError:
                    pass
            try:
                self.after(0, self._show_cover_from_bytes, request_id, image_bytes, title, artist)
            except tk.TclError:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def clear_cover(self):
        self._cover_request_id += 1
        self._hide_cover()

    def _zoom_platform_icon(self, platform: str, zoomed: bool):
        if platform == "youtube":
            button = self.btn_youtube
            icon = self._icon_yt_zoom if zoomed else self._icon_yt
        else:
            button = self.btn_spotify
            icon = self._icon_spotify_zoom if zoomed else self._icon_spotify

        if zoomed and str(button.cget("state")) != "normal":
            return
        button.configure(image=icon)

    def _refresh_result_language(self):
        if self._result_mode == "result":
            self._set_result_text(
                self._format_recognition_text(
                    self._last_result,
                    self._last_result_corrected,
                    self._last_result_configured,
                )
            )
        elif self._result_mode == "error":
            self._set_result_text(f"{self.tr('error_prefix')}: {self._last_error}")
        else:
            self._set_result_text(self.tr("placeholder"))

    def set_status(self, key: str):
        self._status_key = key
        self.update_status(self.tr(key), remember=False)

    def update_status(self, text: str, remember: bool = True):
        if remember:
            self._status_key = None
        self._status_label.configure(text=text)

    def toggle_language(self):
        current_index = LANGUAGE_ORDER.index(self.language)
        self.language = LANGUAGE_ORDER[(current_index + 1) % len(LANGUAGE_ORDER)]
        self.apply_language()

    def apply_language(self):
        if hasattr(self, "btn_language"):
            self.btn_language.configure(text=self.tr("language_button"))
        if hasattr(self, "btn_recognize"):
            self.btn_recognize.configure(text=f"  {self.tr('listen_music')}")
        if hasattr(self, "btn_stop"):
            self.btn_stop.configure(text=f"  {self.tr('stop_recording')}")
        if hasattr(self, "label_microphone"):
            self.label_microphone.configure(text=self.tr("microphone"))
        if hasattr(self, "label_result"):
            self.label_result.configure(text=self.tr("result"))
        if hasattr(self, "btn_clear"):
            self.btn_clear.configure(text=self.tr("clear_result"))
        if hasattr(self, "btn_history"):
            key = "close" if self.history_sidebar_visible else "history"
            self.btn_history.configure(text=self.tr(key))
        if hasattr(self, "history_title_label"):
            self.history_title_label.configure(text=self.tr("history"))
        if hasattr(self, "btn_open_history_json"):
            self.btn_open_history_json.configure(text=self.tr("open_json"))
        if hasattr(self, "btn_clear_history"):
            self.btn_clear_history.configure(text=self.tr("clear_history"))
        if self._status_key and hasattr(self, "_status_label"):
            self._status_label.configure(text=self.tr(self._status_key))
        self._refresh_result_language()
        self.render_history()

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
            font=(FONT_FAMILY, 22, "bold"),
            text_color=ACCENT_LIGHT,
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text="Ichthus",
            font=(FONT_FAMILY, 20, "bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left", padx=(8, 0))

        self._dot = ctk.CTkLabel(
            header, text="●", font=(FONT_FAMILY, 10), text_color=TEXT_MUTED
        )
        self.btn_language = ctk.CTkButton(
            header,
            text=self.tr("language_button"),
            font=(FONT_FAMILY, 11, "bold"),
            width=42,
            height=28,
            corner_radius=9,
            fg_color=BG_FIELD,
            hover_color=GRAY_HOVER,
            border_color=BORDER,
            border_width=1,
            text_color=TEXT_PRIMARY,
            command=self.toggle_language,
        )
        self.btn_language.pack(side="right", padx=(8, 0))
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
            text=self.tr("ready_to_listen"),
            font=(FONT_FAMILY, 13),
            text_color=TEXT_MUTED,
        )
        self._status_label.pack(side="left")

        self.btn_recognize = ctk.CTkButton(
            card,
            text=f"  {self.tr('listen_music')}",
            font=(FONT_FAMILY, 15, "bold"),
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
            text=f"  {self.tr('stop_recording')}",
            font=(FONT_FAMILY, 13),
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
        self.label_microphone = ctk.CTkLabel(
            card,
            text=self.tr("microphone"),
            font=(FONT_FAMILY, 10, "bold"),
            text_color=TEXT_MUTED,
        )
        self.label_microphone.pack(anchor="w", padx=28, pady=(16, 4))

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
            font=(FONT_FAMILY, 12),
        )
        self.device_selector.pack(fill="x", padx=24)
        if self.input_devices:
            self.device_selector.set(self.input_devices[0])
        self.device_selector._entry.configure(state="readonly", cursor="arrow")

        ctk.CTkFrame(card, height=1, fg_color=BORDER).pack(
            fill="x", padx=24, pady=(16, 0)
        )


        self.label_result = ctk.CTkLabel(
            card,
            text=self.tr("result"),
            font=(FONT_FAMILY, 10, "bold"),
            text_color=TEXT_MUTED,
        )
        self.label_result.pack(anchor="w", padx=28, pady=(16, 4))

        self.cover_slot = ctk.CTkFrame(
            card,
            height=COVER_CARD_HEIGHT,
            fg_color="transparent",
        )
        self.cover_slot.pack_propagate(False)

        self.cover_frame = ctk.CTkFrame(
            self.cover_slot,
            height=COVER_CARD_HEIGHT,
            corner_radius=12,
            fg_color=BG_FIELD,
            border_color=BORDER,
            border_width=1,
        )
        self.cover_frame.pack_propagate(False)
        self.cover_art_label = ctk.CTkLabel(
            self.cover_frame,
            text="",
            width=COVER_SIZE,
            height=COVER_SIZE,
            fg_color="transparent",
            corner_radius=0,
        )
        self.cover_art_label.pack(side="left", padx=(10, 12), pady=10)

        self.cover_text = ctk.CTkFrame(self.cover_frame, fg_color="transparent")
        self.cover_text.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=12)
        self.cover_title_label = ctk.CTkLabel(
            self.cover_text,
            text="",
            font=(FONT_FAMILY, 13, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
            wraplength=320,
            justify="left",
        )
        self.cover_title_label.pack(anchor="w", fill="x")

        cover_meta_row = ctk.CTkFrame(self.cover_text, fg_color="transparent")
        cover_meta_row.pack(anchor="w", fill="x", pady=(5, 0))
        self.cover_artist_label = ctk.CTkLabel(
            cover_meta_row,
            text="",
            font=(FONT_FAMILY, 11),
            text_color=ACCENT_LIGHT,
            anchor="w",
            justify="left",
        )
        self.cover_artist_label.pack(side="left")

        self._icon_yt      = _load_icon("youtube.png", (30, 21))
        self._icon_yt_zoom = _load_icon("youtube.png", (34, 24))
        self._icon_spotify = _load_icon("spotify.png", (28, 28))
        self._icon_spotify_zoom = _load_icon("spotify.png", (32, 32))

        cover_platform_row = ctk.CTkFrame(cover_meta_row, fg_color="transparent")
        cover_platform_row.pack(side="left", padx=(28, 0))

        self.btn_youtube = ctk.CTkButton(
            cover_platform_row,
            text="",
            image=self._icon_yt,
            width=34,
            height=30,
            corner_radius=8,
            fg_color="transparent",
            hover_color=BG_CARD2,
            border_width=0,
            state="disabled",
            command=self.open_youtube,
        )
        self.btn_youtube.pack(side="left", padx=(0, 10))
        self.btn_youtube.bind(
            "<Enter>",
            lambda _event: self._zoom_platform_icon("youtube", True),
            add="+",
        )
        self.btn_youtube.bind(
            "<Leave>",
            lambda _event: self._zoom_platform_icon("youtube", False),
            add="+",
        )

        self.btn_spotify = ctk.CTkButton(
            cover_platform_row,
            text="",
            image=self._icon_spotify,
            width=34,
            height=30,
            corner_radius=8,
            fg_color="transparent",
            hover_color=BG_CARD2,
            border_width=0,
            state="disabled",
            command=self.open_spotify,
        )
        self.btn_spotify.pack(side="left")
        self.btn_spotify.bind(
            "<Enter>",
            lambda _event: self._zoom_platform_icon("spotify", True),
            add="+",
        )
        self.btn_spotify.bind(
            "<Leave>",
            lambda _event: self._zoom_platform_icon("spotify", False),
            add="+",
        )
        self.cover_frame.place_forget()

        #histórico e limpeza ficam fora do card da música; plataformas ficam dentro dele.
        self.stream_row = ctk.CTkFrame(card, fg_color="transparent")
        self.stream_row.pack(fill="x", padx=24, pady=(0, 6))

        self.btn_history = ctk.CTkButton(
            self.stream_row,
            text=self.tr("history"),
            font=(FONT_FAMILY, 11, "bold"),
            width=86,
            height=36,
            corner_radius=12,
            fg_color=BG_FIELD,
            hover_color=GRAY_HOVER,
            border_color=BORDER,
            border_width=1,
            text_color=TEXT_PRIMARY,
            command=self.toggle_history_sidebar,
        )
        self.btn_history.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_clear = ctk.CTkButton(
            self.stream_row,
            text=self.tr("clear_result"),
            font=(FONT_FAMILY, 11),
            width=76,
            height=36,
            corner_radius=12,
            fg_color=GRAY_BTN,
            hover_color=GRAY_HOVER,
            text_color=TEXT_MUTED,
            command=self.clear_results,
        )
        self.btn_clear.pack(side="left", fill="x", expand=True)

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
        clean_history = []
        for entry in history:
            if not isinstance(entry, dict):
                continue
            corrected, _ = apply_known_corrections({"ok": True, **entry})
            corrected.pop("ok", None)
            clean_history.append(corrected)
        return clean_history[:MAX_HISTORY]

    def save_history(self):
        with HISTORY_FILE.open("w", encoding="utf-8") as file:
            json.dump(self.history[:MAX_HISTORY], file, ensure_ascii=False, indent=2)

    def _history_entry_query(self, entry: dict) -> str:
        query = str(entry.get("query") or "").strip()
        if query:
            return query
        return " ".join(
            str(entry.get(key) or "").strip()
            for key in ("title", "artist", "album")
            if str(entry.get(key) or "").strip()
        )

    def _finish_history_thumbnail(
        self,
        query_key: str,
        image_url: str,
        image_bytes: bytes | None,
    ):
        self._history_thumbnail_loading.discard(query_key)
        if not image_bytes:
            self._history_thumbnail_failures.add(query_key)
            return

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            image = ImageOps.fit(
                image,
                (HISTORY_THUMB_SIZE, HISTORY_THUMB_SIZE),
                method=Image.LANCZOS,
            )
            thumbnail = ImageTk.PhotoImage(image)
        except (OSError, ValueError, tk.TclError):
            self._history_thumbnail_failures.add(query_key)
            return

        self._history_thumbnail_cache[query_key] = thumbnail
        if image_url:
            self._cover_url_cache[query_key] = image_url
            self._remember_history_image_url(query_key, image_url)
        self.render_history()

    def _ensure_history_thumbnail(self, entry: dict):
        query = self._history_entry_query(entry)
        query_key = _normalize_text(query)
        if not query_key:
            return None

        cached = self._history_thumbnail_cache.get(query_key)
        if cached:
            return cached
        if query_key in self._history_thumbnail_loading or query_key in self._history_thumbnail_failures:
            return None

        entry_cover_url = "" if entry.get("corrected") else entry.get("cover_url")
        direct_url = str(
            entry.get("image_url")
            or entry_cover_url
            or self._cover_url_cache.get(query_key)
            or ""
        ).strip()
        result = {
            "title": entry.get("title") or "",
            "artist": entry.get("artist") or "",
            "album": entry.get("album") or "",
            "cover_url": entry.get("cover_url") or "",
            "corrected": entry.get("corrected") or False,
        }

        self._history_thumbnail_loading.add(query_key)

        def worker():
            urls = []
            if direct_url:
                urls.append(direct_url)
            urls.extend(self._cover_url_candidates(result, query))

            image_bytes = None
            successful_url = ""
            seen = set()
            for url in urls:
                if not url or url in seen:
                    continue
                seen.add(url)
                image_bytes = self._fetch_image_bytes(url)
                if image_bytes:
                    successful_url = url
                    break

            try:
                self.after(
                    0,
                    self._finish_history_thumbnail,
                    query_key,
                    successful_url,
                    image_bytes,
                )
            except tk.TclError:
                pass

        threading.Thread(target=worker, daemon=True).start()
        return None

    def render_history(self):
        self._history_redraw_job = None

        if not self.history_canvas or not self.history_canvas.winfo_exists():
            return

        if self.history_count_label and self.history_count_label.winfo_exists():
            self.history_count_label.configure(text=self._history_count_text())

        canvas = self.history_canvas
        canvas.delete("all")
        self._history_images = []
        self._history_report_items = {}
        canvas_width = max(canvas.winfo_width(), 260)
        card_x0 = 10
        card_x1 = canvas_width - 12
        card_w = max(card_x1 - card_x0, 220)
        title_font_tuple = (FONT_FAMILY, 10, "bold")
        body_font_tuple = (FONT_FAMILY, 8)
        meta_font_tuple = (FONT_FAMILY, 7)
        tag_font_tuple = (FONT_FAMILY, 7, "bold")
        title_font = tkfont.Font(family=FONT_FAMILY, size=10, weight="bold")
        body_font = tkfont.Font(family=FONT_FAMILY, size=8)
        meta_font = tkfont.Font(family=FONT_FAMILY, size=7)
        tag_font = tkfont.Font(family=FONT_FAMILY, size=7, weight="bold")

        def fit_text(value, font, max_px):
            text = str(value or "").strip()
            if font.measure(text) <= max_px:
                return text
            while text and font.measure(text + "...") > max_px:
                text = text[:-1].rstrip()
            return (text + "...") if text else "..."

        if not self.history:
            canvas.create_rectangle(
                card_x0,
                10,
                card_x1,
                82,
                fill=BG_FIELD,
                outline=BORDER,
                width=1,
            )
            canvas.create_text(
                card_x0 + 14,
                46,
                text=self.tr("no_history"),
                font=(FONT_FAMILY, 12),
                fill=TEXT_MUTED,
                anchor="w",
                width=card_w - 28,
            )
            canvas.configure(scrollregion=(0, 0, canvas_width, 92))
            return

        y = 10
        for index, entry in enumerate(self.history, 1):
            when = entry.get("when") or ""
            card_h = 108
            thumb_x0 = card_x0 + 12
            thumb_y0 = y + 14
            thumb_x1 = thumb_x0 + HISTORY_THUMB_SIZE
            thumb_y1 = thumb_y0 + HISTORY_THUMB_SIZE
            report_w = 62
            tag_x1 = card_x1 - 10
            report_x0 = tag_x1 - report_w
            text_x = thumb_x1 + 12
            text_w = max(report_x0 - text_x - 8, 80)
            title = fit_text(entry.get("title") or self.tr("unknown"), title_font, text_w)
            artist = fit_text(entry.get("artist") or self.tr("unknown"), body_font, text_w)
            album = fit_text(entry.get("album") or "", body_font, text_w)

            canvas.create_rectangle(
                card_x0,
                y,
                card_x1,
                y + card_h,
                fill="#101025",
                outline=BORDER,
                width=1,
            )

            canvas.create_rectangle(
                thumb_x0,
                thumb_y0,
                thumb_x1,
                thumb_y1,
                fill=BG_CARD2,
                outline=BORDER,
                width=1,
            )
            thumbnail = self._ensure_history_thumbnail(entry)
            if thumbnail:
                self._history_images.append(thumbnail)
                canvas.create_image(
                    thumb_x0 + HISTORY_THUMB_SIZE / 2,
                    thumb_y0 + HISTORY_THUMB_SIZE / 2,
                    image=thumbnail,
                )
            else:
                canvas.create_text(
                    thumb_x0 + HISTORY_THUMB_SIZE / 2,
                    thumb_y0 + HISTORY_THUMB_SIZE / 2,
                    text="♪",
                    font=(FONT_FAMILY, 20, "bold"),
                    fill=TEXT_MUTED,
                )

            canvas.create_rectangle(
                thumb_x0,
                thumb_y0,
                thumb_x0 + 27,
                thumb_y0 + 20,
                fill=ACCENT,
                outline=ACCENT,
            )
            canvas.create_text(
                thumb_x0 + 13.5,
                thumb_y0 + 10,
                text=f"{index:02d}",
                font=tag_font_tuple,
                fill=TEXT_PRIMARY,
            )

            canvas.create_text(
                text_x,
                y + 14,
                text=title,
                font=title_font_tuple,
                anchor="w",
                fill=TEXT_PRIMARY,
            )

            canvas.create_text(
                text_x,
                y + 36,
                text=artist,
                font=body_font_tuple,
                anchor="w",
                fill=ACCENT_LIGHT,
            )

            if album:
                canvas.create_text(
                    text_x,
                    y + 58,
                    text=album,
                    font=body_font_tuple,
                    anchor="w",
                    fill=TEXT_MUTED,
            )

            meta_y = y + card_h - 24
            max_when_px = max(report_x0 - text_x - 8, 44)
            when_text = fit_text(when, meta_font, max_when_px)

            canvas.create_text(
                text_x,
                meta_y,
                text=when_text,
                font=meta_font_tuple,
                anchor="w",
                fill=TEXT_MUTED,
            )

            report_tag = f"report_{index}"
            self._history_report_items[report_tag] = dict(entry)
            canvas.create_rectangle(
                report_x0,
                meta_y - 13,
                tag_x1,
                meta_y + 13,
                fill="#2A213C",
                outline="#2A213C",
                tags=(report_tag, "report_button"),
            )
            canvas.create_text(
                (report_x0 + tag_x1) / 2,
                meta_y,
                text=self.tr("report"),
                font=tag_font_tuple,
                fill=ACCENT_LIGHT,
                tags=(report_tag, "report_button"),
            )
            canvas.tag_bind(report_tag, "<Button-1>", self.report_history_item)
            canvas.tag_bind(report_tag, "<Enter>", lambda _event: canvas.configure(cursor="hand2"))
            canvas.tag_bind(report_tag, "<Leave>", lambda _event: canvas.configure(cursor=""))

            y += card_h + 10

        canvas.configure(scrollregion=(0, 0, canvas_width, y))

    def open_history_file(self):
        if not HISTORY_FILE.exists():
            self.save_history()
        webbrowser.open(HISTORY_FILE.as_uri())

    def report_history_item(self, event):
        tags = event.widget.gettags("current")
        report_tag = next((tag for tag in tags if tag.startswith("report_")), "")
        entry = self._history_report_items.get(report_tag)
        if not entry:
            return

        reports = _read_json_list(REPORTS_FILE)
        reports.insert(
            0,
            {
                "reported_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "status": "pending",
                "entry": entry,
                "hint": self.tr("report_hint"),
            },
        )
        _write_json_list(REPORTS_FILE, reports[:MAX_HISTORY])
        self.set_status("report_saved")

    def _build_history_sidebar(self):
        self.history_sidebar = ctk.CTkFrame(
            self,
            width=300,
            fg_color=BG_CARD,
            corner_radius=18,
        )
        self.history_sidebar.pack_propagate(False)

        self.history_title_label = ctk.CTkLabel(
            self.history_sidebar,
            text=self.tr("history"),
            font=(FONT_FAMILY, 18, "bold"),
            text_color=TEXT_PRIMARY,
        )
        self.history_title_label.pack(anchor="w", padx=18, pady=(16, 4))

        self.history_count_label = ctk.CTkLabel(
            self.history_sidebar,
            text=self._history_count_text(),
            font=(FONT_FAMILY, 10),
            text_color=TEXT_MUTED,
            wraplength=260,
        )
        self.history_count_label.pack(anchor="w", padx=18, pady=(0, 10))

        actions = ctk.CTkFrame(self.history_sidebar, fg_color="transparent")
        actions.pack(fill="x", padx=18, pady=(0, 10))

        self.btn_open_history_json = ctk.CTkButton(
            actions,
            text=self.tr("open_json"),
            font=(FONT_FAMILY, 11, "bold"),
            height=32,
            corner_radius=10,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT_PRIMARY,
            command=self.open_history_file,
        )
        self.btn_open_history_json.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_clear_history = ctk.CTkButton(
            actions,
            text=self.tr("clear_history"),
            font=(FONT_FAMILY, 11),
            height=32,
            corner_radius=10,
            fg_color=GRAY_BTN,
            hover_color=GRAY_HOVER,
            text_color=TEXT_MUTED,
            command=self.clear_history,
        )
        self.btn_clear_history.pack(side="left", fill="x", expand=True)

        self.history_list = ctk.CTkFrame(
            self.history_sidebar,
            corner_radius=14,
            fg_color=BG_FIELD,
            border_color=BORDER,
            border_width=1,
        )
        self.history_list.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.history_canvas = ctk.CTkCanvas(
            self.history_list,
            bg=BG_FIELD,
            highlightthickness=0,
            bd=0,
        )
        history_scrollbar = ctk.CTkScrollbar(
            self.history_list,
            orientation="vertical",
            command=self.history_canvas.yview,
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
        )
        self.history_canvas.configure(yscrollcommand=history_scrollbar.set)
        self.history_canvas.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        history_scrollbar.pack(side="right", fill="y", padx=(4, 8), pady=8)
        self.history_canvas.bind("<MouseWheel>", self.on_history_mousewheel)
        self.history_canvas.bind("<Configure>", self.schedule_history_render)
        self.render_history()

    def schedule_history_render(self, _event=None):
        if self._history_redraw_job:
            try:
                self.after_cancel(self._history_redraw_job)
            except tk.TclError:
                pass
        self._history_redraw_job = self.after(40, self.render_history)

    def on_history_mousewheel(self, event):
        if not self.history_canvas:
            return "break"

        direction = -1 if event.delta > 0 else 1
        self.history_canvas.yview_scroll(direction * 3, "units")
        return "break"

    def toggle_history_sidebar(self):
        if not self.history_sidebar:
            return

        if self.history_sidebar_visible:
            self.history_sidebar.pack_forget()
            self.history_sidebar_visible = False
            self.minsize(420, 620)
            self.btn_history.configure(text=self.tr("history"))
            return

        self.history_sidebar.pack(side="right", fill="y", padx=(0, 18), pady=22)
        self.history_sidebar_visible = True
        self.minsize(720, 620)
        if self.winfo_width() < 720:
            self.geometry(f"760x{max(self.winfo_height(), 720)}")
        self.btn_history.configure(text=self.tr("close"))
        self.render_history()

    def add_history_entry(self, result: dict):
        title = str(result.get("title") or "").strip()
        artist = str(result.get("artist") or "").strip()

        if not title or title == "Desconhecido":
            return

        entry = {
            "when": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "provider": str(result.get("provider") or "Shazam"),
            "title": title,
            "artist": artist or "Desconhecido",
            "album": str(result.get("album") or ""),
            "cover_url": str(result.get("cover_url") or ""),
            "image_url": "" if result.get("corrected") else str(result.get("cover_url") or ""),
            "query": " ".join(
                part for part in (title, artist, str(result.get("album") or "")) if part
            ),
        }
        if result.get("corrected"):
            entry["corrected"] = True
            entry["corrected_from"] = str(result.get("corrected_from") or "")

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
        self.set_status("history_cleared")

    def _set_dot(self, color: str):
        self._dot.configure(text_color=color)

    def clear_results(self):
        self._result_mode = "placeholder"
        self._last_result = None
        self._last_result_corrected = False
        self._last_result_configured = True
        self._last_error = ""
        self._set_result_text(self.tr("placeholder"))
        self.clear_cover()
        self._youtube_query = ""
        self.btn_youtube.configure(
            state="disabled",
            fg_color="transparent",
            border_width=0,
            image=self._icon_yt,
        )
        self.btn_spotify.configure(
            state="disabled",
            fg_color="transparent",
            border_width=0,
            image=self._icon_spotify,
        )

    def start_recognition_thread(self):
        self.btn_recognize.configure(state="disabled")
        self.btn_stop.configure(
            state="normal",
            fg_color=RED,
            text_color=TEXT_PRIMARY,
        )
        self.clear_cover()
        self.set_status("listening")
        self._set_dot(ACCENT_LIGHT)
        self._bars.start()
        thread = threading.Thread(target=self.run_recognition, daemon=True)
        thread.start()

    def run_recognition(self):
        final_status_text = ""
        self._set_result_text("")
        try:
            selection  = self.device_selector.get()
            device_id  = int(selection.split(":")[0]) if selection else None

            audio = record_audio(device=device_id)

            result = None
            corrected = False
            configured = True
            self.set_status("identifying_shazam")
            result = recognize_shazam(audio, sample_rate=SAMPLE_RATE)
            if isinstance(result, dict) and result.get("ok"):
                result, corrected = apply_known_corrections(result)
            elif isinstance(result, dict):
                final_status_text = str(result.get("error") or self.tr("no_music"))
            else:
                final_status_text = self.tr("no_music")

            clean_text = self._format_recognition_text(result, corrected, configured)
            self._last_result = result
            self._last_result_corrected = corrected
            self._last_result_configured = configured
            self._result_mode = "result"
            self._set_result_text(clean_text if clean_text else self.tr("no_music"))

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
                self._load_cover_async(result, self._youtube_query)
                self.btn_youtube.configure(
                    state="normal",
                    fg_color="transparent",
                    border_width=0,
                    image=self._icon_yt,
                )
                self.btn_spotify.configure(
                    state="normal",
                    fg_color="transparent",
                    border_width=0,
                    image=self._icon_spotify,
                )
            else:
                self.after(0, self.clear_cover)
                if not final_status_text:
                    final_status_text = self.tr("no_music")

        except Exception as e:
            self._last_error = str(e)
            self._result_mode = "error"
            final_status_text = f"{self.tr('error_prefix')}: {e}"
            self._set_result_text(f"{self.tr('error_prefix')}: {e}")
            self.after(0, self.clear_cover)

        finally:
            self._bars.stop()
            if final_status_text:
                self.update_status(final_status_text)
            else:
                self.set_status("ready")
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
        self.set_status("recording_stopped")
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
