from hermes_api.anonymizer import anonymize, deanonymize


def test_anonymiza_cpf_cnpj_oab_email_phone() -> None:
    text = (
        "Reclamante CPF 123.456.789-09, advogado OAB/SP 123456, "
        "empresa CNPJ 12.345.678/0001-99, contato joao@empresa.com.br, "
        "telefone (11) 98765-4321."
    )
    result = anonymize(text)
    assert "123.456.789-09" not in result.text
    assert "12.345.678/0001-99" not in result.text
    assert "OAB/SP 123456" not in result.text
    assert "joao@empresa.com.br" not in result.text
    assert "98765-4321" not in result.text
    # placeholders presentes
    assert "<CPF_1>" in result.text
    assert "<CNPJ_1>" in result.text


def test_deanonymize_reverte() -> None:
    text = "CPF 123.456.789-09 e e-mail x@y.com"
    result = anonymize(text)
    assert deanonymize(result.text, result.mapping) == text


def test_multiplos_cpfs_recebem_indices() -> None:
    text = "111.222.333-44 e 555.666.777-88"
    result = anonymize(text)
    assert "<CPF_1>" in result.text
    assert "<CPF_2>" in result.text
    assert len(result.mapping) == 2


def test_texto_sem_pii_passa_intacto() -> None:
    text = "Lorem ipsum dolor sit amet."
    result = anonymize(text)
    assert result.text == text
    assert result.mapping == {}
