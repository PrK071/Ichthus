import io
import os
from typing import Any

import numpy as np
import requests
import soundfile as sf
from dotenv import load_dotenv

load_dotenv()

PLACEHOLDER_MARKERS = (
    "cole_",
    "_aqui",
    "your_",
    "seu_token",
    "token_audd",
    "placeholder",
)


def _read_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip().strip("\"'")


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return (
        not normalized
        or normalized in {"teste", "changeme", "change_me"}
        or any(marker in normalized for marker in PLACEHOLDER_MARKERS)
    )


AUDD_API_URL = _read_env("AUDD_API_URL", "https://api.audd.io/")
API_TOKEN = _read_env("AUDD_API_TOKEN")


def is_configured() -> bool:
    return not _is_placeholder(API_TOKEN)


def _audio_to_wav_buffer(audio: np.ndarray, sample_rate: int) -> io.BytesIO:
    """Converte o áudio numpy em WAV em memória para enviar à API."""
    audio = np.asarray(audio, dtype=np.float32).flatten()

    if audio.size == 0:
        raise ValueError("Áudio vazio. Nada foi gravado pelo microfone.")

    peak = float(np.max(np.abs(audio)))
    if peak > 0:
        audio = audio / peak

    buffer = io.BytesIO()
    sf.write(buffer, audio, sample_rate, format="WAV", subtype="PCM_16")
    buffer.seek(0)
    return buffer


def recognize_from_audio(audio: np.ndarray, sample_rate: int = 22050) -> dict[str, Any]:
    
    if not is_configured():
        return {
            "ok": False,
            "provider": "AudD",
            "error": "Configure AUDD_API_TOKEN no arquivo .env. Use test para testar ou cole um token real da AudD.",
        }

    try:
        buffer = _audio_to_wav_buffer(audio, sample_rate)
        response = requests.post(
            AUDD_API_URL,
            data={
                "api_token": API_TOKEN,
                "return": "apple_music,spotify",
            },
            files={"file": ("audio.wav", buffer, "audio/wav")},
            timeout=25,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        return {"ok": False, "provider": "AudD", "error": "Timeout: servidor demorou para responder."}
    except requests.exceptions.RequestException as e:
        return {"ok": False, "provider": "AudD", "error": f"Erro de rede: {e}"}
    except ValueError as e:
        return {"ok": False, "provider": "AudD", "error": str(e)}

    if data.get("status") != "success":
        return {
            "ok": False,
            "provider": "AudD",
            "error": data.get("error", {}).get("error_message") or data.get("error") or "Resposta sem sucesso da AudD.",
            "raw": data,
        }

    result = data.get("result")
    if not result:
        return {
            "ok": False,
            "provider": "AudD",
            "error": "AudD não reconheceu a música.",
            "raw": data,
        }

    return {
        "ok": True,
        "provider": "AudD",
        "title": result.get("title") or "Desconhecido",
        "artist": result.get("artist") or "Desconhecido",
        "album": result.get("album") or "",
        "release_date": result.get("release_date") or "",
        "label": result.get("label") or "",
        "raw": result,
    }


def format_result(result: dict[str, Any] | None) -> str:
    if not result:
        return "AudD: sem resposta."

    if not result.get("ok"):
        return f"AudD: {result.get('error', 'Música não reconhecida.')}"

    lines = [
        f"Fonte: {result.get('provider', 'AudD')}",
        f"Título: {result.get('title', 'Desconhecido')}",
        f"Artista: {result.get('artist', 'Desconhecido')}",
    ]
    if result.get("album"):
        lines.append(f"Álbum: {result['album']}")
    if result.get("release_date"):
        lines.append(f"Lançamento: {result['release_date']}")
    return "\n".join(lines)
