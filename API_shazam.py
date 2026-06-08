import asyncio
import io
import warnings
from typing import Any

import numpy as np
import soundfile as sf

warnings.filterwarnings(
    "ignore",
    message="Couldn't find ffmpeg or avconv.*",
    category=RuntimeWarning,
)

from shazamio import Shazam


def _audio_to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    audio = np.asarray(audio, dtype=np.float32).flatten()
    if audio.size == 0:
        raise ValueError("Audio vazio. Nada foi gravado.")

    peak = float(np.max(np.abs(audio)))
    if peak > 0:
        audio = audio / peak

    buffer = io.BytesIO()
    sf.write(buffer, audio, sample_rate, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


def _metadata_value(track: dict[str, Any], *names: str) -> str:
    wanted = {name.casefold() for name in names}
    for section in track.get("sections") or []:
        if not isinstance(section, dict):
            continue
        for item in section.get("metadata") or []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip().casefold()
            if title in wanted:
                return str(item.get("text") or "").strip()
    return ""


def _extract_cover_url(track: dict[str, Any]) -> str:
    images = track.get("images")
    if not isinstance(images, dict):
        return ""
    for key in ("coverarthq", "coverart", "background"):
        if images.get(key):
            return str(images[key])
    return ""


def _extract_youtube_url(track: dict[str, Any]) -> str:
    for section in track.get("sections") or []:
        if not isinstance(section, dict):
            continue
        if section.get("youtubeurl"):
            return str(section["youtubeurl"])
    return ""


def normalize_result(data: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {
            "ok": False,
            "provider": "Shazam",
            "error": "Resposta invalida do Shazam.",
        }

    track = data.get("track")
    if not isinstance(track, dict):
        return {
            "ok": False,
            "provider": "Shazam",
            "error": "Musica nao reconhecida.",
            "raw": data,
        }

    return {
        "ok": True,
        "provider": "Shazam",
        "title": str(track.get("title") or "Desconhecido"),
        "artist": str(track.get("subtitle") or "Desconhecido"),
        "album": _metadata_value(track, "album"),
        "release_date": _metadata_value(
            track,
            "released",
            "release date",
            "lançamento",
        ),
        "label": _metadata_value(track, "label", "gravadora"),
        "cover_url": _extract_cover_url(track),
        "youtube_url": _extract_youtube_url(track),
        "shazam_url": str(track.get("url") or ""),
        "raw": track,
    }


async def _recognize_bytes_async(audio_bytes: bytes) -> dict[str, Any]:
    shazam = Shazam(language="pt-BR", endpoint_country="BR")
    response = await shazam.recognize(audio_bytes)
    return normalize_result(response)


def recognize_from_bytes(audio_bytes: bytes) -> dict[str, Any]:
    if not audio_bytes:
        return {
            "ok": False,
            "provider": "Shazam",
            "error": "Audio vazio. Nada foi enviado.",
        }

    try:
        return asyncio.run(_recognize_bytes_async(audio_bytes))
    except Exception as error:
        return {
            "ok": False,
            "provider": "Shazam",
            "error": f"Falha no reconhecimento: {error}",
        }


def recognize_from_audio(audio: np.ndarray, sample_rate: int = 22050) -> dict[str, Any]:
    try:
        audio_bytes = _audio_to_wav_bytes(audio, sample_rate)
    except ValueError as error:
        return {"ok": False, "provider": "Shazam", "error": str(error)}
    return recognize_from_bytes(audio_bytes)


def is_configured() -> bool:
    return True


def format_result(
    result: dict[str, Any] | None,
    language: str = "pt",
    show_source: bool = True,
) -> str:
    text = {
        "pt": {
            "source": "Fonte",
            "title": "Titulo",
            "artist": "Artista",
            "album": "Album",
            "release": "Lancamento",
            "unknown": "Desconhecido",
            "not_recognized": "Musica nao reconhecida.",
        },
        "en": {
            "source": "Source",
            "title": "Title",
            "artist": "Artist",
            "album": "Album",
            "release": "Release",
            "unknown": "Unknown",
            "not_recognized": "Song not recognized.",
        },
    }.get(language, {})

    if not result or not result.get("ok"):
        return str((result or {}).get("error") or text["not_recognized"])

    lines = []
    if show_source:
        lines.append(f"{text['source']}: Shazam")
    lines.extend(
        [
            f"{text['title']}: {result.get('title') or text['unknown']}",
            f"{text['artist']}: {result.get('artist') or text['unknown']}",
        ]
    )
    if result.get("album"):
        lines.append(f"{text['album']}: {result['album']}")
    if result.get("release_date"):
        lines.append(f"{text['release']}: {result['release_date']}")
    return "\n".join(lines)
