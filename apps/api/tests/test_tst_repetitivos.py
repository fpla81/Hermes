from hermes_api.services.tst_repetitivos import parse_repetitivos_html

# Imita a estrutura real do /recursos-repetitivos/tabela-completa
SAMPLE_HTML = """
<table>
<tr><th>Tema</th><th>Representativos</th><th>Tese</th><th>Último Movimento</th><th>Há Decisão de Suspensão?</th><th>Relator</th></tr>
<tr>
  <td>1</td>
  <td><a href="https://www.tst.jus.br/processo/IRR-243000-58.2013.5.13.0023">IRR-243000-58.2013.5.13.0023</a></td>
  <td>Não é legítima e caracteriza lesão moral a exigência de Certidão de Antecedentes Criminais...</td>
  <td>Transitado em Julgado (Publicado em 22/9/2017)</td>
  <td>Não</td>
  <td>Min. Augusto César Leite de Carvalho</td>
</tr>
<tr>
  <td>42</td>
  <td>IRR-849-83.2013.5.03.0138</td>
  <td>O divisor aplicável para cálculo das horas extras do bancário, inclusive para os submetidos à jornada de oito horas, é 180 e 220 para as jornadas normais de seis e oito horas.</td>
  <td>Acórdão publicado em 19/12/2016</td>
  <td>Não</td>
  <td>Min. X</td>
</tr>
<tr>
  <td>99</td>
  <td>IRR-1000-00.2024.5.10.0001</td>
  <td>Tema sob análise pelo Pleno — aguardando julgamento.</td>
  <td>Aguardando inclusão em pauta</td>
  <td>Sim</td>
  <td>Min. Y</td>
</tr>
<tr><td colspan="6">linha de continuação que não tem número — deve ser ignorada</td></tr>
</table>
"""


def test_parse_extracts_numero_e_descricao() -> None:
    out = parse_repetitivos_html(SAMPLE_HTML)
    numeros = sorted(o.numero for o in out)
    assert numeros == [1, 42, 99]


def test_parse_classifica_suspenso_pela_coluna_suspensao() -> None:
    out = {o.numero: o for o in parse_repetitivos_html(SAMPLE_HTML)}
    assert out[99].situacao == "suspenso"


def test_parse_classifica_decidido_quando_transitado_em_julgado() -> None:
    out = {o.numero: o for o in parse_repetitivos_html(SAMPLE_HTML)}
    item = out[1]
    assert item.situacao == "decidido"
    assert item.tese and "Antecedentes Criminais" in item.tese


def test_parse_decidido_com_acordao_publicado() -> None:
    out = {o.numero: o for o in parse_repetitivos_html(SAMPLE_HTML)}
    assert out[42].situacao == "decidido"
    assert out[42].tese and "divisor" in out[42].tese.lower()


def test_parse_extrai_link_do_representativo() -> None:
    out = {o.numero: o for o in parse_repetitivos_html(SAMPLE_HTML)}
    assert out[1].link == "https://www.tst.jus.br/processo/IRR-243000-58.2013.5.13.0023"


def test_parse_ignora_linhas_sem_numero() -> None:
    """Linha de continuação com colspan e sem dígito não deve gerar tema."""
    out = parse_repetitivos_html(SAMPLE_HTML)
    # 3 temas (1, 42, 99) — a linha de continuação some
    assert len(out) == 3
