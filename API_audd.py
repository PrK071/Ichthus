import os
import io
import requests
import numpy as np
import soundfile as sf
from dotenv import load_dotenv

load_dotenv()

AUDD_API_URL = "https://api.audd.io/"
API_TOKEN    = os.getenv("AUDD_API_TOKEN", "test")


def recognize_from_audio(audio: np.ndarray, sample_rate: int = 22050) -> dict | None:

    buffer = io.BytesIO()
    sf.write(buffer, audio, sample_rate, format="WAV")
    buffer.seek(0)

    try:
        response = requests.post(
            AUDD_API_URL,
            data={"api_token": API_TOKEN, "return": "apple_music,spotify"},
            files={"file": ("audio.wav", buffer, "audio/wav")},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success" and data.get("result"):
            result = data["result"]
            return {
                "title":        result.get("title", "Desconhecido"),
                "artist":       result.get("artist", "Desconhecido"),
                "album":        result.get("album", ""),
                "release_date": result.get("release_date", ""),
                "label":        result.get("label", ""),
            }

        return None 

    except requests.exceptions.Timeout:
        print("[AudD] Timeout — servidor demorou pra responder.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[AudD] Erro na requisição: {e}")
        return None


def format_result(result: dict) -> str:
    if not result:
        return 

    lines = [
        f"{result['title']}",
        f"{result['artist']}",
    ]
    if result.get("album"):
        lines.append(f"{result['album']}")
    if result.get("release_date"):
        lines.append(f"{result['release_date']}")

    return "\n".join(lines)
