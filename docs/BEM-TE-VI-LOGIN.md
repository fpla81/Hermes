# Login Bem-te-vi pelo app

O Hermes tem um fluxo de login interativo: você clica em **Settings → Iniciar
login**, o Chrome abre, você se autentica normalmente, clica em **"Concluí o
login"** e o cookie fica salvo. Não precisa rodar nada no terminal no
dia-a-dia.

Mas tem **uma escolha de setup** que você faz **uma vez**: o serviço
``hermes-playwright`` precisa rodar onde há tela (no seu Mac, não dentro de
um container Docker headless).

## Setup recomendado (uma vez)

### 1. Pare o container playwright do compose

```bash
docker compose -f docker/docker-compose.yml stop playwright
docker compose -f docker/docker-compose.yml rm -f playwright
```

E remova/comente o serviço ``playwright`` do ``docker-compose.yml``, ou
adicione a flag ``profiles: ["disabled"]`` pra ele não subir mais.

### 2. Aponte o api/worker para o playwright local

No ``.env``:

```
PLAYWRIGHT_SERVICE_URL=http://host.docker.internal:8001
```

E reinicie api + worker:

```bash
docker compose -f docker/docker-compose.yml up -d --force-recreate api worker
```

### 3. Suba o playwright no Mac

```bash
./scripts/playwright-host.sh
```

Confirme em http://localhost:8001/health.

### 4. (Opcional) Auto-iniciar no login

```bash
# substitui o placeholder pelo path absoluto do repo
HERMES_ROOT="$(pwd)"
sed "s|{{HERMES_ROOT}}|$HERMES_ROOT|g" \
  scripts/com.hermes.playwright.plist.template \
  > ~/Library/LaunchAgents/com.hermes.playwright.plist

mkdir -p "$HERMES_ROOT/.logs"

launchctl load ~/Library/LaunchAgents/com.hermes.playwright.plist
launchctl start com.hermes.playwright
```

Pra remover:

```bash
launchctl unload ~/Library/LaunchAgents/com.hermes.playwright.plist
```

## Fluxo de login no dia-a-dia

1. Abra http://localhost:3100/settings
2. Clique **"Iniciar login"**
3. O Chromium abre na ``https://bemtevi.tst.jus.br/``
4. Faça o login normal (gov.br, certificado, etc.)
5. Volte ao app e clique **"Concluí o login"** → janela fecha, cookie salva
6. Pode capturar processos. O cookie dura até o Bem-te-vi expirá-lo (geralmente dias).

Se ao gerar uma captura o HTML voltar como tela de login, é hora de repetir o
fluxo acima.

## Troubleshooting

| Erro | Causa | Solução |
|---|---|---|
| 503 ``playwright service indisponível`` | api não consegue alcançar o playwright | confirme ``PLAYWRIGHT_SERVICE_URL`` e o serviço rodando em :8001 |
| 503 ``não foi possível abrir o Chromium headed`` | playwright rodando sem display (container ou SSH sem X11) | rode no Mac via ``./scripts/playwright-host.sh`` |
| Chromium abre mas a URL não carrega | o template ``BEMTEVI_LOGIN_URL`` aponta pra lugar inválido | ajuste no ``.env`` |
| ``BrowserContext.close()`` já fechado | você fechou o Chromium pelo X em vez de "Concluí o login" | tudo bem, recomece o fluxo — o cookie pode ter salvo mesmo assim |
