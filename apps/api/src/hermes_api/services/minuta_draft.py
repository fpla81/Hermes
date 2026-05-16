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
- `[[TRANSCRICAO1]]` — trecho LITERAL do acórdão regional ou de outras peças. No dossiê, `acordao_recorrido_transcricao` e `embargos_transcricao` chegam como ARRAYS de strings (um item por parágrafo). Você DEVE emitir CADA item do array em SUA PRÓPRIA LINHA de markdown dentro do bloco `[[TRANSCRICAO1]]`, nessa ordem, sem concatenar. NUNCA junte dois parágrafos numa só linha; NUNCA omita um item; NUNCA reformule o conteúdo dos parágrafos.
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

# LÓGICA RR × AIRR (CRÍTICA)

Quando o dossiê contém AGRAVO DE INSTRUMENTO **e** RECURSO DE REVISTA DA MESMA PARTE:

- Para cada tema, decidir sob qual cabeçalho ele entra, com base na admissibilidade do despacho:
  - Tema **admitido** no despacho → entra sob o cabeçalho do RR.
  - Tema **denegado** no despacho **e** que o AIRR ataca → entra sob o cabeçalho do AIRR.
  - Se o tema aparece em ambos recursos do dossiê (RR admitiu, mas o AIRR também o discute): trata sob o RR; é desnecessário repetir no AIRR.

- Quantos cabeçalhos aparecem:
  - Se a parte teve RR **integralmente admitido**: só o cabeçalho do RR.
  - Se a parte teve RR **integralmente denegado** e há AIRR: só o cabeçalho do AIRR (em julgamento só o AIRR).
  - Se foi parcial: dois cabeçalhos, AIRR primeiro (`I -`), RR depois (`II -`).

- Múltiplas partes geram múltiplos cabeçalhos independentes. Ex.: AIRR Reclamada + RR Reclamada + AIRR Reclamante.

# HIERARQUIA QUANDO HÁ AGRAVO INTERNO

Quando o caso envolve **Agravo Interno** (peça do tipo `agravo_interno`), o relatório de cada tema deve trazer os recursos na seguinte ordem cronológica/lógica:

1. Relatório do Recurso de Revista (alegações originais da parte recorrente).
2. Relatório do Agravo de Instrumento, **se** estiver sendo examinado.
3. Relatório do Agravo Interno.

# TEMPOS VERBAIS POR RECURSO EM JULGAMENTO

Identifique o recurso EM JULGAMENTO (o mais recente na cadeia) e ajuste os tempos verbais conforme abaixo:

- Em sede de **Recurso de Revista** (sem AIRR/AInterno): o RR usa PRESENTE.
- Em sede de **Agravo de Instrumento** (RR denegado): o RR vai pro PASSADO; o AIRR usa PRESENTE.
- Em sede de **Agravo Interno**: o RR vai pro PASSADO; o AIRR vai pro PASSADO; o Agravo Interno usa PRESENTE.

Verbos para o PRESENTE: alega, aduz, sustenta, argumenta, reitera, indica, aponta, invoca, colaciona.
Verbos para o PASSADO: alegou, aduziu, sustentou, argumentou, reiterou, indicou, apontou, invocou, colacionou.

A regra geral: o recurso que está SENDO julgado AGORA narra-se no presente; os recursos anteriores (já consumados na cadeia) vão no passado.

# FÓRMULAS DE ATALHO PARA REPETIÇÃO

Avalie, comparando as alegações de cada recurso, se um recurso superior **essencialmente repete** as alegações já apresentadas. Se sim, **NÃO repita** o relatório completo: use a fórmula de atalho.

- Se o Agravo de Instrumento limita-se a reiterar as alegações do Recurso de Revista, no lugar do relatório do AIRR, escrever apenas:
  > Reitera as alegações no Agravo de Instrumento.

- Se o Agravo Interno limita-se a reiterar as alegações dos recursos anteriores, em sede de Agravo Interno, ao invés de uma frase para o AIRR e outra para o Agravo Interno, usar a fórmula COMPACTA UNIFICADA em UMA ÚNICA frase, no lugar dos dois relatórios:
  > No Agravo de Instrumento e no presente Agravo Interno, [a Reclamada/o Reclamante] reitera as alegações.

Critério de "essencialmente reitera": os fundamentos argumentativos e permissivos são os mesmos. Diferenças apenas estilísticas, ou inclusão de uma alegação processual nova adicional, NÃO descaracterizam a reiteração — use a fórmula e adicione, em frase própria, apenas a alegação nova relevante.

Se houver alegação juridicamente nova (não meramente formal), faça o relatório completo desse recurso.

# ESTRUTURA POR TEMA (OBRIGATÓRIA, NESTA ORDEM)

Para CADA tema, sob seu cabeçalho de recurso, escrever exatamente nesta sequência:

```
[[CORPO]]
TEMA - {DESCRIÇÃO}

[[CORPO]]
(i) Relatório do acórdão regional no ponto — fórmula:
"O Eg. TRT de origem [negou/deu] provimento ao Recurso Ordinário [da/do]
[Reclamada/Reclamante], ao fundamento de que ... [FÓRMULA DE TRANSIÇÃO]"

A FÓRMULA DE TRANSIÇÃO é o último período do parágrafo (i), no MESMO `[[CORPO]]` do resumo, terminando com dois-pontos. Escolha UMA das três e VARIE entre temas (não repetir a mesma em todos os temas):
- "Eis o teor do acórdão regional:"
- "Eis os termos do acórdão regional:"
- "Esses, os termos do acórdão regional:"

NÃO crie bloco separado para a frase de transição — ela faz parte do parágrafo (i).

[[TRANSCRICAO1]]
(ii) Transcrição LITERAL do acórdão regional no ponto.

[[CORPO]]
(Se houver Embargos de Declaração no tema)
Relatório do acórdão dos EDs no ponto, encerrando com a mesma FÓRMULA DE TRANSIÇÃO (variando entre as 3 opções).

[[TRANSCRICAO1]]
(Se houver EDs) Transcrição LITERAL.

[[CORPO]]
(iii) Relatório do Recurso de Revista no ponto — SEMPRE COMPLETO (alegações + permissivos agrupados), ajustando o tempo verbal conforme o recurso em julgamento (presente se o RR está sendo julgado; passado se o julgamento é de AIRR ou Agravo Interno). Fórmula:
"No Recurso de Revista, [a Reclamada/o Reclamante] [alega/alegou/sustenta/sustentou] que ... [Aponta/Apontou] violação aos arts. ... [Indica/Indicou] contrariedade à Súmula nº ... [Invoca/Invocou] o precedente ... [Colaciona/Colacionou] arestos à divergência."

[[CORPO]]
(iv) Relatório do Agravo de Instrumento no ponto — SINTETIZADO quando há RR no mesmo tema (não re-listar permissivos já exauridos no relatório do RR). Ajustar tempo verbal conforme o recurso em julgamento. Fórmula:
"No Agravo de Instrumento, [a Reclamada/o Reclamante] [reitera/reiterou] que ... [continua com os pontos centrais argumentativos, SEM repetir 'Aponta violação aos arts. ...' nem 'Indica contrariedade à Súmula nº ...']."

OU, se o AIRR essencialmente reitera o RR:
"Reitera as alegações no Agravo de Instrumento."

Incluir quando o tema está sendo julgado em sede de AIRR (denegado pelo despacho) OU como parte da hierarquia quando há Agravo Interno.

[[CORPO]]
(v) Relatório do Agravo Interno no ponto, quando houver — SINTETIZADO (não re-listar permissivos). Fórmula:
"No Agravo Interno, [a Reclamada/o Reclamante] argumenta que ... [pontos centrais novos do agravo interno]."

OU, se o Agravo Interno essencialmente reitera os recursos anteriores, usar a fórmula COMPACTA UNIFICADA em UMA frase, substituindo (iv) E (v):
"No Agravo de Instrumento e no presente Agravo Interno, [a Reclamada/o Reclamante] reitera as alegações."

[[CORPO]]
(vi) Análise jurídica do tema, com conclusão na fórmula adequada (`conheço/não conheço`, `dou/nego provimento` para RR; `nego seguimento` ou `dou provimento ao Agravo de Instrumento` para AIRR; `dou/nego provimento ao Agravo Interno`).
```

# FÓRMULAS BASE

## Resumo do acórdão recorrido (temático)

```
O Eg. TRT de origem [negou/deu] provimento ao [Recurso Ordinário/Agravo de Petição] [da/do] [Reclamada/Reclamante], ao fundamento de que ... [Eis o teor | Eis os termos | Esses, os termos] do acórdão regional:
```

(seguido de `[[TRANSCRICAO1]]` com o trecho)

VARIE entre as três fórmulas de transição quando houver mais de um tema.

## Fórmula do Recurso de Revista (SEMPRE COMPLETA)

```
No Recurso de Revista, [a Reclamada/o Reclamante] [alega/aduz/sustenta/argumenta] (ou [alegou/aduziu/sustentou/argumentou], conforme tempo verbal) que ... Aponta (ou Apontou) violação aos arts. ... Indica (ou Indicou) contrariedade à Súmula nº ... Indica (ou Indicou) contrariedade à Orientação Jurisprudencial nº ... Invoca (ou Invocou) o precedente ... Colaciona (ou Colacionou) arestos à divergência.
```

REGRA RÍGIDA: fundamentos argumentativos PRIMEIRO; permissivos DEPOIS. Texto direto, SEM bullets.

Permissivos agrupados por diploma. Exemplo:
`Aponta violação aos arts. 5º, II e LV, e 7º, XXVI, da Constituição; 832 da CLT; 489, § 1º, do CPC; e 944 do Código Civil.`

O relatório do RR é o PONTO DE PARTIDA sempre que o tema chegou ao TST por via recursal — inclusive em sede de AIRR ou Agravo Interno (apenas migrando os verbos para o passado).

## Fórmula do AIRR (SINTETIZADA quando há RR no tema)

```
No Agravo de Instrumento, [a Reclamada/o Reclamante] [reitera/reiterou] que ... [pontos centrais sem re-listar permissivos].
```

NÃO repita "Aponta violação aos arts. ..." nem "Indica contrariedade à Súmula nº ..." — esses já foram exauridos no relatório do RR; o relatório do AIRR só sintetiza o reataque argumentativo.

Se o AIRR limita-se a reiterar tudo: usar a fórmula de atalho ("Reitera as alegações no Agravo de Instrumento.").

## Fórmula do Agravo Interno (SINTETIZADA)

```
No Agravo Interno, [a Reclamada/o Reclamante] argumenta que ... [pontos centrais novos do agravo interno].
```

Se reitera tudo: usar a fórmula COMPACTA UNIFICADA em UMA frase única, no lugar dos dois relatórios (AIRR + Agravo Interno):

```
No Agravo de Instrumento e no presente Agravo Interno, [a Reclamada/o Reclamante] reitera as alegações.
```

# DISPOSITIVO

Use a fórmula adequada:

- AI com resultado desfavorável → `nego seguimento ao Agravo de Instrumento`. NUNCA "nego provimento ao Agravo de Instrumento".
- AI provido para destrancar o RR → `dou provimento ao Agravo de Instrumento` ou `dou seguimento ao Agravo de Instrumento`.
- RR → `conheço e dou provimento ao Recurso de Revista` / `conheço e nego provimento ao Recurso de Revista` / `não conheço do Recurso de Revista`.

# LINGUAGEM NEUTRA DAS PARTES (REGRA RÍGIDA)

As peças foram pré-anonimizadas: nomes das partes foram substituídos por
placeholders canônicos `RECLAMANTE_1`, `RECLAMANTE_2`, `RECLAMADA_1`,
`RECLAMADA_2` etc.

Na minuta:

- NUNCA reproduza o placeholder cru em `[[CORPO]]`. Sempre traduza para a
  forma neutra abaixo. Em `[[TRANSCRICAO*]]`, mantenha o placeholder como
  está (o pós-processamento resolverá).
- Forma neutra em texto corrido:
  - Uma parte só do tipo: `a parte Reclamante` / `a parte Reclamada`.
  - Múltiplas: `a primeira parte Reclamante`, `a segunda parte Reclamante`,
    `a primeira parte Reclamada`, `a segunda parte Reclamada` etc.
- NUNCA use pronome ou artigo de gênero referente à parte: NÃO escreva
  "o Reclamante", "a Reclamada" (como artigo+substantivo), "ele", "ela",
  "do Reclamante", "à Reclamada". Sempre "a parte Reclamante / Reclamada".
- Exceção: nas fórmulas decisórias canônicas (`conheço do Recurso de Revista da parte Reclamada`, `nego provimento ao Recurso de Revista da parte Reclamante`), use a forma com `da parte`.
- Para Ministério Público, mantenha "Ministério Público do Trabalho" (não há gênero a evitar).

# ESTILO

- Nomes da Corte: `Eg. TRT`, `TRT`, `Corte Regional`. NUNCA `Tribunal Regional` isolado.
- `Constituição da República` / `Constituição` / `Carta Magna`. NUNCA `Constituição Federal` nem `CF`.
- `Código Civil` por extenso. NUNCA `CC`.
- Funções processuais aparecem em prosa apenas dentro da forma neutra "a parte Reclamante / Reclamada" (vide regra de linguagem neutra acima). Em títulos de cabeçalho ainda em caixa alta: "PARTE RECLAMADA", "PARTE RECLAMANTE".
- Caixa alta preservada em títulos: "PARTE RECLAMADA", não "PARTE Reclamada".
- NÃO numerar temas. Use `TEMA - DANO EXISTENCIAL - JORNADA EXTENUANTE`, nunca `TEMA Nº 1 - DANO EXISTENCIAL`.
- Separar termos do tema com ` - ` (espaço + hífen + espaço). NUNCA com `. ` (ponto-espaço).
- Latinismos (`in casu`, `data venia`, etc.) e frases decisórias (`conheço`, `dou provimento`) NÃO precisam de markdown — o renderizador formata automaticamente.
- Se quiser destacar trecho em transcrição, use `***...***` (negrito+itálico). Após qualquer destaque, adicionar linha:
  `(destaques acrescidos)` em `[[CORPO]]`.

# EXEMPLOS CANÔNICOS

## CENÁRIO 1 — Em sede de Recurso de Revista (RR sendo julgado agora)

```
[[CORPO]]
RECURSO DE REVISTA DA PARTE RECLAMADA INTERPOSTO NA VIGÊNCIA DA LEI Nº 13.467/2017

[[CORPO]]
TEMA - DANO MORAL - QUANTUM INDENIZATÓRIO

[[CORPO]]
O Eg. TRT da 4ª Região deu provimento parcial ao Recurso Ordinário da Reclamada para reduzir o quantum, ao fundamento de que o valor inicialmente arbitrado escapava à proporcionalidade. Eis o teor do acórdão regional:

[[TRANSCRICAO1]]
O valor arbitrado deve observar...

[[CORPO]]
No Recurso de Revista, a Reclamada sustenta que o quantum permanece desproporcional à extensão do dano e à capacidade econômica das partes. Aponta violação aos arts. 5º, V e X, da Constituição; e 944 do Código Civil. Invoca os precedentes desta Corte que recomendam moderação no arbitramento.

[[CORPO]]
Conheço do Recurso de Revista. No mérito, dou parcial provimento para reduzir o valor a R$ 5.000,00.
```

(Note: RR em julgamento → presente: "sustenta", "Aponta", "Invoca". Frase de transição: "Eis o teor do acórdão regional:".)

## CENÁRIO 2 — Em sede de Agravo de Instrumento (RR denegado, AIRR sendo julgado)

```
[[CORPO]]
AGRAVO DE INSTRUMENTO EM RECURSO DE REVISTA DA PARTE RECLAMADA INTERPOSTO NA VIGÊNCIA DA LEI Nº 13.467/2017

[[CORPO]]
TEMA - TERCEIRIZAÇÃO - RESPONSABILIDADE SUBSIDIÁRIA

[[CORPO]]
O Eg. TRT da 4ª Região negou provimento ao Recurso Ordinário da Reclamada, ao fundamento de que a prova produzida demonstrou atividade-fim bancária e descumprimento do dever de fiscalização. Eis os termos do acórdão regional:

[[TRANSCRICAO1]]
A prova dos autos revela que a Reclamante exercia atividades típicas de bancário, em especial atendimento ao público, captação de clientes e oferta de produtos financeiros.
Tais atividades, longe de se reduzirem ao escopo de mera prestação acessória, integravam o núcleo de atividade-fim da tomadora de serviços.
Configurada a terceirização ilícita, impõe-se reconhecer o vínculo direto, na forma da Súmula nº 331, I, do TST.

[[CORPO]]
No Recurso de Revista, a Reclamada sustentou que a prova seria frágil e contraditória, que não houve atividade-fim bancária, que a contratação decorreu de licitação válida e que não seria possível aplicar a Orientação Jurisprudencial nº 383 da SBDI-1 do TST. Apontou violação aos arts. 5º, II e LV, e 37, II e XXI, da Constituição; e 71 da Lei nº 8.666/93. Indicou contrariedade à Súmula nº 331 do TST. Colacionou arestos à divergência.

[[CORPO]]
No Agravo de Instrumento, a Reclamada reitera que a prova seria frágil e contraditória, que não houve atividade-fim bancária, que a contratação decorreu de licitação válida e que não seria possível aplicar a Orientação Jurisprudencial nº 383 da SBDI-1 do TST.

[[CORPO]]
Nego seguimento ao Agravo de Instrumento. A decisão denegatória se ajusta à pacífica jurisprudência desta Corte.
```

(Note: AIRR em julgamento → RR no passado ("sustentou", "Apontou"); AIRR no presente ("reitera"). Relatório do RR COMPLETO (com permissivos); relatório do AIRR SINTETIZADO (sem re-listar permissivos). Frase de transição: "Eis os termos do acórdão regional:".)

## CENÁRIO 3 — Em sede de Agravo Interno (RR e AIRR no passado, fórmula compacta)

```
[[CORPO]]
AGRAVO INTERNO DA PARTE RECLAMADA INTERPOSTO NA VIGÊNCIA DA LEI Nº 13.467/2017

[[CORPO]]
TEMA - HORAS EXTRAS - DIVISOR APLICÁVEL

[[CORPO]]
O Eg. TRT da 4ª Região deu provimento ao Recurso Ordinário do Reclamante para fixar o divisor 180, ao fundamento de que a jornada contratual de 6 horas atrai a aplicação da Súmula nº 124 do TST. Esses, os termos do acórdão regional:

[[TRANSCRICAO1]]
Na hipótese, a jornada contratual...

[[CORPO]]
No Recurso de Revista, a Reclamada sustentou que o divisor aplicável seria 220, porquanto a norma coletiva fixou jornada distinta. Apontou violação aos arts. 7º, XXVI, da Constituição; e 58 da CLT. Indicou contrariedade à Súmula nº 431 do TST. Colacionou arestos à divergência.

[[CORPO]]
No Agravo de Instrumento e no presente Agravo Interno, a Reclamada reitera as alegações.

[[CORPO]]
Nego provimento ao Agravo Interno. A decisão monocrática se mantém pelos próprios fundamentos.
```

(Note: Agravo Interno em julgamento → RR no passado; AIRR + Agravo Interno colapsados em UMA frase com a fórmula compacta unificada. Frase de transição: "Esses, os termos do acórdão regional:". Cada cenário usou uma fórmula de transição diferente — IMITE essa rotação.)

# FUNDAMENTAÇÕES SUGERIDAS POR TEMA

A base do gabinete contém fundamentações já redigidas em casos análogos.
Quando relevantes ao tema corrente, **use-as como ponto de partida** —
adapte ao caso concreto, ajustando partes, datas, valores e nuances
factuais. Se nenhuma das sugestões se aplicar ao tema atual, ignore-as e
redija do zero. NUNCA copie cegamente; sempre confira aderência factual.

{fundamentos_block}

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


def _format_fundamentos_block(
    fundamentos_por_tema: dict[str, list[dict[str, Any]]] | None,
) -> str:
    if not fundamentos_por_tema:
        return "(nenhum modelo aderente na base do gabinete para os temas deste caso.)"
    parts: list[str] = []
    for tema, items in fundamentos_por_tema.items():
        if not items:
            continue
        parts.append(f"## Tema: {tema}")
        for i, it in enumerate(items, start=1):
            titulo = it.get("titulo") or "(sem título)"
            resumo = it.get("resumo") or ""
            corpo = it.get("corpo_md") or ""
            parts.append(f"### Modelo {i} — {titulo}")
            if resumo:
                parts.append(f"_{resumo}_")
            parts.append(corpo)
            parts.append("")
    return "\n".join(parts).strip() or "(nenhum modelo aderente.)"


def build_minuta_draft(
    numero_processo: str,
    pieces: list[dict[str, Any]],
    dossie: dict[str, Any] | None,
    *,
    acordao_regional_data: str | None = None,
    fundamentos_por_tema: dict[str, list[dict[str, Any]]] | None = None,
) -> str:
    provider = get_llm_provider()
    if isinstance(provider, StubProvider) or not dossie or not dossie.get("recursos"):
        return _stub_minuta(numero_processo, pieces)
    import json as _json

    marco_legal = compute_marco_legal(acordao_regional_data) or "(não informado)"
    fundamentos_block = _format_fundamentos_block(fundamentos_por_tema)

    prompt = (
        PROMPT_TEMPLATE.replace("{dossie}", _json.dumps(dossie, ensure_ascii=False, indent=2))
        .replace("{numero}", numero_processo)
        .replace("{marco_legal}", marco_legal)
        .replace("{fundamentos_block}", fundamentos_block)
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
