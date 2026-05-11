import librosa
import numpy as np
import sounddevice as sd


SAMPLE_RATE = 22050
RECORD_SECONDS = 10  

N_FFT = 2048
HOP_LENGTH = 512


def load_audio(path: str) -> np.ndarray:
    """Carrega um arquivo de áudio e retorna o sinal normalizado."""
    audio, _ = librosa.load(path, sr=SAMPLE_RATE, mono=True)
    return audio


def record_audio(device=None) -> np.ndarray:
    """Grava áudio do microfone e retorna o sinal normalizado."""
    print(f"Gravando por {RECORD_SECONDS} segundos...")
    audio = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=device,
    )
    sd.wait()
    print("Gravação finalizada.")

    audio = audio.flatten()


    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak

    return audio


def spectrogram(audio: np.ndarray) -> np.ndarray:
    """
    Gera um espectrograma em escala logarítmica (dB).

    Usar dB é FUNDAMENTAL para a detecção de picos funcionar:
    - A magnitude bruta do STFT varia em ordens de grandeza
    - Em dB, os valores ficam em uma faixa previsível (ex: -80 a 0)
    - Picos ficam bem definidos e o threshold faz sentido
    """
    S = librosa.stft(audio, n_fft=N_FFT, hop_length=HOP_LENGTH)
    magnitude = np.abs(S)

    # Referência = max do sinal, então 0 dB = pico máximo
    # Resultado: escala de ~-80 a 0 dB
    S_db = librosa.amplitude_to_db(magnitude, ref=np.max)
    return S_db
