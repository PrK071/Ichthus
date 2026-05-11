"""
Reconhecimento de músicas via AudD API.

Não precisa baixar nada — manda o áudio gravado direto pra API
e ela identifica contra um catálogo de milhões de músicas.

Dependências:
    pip install requests soundfile

Setup:
    1. Cria conta grátis em https://audd.io  (300 reconhecimentos/mês grátis)
    2. Pega seu token no dashboard
    3. Coloca no .env:  AUDD_API_TOKEN=seu_token_aqui
"""

import os
import io
import requests
import numpy as np
import soundfile as sf
from dotenv import load_dotenv

load_dotenv()

AUDD_API_URL = "https://api.audd.io/"
API_TOKEN    = os.getenv("AUDD_API_TOKEN", "test")
# "test" funciona sem token mas tem limite bem baixo — use só pra testar


def recognize_from_audio(audio: np.ndarray, sample_rate: int = 22050) -> dict | None:
    """
    Recebe um array numpy de áudio e manda pra AudD identificar.

    Retorna um dict com os dados da música se encontrar, None se não encontrar.

    Exemplo de retorno:
        {
            "title":        "Wonderwall",
            "artist":       "Oasis",
            "album":        "(What's the Story) Morning Glory?",
            "release_date": "1995-10-02",
            "label":        "Epic",
        }
    """
    # Converte o array numpy pra bytes WAV em memória (sem salvar arquivo)
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

        return None  # música não encontrada no catálogo

    except requests.exceptions.Timeout:
        print("[AudD] Timeout — servidor demorou pra responder.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[AudD] Erro na requisição: {e}")
        return None


def format_result(result: dict) -> str:
    """Formata o resultado pra exibir na GUI."""
    if not result:
        return "Música não identificada."

    lines = [
        f"🎵 {result['title']}",
        f"👤 {result['artist']}",
    ]
    if result.get("album"):
        lines.append(f"💿 {result['album']}")
    if result.get("release_date"):
        lines.append(f"📅 {result['release_date']}")

    return "\n".join(lines)
