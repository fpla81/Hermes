"""Parser do Despacho de Admissibilidade do TRT.

Recebe o texto do despacho e devolve um "blueprint" estruturado dos recursos
esperados: para cada recurso, identifica a parte recorrente, os temas
analisados e a conclusão (admitido / denegado / parcialmente admitido /
prejudicado / não conhecido) e o tipo de recurso (RR / Agravo).

Implementação: usa ``LLMProvider.analyze`` com prompt JSON estruturado. Em
modo stub (sem GEMINI_API_KEY), devolve um esqueleto vazio com aviso. Falha
graciosamente — qualquer erro de parse devolve ``{recursos: [], note: ...}``.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..llm import StubProvider, get_llm_provider

PROMPT_TEMPLATE = """Você é um analista jurídico do TST. Leia o despacho de admissibilidade do TRT abaixo e extraia, em JSON puro (sem ```), a lista de recursos analisados.

Para cada recurso, devolva:
- tipo: "recurso_revista" | "agravo_instrumento" | "agravo_interno" | "outro"
- parte: "reclamante" | "reclamada" | "reclamantes" | "reclamadas" | "ministerio_publico" | "outro"
- temas: lista de strings com os temas analisados PELO PRÓPRIO DESPACHO (substantivo, ex.: "Horas extras", "Negativa de prestação jurisdicional")
- conclusao: "admitido" | "denegado" | "parcialmente_admitido" | "prejudicado" | "nao_conhecido"

REGRAS CRÍTICAS PARA EXTRAÇÃO DE TEMAS:

1. Tema = capítulo de análise do DESPACHO (admissibilidade recursal). Identifique pela ESTRUTURA do despacho: cabeçalho/seção (geralmente em CAIXA ALTA ou taxonomia hierárquica do PJe, ex.: "DIREITO PROCESSUAL CIVIL E DO TRABALHO / ATOS PROCESSUAIS / NULIDADE / NEGATIVA DE PRESTAÇÃO JURISDICIONAL"), tipicamente seguido de "Alegação(ões)" e dos fundamentos de admissibilidade.

2. IGNORE tópicos que aparecem APENAS dentro de trechos transcritos de outras decisões. Despachos costumam reproduzir longos trechos da sentença, do acórdão regional ou dos embargos de declaração — esses trechos são CONTEXTO, não temas analisados pelo despacho. Se o despacho cola uma decisão que menciona "Tutela inibitória", "Dano moral coletivo" ou enumera obrigações de fazer, mas o despacho EM SI não tem cabeçalho/análise próprios sobre cada um desses pontos, NÃO os inclua como temas.

3. Critério prático: cada tema da lista deve corresponder a uma decisão de admissibilidade própria no despacho (admite/denega aquele ponto). Se o despacho denega o recurso "globalmente" por um único fundamento (ex.: ausência de prestação jurisdicional, ou inadmissibilidade processual), o recurso tem UM tema só.

4. Quando o despacho de fato analisa vários temas distintos com decisões próprias, liste todos. Se um tema é guarda-chuva (ex.: "Obrigações de fazer") e o despacho analisa sub-itens com decisões individuais, prefira o nome guarda-chuva como tema principal e cite os sub-itens entre parênteses no mesmo string apenas se isso for útil — não crie múltiplos temas para o mesmo capítulo de análise.

Além disso, devolva no nível raiz:
- acordao_regional_data: data do acórdão regional (Recurso Ordinário) em formato dd/mm/aaaa quando mencionada no despacho; senão null. Importante para definir o marco legal do Recurso de Revista.

Formato exato da resposta (apenas JSON, sem texto adicional):
{
  "recursos": [
    {"tipo": "...", "parte": "...", "temas": ["..."], "conclusao": "..."}
  ],
  "acordao_regional_data": "dd/mm/aaaa" | null
}

Despacho:
---
{text}
---
"""


def _normalize_blueprint(raw: dict[str, Any]) -> dict[str, Any]:
    recursos = raw.get("recursos", []) if isinstance(raw, dict) else []
    cleaned: list[dict[str, Any]] = []
    for item in recursos:
        if not isinstance(item, dict):
            continue
        cleaned.append({
            "tipo": str(item.get("tipo", "")).strip().lower() or "outro",
            "parte": str(item.get("parte", "")).strip().lower() or "outro",
            "temas": [str(t).strip() for t in (item.get("temas") or []) if str(t).strip()],
            "conclusao": str(item.get("conclusao", "")).strip().lower() or "",
        })
    acordao_data = raw.get("acordao_regional_data") if isinstance(raw, dict) else None
    if isinstance(acordao_data, str):
        acordao_data = acordao_data.strip() or None
    else:
        acordao_data = None
    return {"recursos": cleaned, "acordao_regional_data": acordao_data}


def _extract_json(text: str) -> dict[str, Any] | None:
    # tenta extrair o primeiro bloco JSON do texto (LLM pode prefixar/sufixar)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def parse_despacho(text: str) -> dict[str, Any]:
    provider = get_llm_provider()
    if isinstance(provider, StubProvider):
        return {
            "recursos": [],
            "note": "GEMINI_API_KEY ausente — adicione a chave para extrair o blueprint automaticamente.",
        }
    try:
        prompt = PROMPT_TEMPLATE.replace("{text}", text)
        response = provider.analyze(prompt)
    except Exception as exc:  # noqa: BLE001
        return {"recursos": [], "note": f"falha ao chamar LLM: {exc}"}
    parsed = _extract_json(response)
    if parsed is None:
        return {"recursos": [], "note": "resposta do LLM não veio em JSON válido"}
    return _normalize_blueprint(parsed)
