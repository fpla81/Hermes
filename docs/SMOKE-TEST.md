# Smoke test ponta-a-ponta

Roteiro para validar o pipeline Hermes completo (captura → pieces → manifest →
prepared → validate → packets → minuta → DOCX). Roda contra o docker-compose
local com Postgres + Redis + MinIO + Mailhog + os 4 serviços do app.

## 0. Pré-requisitos

```bash
cp .env.example .env
pnpm install
uv sync
```

Edite o `.env` se quiser usar o Gemini real (`GEMINI_API_KEY=...`); caso
contrário roda com o stub.

## 1. Subir infra + serviços

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

Aguarde o `migrate` rodar até o fim (vai aplicar a 0005). Confira:

```bash
docker compose -f docker/docker-compose.yml ps
docker compose -f docker/docker-compose.yml logs -f web api worker playwright
```

Endpoints disponíveis:
- Web Next: http://localhost:3100
- API FastAPI: http://localhost:8000 (docs em `/docs`)
- Playwright service: http://localhost:8001
- MinIO console: http://localhost:9001 (user/pass `minioadmin`)
- Mailhog: http://localhost:8025

## 2. Login

Abra http://localhost:3100, peça o magic link, confira no Mailhog. Após o
login, copie o cookie de sessão se quiser bater na API direto via `curl`.

Os exemplos abaixo usam o atalho `INT` para o secret interno:

```bash
export INT="-H X-Hermes-Secret:dev-secret -H X-Hermes-User-Id:seu-email@x"
export API=http://localhost:8000
```

## 3. Criar um caso

Pela UI: `/cases/new`. Ou via API:

```bash
curl -s -X POST $API/cases $INT -H content-type:application/json \
  -d '{"numero_processo":"0001234-56.2023.5.06.0020","titulo":"Smoke"}' | jq
# guarda o id:
export CID=<uuid retornado>
```

## 4. Captura (Bem-te-vi → HTML + pieces)

```bash
curl -s -X POST $API/cases/$CID/capture $INT
# aguarde alguns segundos
curl -s $API/cases/$CID $INT | jq '.status, .has_manifest'
```

> **Stub vs real:** com `BEMTEVI_REAL_CAPTURE=false` (default) o playwright
> devolve HTML sintético — `pieces_json` ficará vazio. Para ver a extração
> real, gere um HTML de teste com a tabela e force via endpoint
> `/capture` do playwright service:
>
> ```bash
> curl -s -X POST http://localhost:8001/capture \
>   -H content-type:application/json \
>   -d '{"numero_processo":"0001234-56.2023.5.06.0020"}' | jq '.pieces'
> ```

## 5. Pieces e manifest (se o stub não populou)

Pela UI: cole o JSON na seção "2. Pieces e manifest" e clique "Gerar
manifest". Ou via API:

```bash
curl -s -X POST $API/cases/$CID/pieces $INT -H content-type:application/json \
  -d '{"pieces":[
    {"tipo":"Despacho de Admissibilidade do TRT","data":"15/03/2024","id":"100","local_path":"despacho.txt"},
    {"tipo":"Recurso de Revista","data":"10/01/2024","id":"101","local_path":"rr.txt"},
    {"tipo":"Agravo de Instrumento em Recurso de Revista","data":"01/04/2024","id":"102","local_path":"agravo.txt"}
  ]}' | jq '.has_manifest'

curl -s -X POST $API/cases/$CID/manifest $INT | jq '.has_manifest'
```

## 6. Subir arquivos preparados (anonimizados)

Pela UI: seção "3. Arquivos preparados". Ou via API:

```bash
# crie arquivos de teste
for f in despacho rr agravo; do
  printf 'Conteúdo do %s ' "$f" > /tmp/$f.txt
  for _ in $(seq 1 200); do printf 'lorem ipsum dolor sit amet ' >> /tmp/$f.txt; done
done

for f in despacho rr agravo; do
  curl -s -X POST $API/cases/$CID/prepared $INT \
    -F "file=@/tmp/$f.txt" | jq
done

curl -s $API/cases/$CID/prepared $INT | jq
```

## 7. Validar texto dos recursos

```bash
curl -s -X POST $API/cases/$CID/validate-resources $INT | jq '.status'
```

## 8. Packets (Celery)

```bash
curl -s -X POST $API/cases/$CID/packets $INT | jq
# aguarde alguns segundos e veja o índice:
curl -s $API/cases/$CID/packets $INT | jq '.packet_count, .sources[].filename'
# baixar o ndjson completo:
curl -s "$API/cases/$CID/packets?raw=1" $INT | head -3
```

No MinIO console deve aparecer `cases/$CID/packets.jsonl`.

## 9. Subir a minuta

```bash
cat <<'EOF' > /tmp/minuta.md
[[CORPO]]
PROCESSO Nº 0001234-56.2023.5.06.0020

RECURSO DE REVISTA DA RECLAMADA

TEMA - HORAS EXTRAS

Trata-se de recurso interposto pela reclamada contra acórdão regional.

[[TRANSCRICAO1]]
Trecho transcrito do acórdão regional para fundamentar.

[[CORPO]]
Conheço do recurso e dou provimento.
EOF

curl -s -X POST $API/cases/$CID/minuta $INT -H content-type:application/json \
  -d @<(jq -Rs '{text:.}' < /tmp/minuta.md) | jq '.has_minuta'
```

## 10. DOCX final (Celery)

```bash
curl -s -X POST $API/cases/$CID/docx $INT | jq
# aguarde, depois baixe via API:
curl -s -o /tmp/minuta.docx $API/cases/$CID/docx $INT
file /tmp/minuta.docx
```

Pela UI: o botão "Baixar minuta.docx" aparece na seção 7 quando `has_docx` fica
true. O download passa pelo proxy `/cases/$CID/docx` do Next, que injeta o
header de autenticação.

## 11. Limpeza

```bash
docker compose -f docker/docker-compose.yml down -v
```

## Troubleshooting

| Sintoma | Causa provável |
|---|---|
| `503 storage S3 não configurado` em `/prepared` ou `/docx` | `S3_BUCKET` ausente no .env do api/worker |
| `412 envie pieces antes de gerar o manifest` | esqueceu o POST `/pieces` |
| Task Celery não roda | worker não subiu — `docker compose logs worker` |
| `pieces.json` vazio após captura real | seletores da tabela do Bem-te-vi mudaram — ajustar `apps/playwright/src/hermes_playwright/extract.py` |
| DOCX corrompido | a minuta tem marcadores `[[CORPO]]` malformados ou `python-docx` não instalado no container do api/worker |
