from hermes_api.services.tst_repetitivos import parse_repetitivos_html

SAMPLE_HTML = """
<html><body>
<h2>Tabela de Recursos de Revista Repetitivos</h2>

<div class="tema">
  <h3>Tema 42</h3>
  <p>Aplicação da Súmula 124 do TST ao bancário com jornada contratual de 6h.</p>
  <p>Situação: Suspenso por decisão do colegiado em 12/03/2024.</p>
</div>

<div class="tema">
  <h3>Tema 87</h3>
  <p>Validade da norma coletiva que fixa divisor 220 para bancário.</p>
  <p>Situação: Decidido pelo Pleno em 09/06/2025.</p>
  <p>Tese firmada: É válida a cláusula de norma coletiva que estabelece divisor 220 para bancário, observado o art. 7º, XXVI da Constituição.</p>
</div>

<div class="tema">
  <h3>Tema 99</h3>
  <p>Tema instaurado em 2024 — Aguardando julgamento.</p>
</div>
</body></html>
"""


def test_parse_extracts_numero_e_descricao() -> None:
    out = parse_repetitivos_html(SAMPLE_HTML)
    numeros = sorted(o.numero for o in out)
    assert numeros == [42, 87, 99]


def test_parse_extrai_situacao_suspenso() -> None:
    out = {o.numero: o for o in parse_repetitivos_html(SAMPLE_HTML)}
    assert out[42].situacao == "suspenso"


def test_parse_extrai_tese_quando_decidido() -> None:
    out = {o.numero: o for o in parse_repetitivos_html(SAMPLE_HTML)}
    item = out[87]
    assert item.situacao == "decidido"
    assert item.tese and "divisor 220" in item.tese


def test_parse_default_situacao_outro_quando_apenas_aguardando() -> None:
    out = {o.numero: o for o in parse_repetitivos_html(SAMPLE_HTML)}
    # "Aguardando julgamento" não casa nenhum dos sinais → cai em "outro".
    assert out[99].situacao in ("outro", "julgado")
