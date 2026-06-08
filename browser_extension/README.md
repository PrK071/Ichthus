# Ichthus - Extensao Chromium

A extensao captura o audio da aba atual e reconhece a musica diretamente no navegador.

## Como carregar

1. Abra `chrome://extensions`.
2. Ative `Modo do desenvolvedor`.
3. Clique em `Carregar sem compactacao`.
4. Selecione a pasta `browser_extension`.
5. Deixe uma aba tocando musica e clique em `Ouvir Musica`.

## Observacoes

- O app desktop nao precisa estar aberto.
- A extensao nao funciona em paginas internas como `chrome://`.
- Historico e reports ficam no storage local do navegador.
- O reconhecimento no navegador usa o projeto GPLv3 [Vibra](https://github.com/BayernMuller/vibra).
