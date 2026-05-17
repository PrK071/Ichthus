# 🎵 ICHTUS
ICHTUS é um reconhecedor de músicas via microfone com interface gráfica em dark mode. Integra a **AudD API** para identificação em nuvem e possui uma engine de **fingerprinting local** ao estilo Shazam, com histórico de reconhecimentos, correções automáticas de metadados e atalhos rápidos para YouTube e Spotify.

ICHTUS is a microphone-based music recognizer with a dark mode GUI. It integrates the **AudD API** for cloud-based identification and includes a Shazam-style **local fingerprinting engine**, with recognition history, automatic metadata corrections, and quick links to YouTube and Spotify.

## Configuração / Setup

Crie um arquivo `.env` na raiz do projeto / Create a `.env` file at the project root:
```env
AUDD_API_URL=https://api.audd.io/
AUDD_API_TOKEN=seu_token_aqui
```
Obtenha um token em / Get a token at [audd.io](https://audd.io). O token `test` funciona para testes rápidos / The `test` token works for quick testing.

Instale as dependências / Install dependencies:
```bash
pip install customtkinter Pillow librosa sounddevice soundfile numpy scipy requests python-dotenv
```

## Como usar / Usage
```bash
python main.py
```