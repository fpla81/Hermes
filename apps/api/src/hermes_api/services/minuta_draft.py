"""Gera rascunho de minuta em Markdown estruturado a partir do dossiê.

Saída usa os marcadores ``[[CORPO]]`` / ``[[TRANSCRICAO1]]`` / ``[[EMENTA]]``
esperados por ``services/docx.py``. Regras de redação seguem o documento
``decisao.md`` da skill original do gabinete.

Sem ``GEMINI_API_KEY`` devolve um esqueleto previsível com TODOs.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ..llm import StubProvider, get_llm_provider
from .analysis_themed import PARTE_LABEL, TIPO_LABEL

# Datas-chave para o marco legal do RR (vide decisao.md "Marco Legal")
LEI_13015 = date(2014, 9, 20)
LEI_13467 = date(2017, 11, 11)


def compute_marco_legal(acordao_regional_data: str | None) -> str | None:
    """Devolve o marco legal padronizado do RR a partir da data do acórdão regional.

    Aceita datas em ``dd/mm/aaaa`` ou ``aaaa-mm-dd``. Devolve None se não
    conseguir parsear — chamador deve registrar lacuna.
    """
    if not acordao_regional_data:
        return None
    parsed: date | None = None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(acordao_regional_data.strip(), fmt).date()
            break
        except ValueError:
            continue
    if parsed is None:
        return None
    if parsed < LEI_13015:
        return "INTERPOSTO ANTERIORMENTE À VIGÊNCIA DA LEI Nº 13.015/2014"
    if parsed < LEI_13467:
        return "INTERPOSTO ANTERIORMENTE À VIGÊNCIA DA LEI Nº 13.467/2017"
    return "INTERPOSTO NA VIGÊNCIA DA LEI Nº 13.467/2017"


VALID_MARKERS = (
    "[[CORPO]]",
    "[[ALERTA_VERMELHO]]",
    "[[EMENTA]]",
    "[[TRANSCRICAO1]]",
    "[[TRANSCRICAO2]]",
    "[[TRANSCRICAO3]]",
    "[[NOTA]]",
)


PROMPT_TEMPLATE = """Você é assistente jurídico do TST. Produza uma MINUTA DE DECISÃO MONOCRÁTICA a partir do dossiê estruturado abaixo.

# MARCADORES VÁLIDOS

A minuta DEVE usar apenas estes marcadores, sempre em linha própria, ANTES de cada bloco de texto a que se aplicam:

- `[[CORPO]]` — texto corrido (relatórios, análises, cabeçalhos, dispositivo). Padrão.
- `[[TRANSCRICAO1]]` — trecho LITERAL do acórdão regional ou de outras peças.
- `[[TRANSCRICAO2]]` / `[[TRANSCRICAO3]]` — transcrições aninhadas (citação dentro de citação).
- `[[EMENTA]]` — ementa de julgado citado como precedente.
- `[[NOTA]]` — nota de rodapé.
- `[[ALERTA_VERMELHO]]` — aviso interno em vermelho (usar só se houver problema impeditivo).

NÃO use texto fora de blocos com marcador.

# ESTRUTURA CANÔNICA

Para cada recurso analisado no dossiê, produza:

```
[[CORPO]]
{CABEÇALHO DO RECURSO}

[[CORPO]]
TEMA - {DESCRIÇÃO 1}

[[CORPO]]
{Relatório temático do acórdão recorrido, conforme fórmula base abaixo}

[[TRANSCRICAO1]]
{trecho LITERAL do acórdão recorrido}

[[CORPO]]
(Se houver Embargos de Declaração no ponto: relatório dos EDs.)

[[TRANSCRICAO1]]
(Se houver EDs: trecho LITERAL.)

[[CORPO]]
{Resumo do recurso conforme fórmula base abaixo — fundamentos PRIMEIRO, permissivos DEPOIS}

[[CORPO]]
{Análise jurídica do tema, com conclusão}

[[CORPO]]
TEMA - {DESCRIÇÃO 2}
...
```

Ao final de TODOS os recursos:

```
[[CORPO]]
DISPOSITIVO

{Conclusão final com fórmula apropriada}
```

# CABEÇALHO DE RECURSO

Modelo exato:

- 1 recurso só:
  `RECURSO DE REVISTA DA PARTE RECLAMADA INTERPOSTO NA VIGÊNCIA DA LEI Nº 13.467/2017`
  ou
  `AGRAVO DE INSTRUMENTO EM RECURSO DE REVISTA DA PARTE RECLAMANTE INTERPOSTO NA VIGÊNCIA DA LEI Nº 13.467/2017`

- Múltiplos recursos: numerar `I -`, `II -`, `III -` na ordem analisada:
  `I - AGRAVO DE INSTRUMENTO EM RECURSO DE REVISTA DA PARTE RECLAMADA ...`
  `II - AGRAVO DE INSTRUMENTO EM RECURSO DE REVISTA DA PARTE RECLAMANTE ...`
  `III - RECURSO DE REVISTA DA PARTE RECLAMADA ...`

O MARCO LEGAL pré-calculado é: {marco_legal}
Se vier null/vazio: OMITA o marco legal e adicione uma nota em [[ALERTA_VERMELHO]] no topo dizendo "Marco legal não definido — confirmar data do acórdão regional."

# FÓRMULAS BASE

## Resumo do acórdão recorrido (temático)

```
O Eg. TRT de origem [negou/deu] provimento ao [Recurso Ordinário/Agravo de Petição] [da/do] [Reclamada/Reclamante], ao fundamento de que ... Eis as razões de decidir:
```

(seguido de `[[TRANSCRICAO1]]` com o trecho)

## Resumo do recurso

```
No Recurso de Revista, [a Reclamada/o Reclamante] [alega/aduz/sustenta/argumenta] que ... Aponta violação aos arts. ... Indica contrariedade à Súmula nº ... Indica contrariedade à Orientação Jurisprudencial nº ... Invoca o precedente ... Colaciona arestos à divergência.
```

REGRA RÍGIDA: fundamentos argumentativos PRIMEIRO; permissivos DEPOIS. Texto direto, SEM bullets.

Permissivos agrupados por diploma. Exemplo:
`Aponta violação aos arts. 5º, II e LV, e 7º, XXVI, da Constituição; 832 da CLT; 489, § 1º, do CPC; e 944 do Código Civil.`

# DISPOSITIVO

Use a fórmula adequada:

- AI com resultado desfavorável → `nego seguimento ao Agravo de Instrumento`. NUNCA "nego provimento ao Agravo de Instrumento".
- AI provido para destrancar o RR → `dou provimento ao Agravo de Instrumento` ou `dou seguimento ao Agravo de Instrumento`.
- RR → `conheço e dou provimento ao Recurso de Revista` / `conheço e nego provimento ao Recurso de Revista` / `não conheço do Recurso de Revista`.

# ESTILO

- Nomes da Corte: `Eg. TRT`, `TRT`, `Corte Regional`. NUNCA `Tribunal Regional` isolado.
- `Constituição da República` / `Constituição` / `Carta Magna`. NUNCA `Constituição Federal` nem `CF`.
- `Código Civil` por extenso. NUNCA `CC`.
- Funções processuais com inicial maiúscula quando designam parte: Reclamante, Reclamada, Embargante, Agravante, Recorrente, Recorrida. Em adjetivo, minúsculo: "acórdão recorrido".
- Caixa alta preservada em títulos: "PARTE RECLAMADA", não "PARTE Reclamada".
- NÃO numerar temas. Use `TEMA - DANO EXISTENCIAL - JORNADA EXTENUANTE`, nunca `TEMA Nº 1 - DANO EXISTENCIAL`.
- Separar termos do tema com ` - ` (espaço + hífen + espaço). NUNCA com `. ` (ponto-espaço).
- Latinismos (`in casu`, `data venia`, etc.) e frases decisórias (`conheço`, `dou provimento`) NÃO precisam de markdown — o renderizador formata automaticamente.
- Se quiser destacar trecho em transcrição, use `***...***` (negrito+itálico). Após qualquer destaque, adicionar linha:
  `(destaques acrescidos)` em `[[CORPO]]`.

# EXEMPLO CANÔNICO MÍNIMO (1 RR, 2 temas)

```
[[CORPO]]
RECURSO DE REVISTA DA PARTE RECLAMADA INTERPOSTO NA VIGÊNCIA DA LEI Nº 13.467/2017

[[CORPO]]
TEMA - HORAS EXTRAS - INTERVALO INTRAJORNADA

[[CORPO]]
O Eg. TRT de origem negou provimento ao Recurso Ordinário da Reclamada, ao fundamento de que a supressão parcial do intervalo intrajornada gera direito ao pagamento da hora suprimida com acréscimo de 50%. Eis as razões de decidir:

[[TRANSCRICAO1]]
Como cediço, a supressão do intervalo intrajornada implica pagamento da hora suprimida...

[[CORPO]]
No Recurso de Revista, a Reclamada alega que a redação do art. 71, § 4º, da CLT, após a Reforma Trabalhista, autoriza o pagamento apenas do tempo suprimido. Aponta violação ao art. 71, § 4º, da CLT.

[[CORPO]]
Conheço do Recurso de Revista. No mérito, dou provimento para limitar a condenação ao tempo efetivamente suprimido, com acréscimo de 50%, sem repercussões em outras parcelas.

[[CORPO]]
TEMA - DANO MORAL - QUANTUM INDENIZATÓRIO

[[CORPO]]
... (segue mesma estrutura)

[[CORPO]]
DISPOSITIVO

Conheço do Recurso de Revista e, no mérito, dou parcial provimento, nos termos da fundamentação.
```

# DIRETIVA FINAL

Devolva APENAS o markdown da minuta. Sem prefácio, sem código, sem comentários. Comece na primeira linha com `[[CORPO]]`. Termine com a conclusão do `DISPOSITIVO`.

# DOSSIÊ

{dossie}
"""


def _stub_minuta(numero: str, pieces: list[dict[str, Any]]) -> str:
    chunks = ["[[CORPO]]", f"PROCESSO Nº {numero}", ""]
    chunks.append(
        "Trata-se de TODO (configurar GEMINI_API_KEY para gerar o rascunho real)."
    )
    for p in pieces:
        tipo = TIPO_LABEL.get(p.get("tipo", ""), p.get("tipo", ""))
        parte = PARTE_LABEL.get(p.get("parte", ""), p.get("parte"))
        header = f"{tipo}"
        if parte:
            header += f" — {parte}"
        chunks.append("")
        chunks.append("[[CORPO]]")
        chunks.append(header.upper())
        chunks.append("")
        chunks.append("TODO: análise.")
    chunks.append("")
    chunks.append("[[CORPO]]")
    chunks.append("DISPOSITIVO")
    chunks.append("")
    chunks.append("TODO: dispositivo.")
    return "\n".join(chunks)


def _validate_minuta_structure(text: str) -> list[str]:
    """Devolve lista de problemas estruturais. Vazia = ok."""
    problems: list[str] = []
    stripped = text.lstrip()
    if not stripped.startswith("[[CORPO]]"):
        problems.append("não começa com [[CORPO]]")
    if "TEMA -" not in text and "TEMA-" not in text:
        problems.append("sem cabeçalho de TEMA")
    if "DISPOSITIVO" not in text.upper():
        problems.append("sem seção DISPOSITIVO")
    # marcadores desconhecidos (typos)
    import re

    for match in re.finditer(r"\[\[[A-Z0-9_]+\]\]", text):
        marker = match.group(0)
        if marker not in VALID_MARKERS:
            problems.append(f"marcador desconhecido: {marker}")
            break
    return problems


def build_minuta_draft(
    numero_processo: str,
    pieces: list[dict[str, Any]],
    dossie: dict[str, Any] | None,
    *,
    acordao_regional_data: str | None = None,
) -> str:
    provider = get_llm_provider()
    if isinstance(provider, StubProvider) or not dossie or not dossie.get("recursos"):
        return _stub_minuta(numero_processo, pieces)
    import json as _json

    marco_legal = compute_marco_legal(acordao_regional_data) or "(não informado)"

    prompt = (
        PROMPT_TEMPLATE.replace("{dossie}", _json.dumps(dossie, ensure_ascii=False, indent=2))
        .replace("{numero}", numero_processo)
        .replace("{marco_legal}", marco_legal)
    )
    try:
        raw = provider.analyze(prompt).strip()
    except Exception as exc:  # noqa: BLE001
        return f"[[CORPO]]\nTODO: falha ao gerar minuta ({exc}).\n"

    problems = _validate_minuta_structure(raw)
    if problems:
        warning = (
            "<!-- AVISO: estrutura possivelmente incompleta: "
            + "; ".join(problems)
            + " -->\n"
        )
        return warning + raw
    return raw
