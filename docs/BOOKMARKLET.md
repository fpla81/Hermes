# Captura via bookmarklet

Como funciona:

1. Você abre o Bem-te-vi normalmente no seu Chrome, faz login normal, navega
   até a página &quot;Peças&quot; do processo.
2. Clica num favorito da barra: **"Enviar pro Hermes"**.
3. O favorito é um JavaScript que pega o HTML da página, encontra o número
   CNJ, e POSTa pra API do Hermes com o seu token pessoal.
4. O Hermes responde com o ID do caso e abre a página do caso numa aba
   nova, já com o status `captured` e a lista de peças extraída.

## Instalação (uma vez)

1. Abra http://localhost:3100/settings logado no Hermes.
2. Você vai ver um botão **"Enviar pro Hermes"**.
3. **Arraste o botão para a barra de favoritos** do Chrome.

Pronto. O token fica embutido no favorito.

## Usar

1. No Bem-te-vi, vai até a página de Peças do processo.
2. Clica no favorito **"Enviar pro Hermes"**.
3. Aba nova abre direto no caso do Hermes com pieces e HTML já populados.
4. Segue o pipeline a partir da seção 2 (manifest → prepared → ... → DOCX).

## Revogar / trocar token

Troque `HERMES_INTERNAL_SECRET` no `.env` e recrie api+web. Todos os tokens
emitidos param de funcionar.

## Limitações conhecidas

- O bookmarklet usa o `localhost:8000` da API. Se você acessar o Hermes de
  outra máquina, o bookmarklet vai falhar (CORS / unreachable). Pra
  produção, sirva a API num domínio fixo e atualize `NEXT_PUBLIC_API_URL`
  no `.env` antes de gerar o bookmarklet.
- A regex de detecção do CNJ pega qualquer match no DOM/URL. Se a página
  tiver mais de um número, pega o primeiro. Em prática, na página de
  Peças isso é estável.
- O CORS da API está liberado para `*.bemtevi.tst.jus.br` (regex). Se o
  Bem-te-vi mudar de domínio, ajuste em
  `apps/api/src/hermes_api/main.py:add_middleware`.
