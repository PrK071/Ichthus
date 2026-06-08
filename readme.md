# Ichthus

Reconhecedor de musicas gratuito com app desktop e extensao Chromium. O desktop usa ShazamIO e a extensao usa Vibra/WebAssembly diretamente no navegador.

## Instalar

Requer Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Usar

```powershell
.\.venv\Scripts\python.exe main.py
```

No app, escolha a entrada de audio e clique em `Ouvir Musica`.
No Windows, tambem e possivel abrir `iniciar_ichthus.bat`.

## Extensao

1. Abra `chrome://extensions`.
2. Ative `Modo do desenvolvedor`.
3. Clique em `Carregar sem compactacao`.
4. Selecione `browser_extension`.
5. Deixe uma aba tocando musica e clique em `Ouvir Musica` na extensao.

A extensao reconhece a musica diretamente no navegador e nao depende do app desktop.

## Arquivos principais

```text
main.py                       inicia o app desktop
gui.py                        interface desktop
API_shazam.py                 reconhecimento com ShazamIO
browser_extension/            extensao Chromium
```
