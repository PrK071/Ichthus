# Ichthus

Reconhecedor de musicas com app desktop e extensao para navegador.

Ichthus grava alguns segundos de audio, consulta a API da AudD e entrega a musica com capa ou thumbnail, historico local e atalhos para YouTube e Spotify.

## Recursos

- Reconhecimento via AudD API.
- App desktop em dark mode com CustomTkinter.
- Extensao Chromium para Chrome, Edge, Brave e Opera.
- Historico com imagem, reports e correcoes locais.
- Links rapidos para YouTube e Spotify.
- Fallback de capa por iTunes, Deezer e YouTube.
- Idiomas PT/EN.

## App Desktop

Instale as dependencias:

```bash
pip install customtkinter Pillow librosa sounddevice soundfile numpy scipy requests python-dotenv
```

Crie um `.env` na raiz:

```env
AUDD_API_URL=https://api.audd.io/
AUDD_API_TOKEN=seu_token_audd_aqui
```

Rode:

```bash
python main.py
```

## Extensao

1. Abra `chrome://extensions`.
2. Ative `Modo do desenvolvedor`.
3. Clique em `Carregar sem compactacao`.
4. Selecione `browser_extension`.
5. Salve seu token AudD na extensao e clique em `Ouvir Musica`.

## Arquivos

```text
main.py             inicia o app desktop
gui.py              interface do Ichthus
API_audd.py         cliente da AudD API
browser_extension/  extensao Chromium
corrections.json    correcoes automaticas
history.json        historico local
```
