import librosa
import numpy as np
import sounddevice as sd


SAMPLE_RATE = 22050
RECORD_SECONDS = 10  

N_FFT = 2048
HOP_LENGTH = 512


def load_audio(path: str) -> np.ndarray:
    audio, _ = librosa.load(path, sr=SAMPLE_RATE, mono=True)
    return audio


def record_audio(device=None) -> np.ndarray:
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
    S = librosa.stft(audio, n_fft=N_FFT, hop_length=HOP_LENGTH)
    magnitude = np.abs(S)


    S_db = librosa.amplitude_to_db(magnitude, ref=np.max)
    return S_db
