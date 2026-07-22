import pytest

from src.parsers.inadimplentes_parser import parse_inadimplentes


def test_extrai_condominio(caminho_inadimplentes):
    dados = parse_inadimplentes(caminho_inadimplentes)
    assert "CONDOMINIO" in dados.condominio.upper()


def test_extrai_percentual_e_quantidade_do_rodape(caminho_inadimplentes):
    dados = parse_inadimplentes(caminho_inadimplentes)
    assert dados.qtd_unidades_inadimplentes == 7
    assert dados.percentual_inadimplencia == 0.175


def test_extrai_lancamentos_das_unidades(caminho_inadimplentes):
    dados = parse_inadimplentes(caminho_inadimplentes)
    assert not dados.unidades.empty
    assert dados.unidades["unidade"].nunique() == 7
    # A unidade "AP 04" tem dois lançamentos em atraso (dois meses).
    assert len(dados.unidades[dados.unidades["unidade"].str.startswith("AP 04")]) == 2


def test_total_geral_bate_com_soma_dos_lancamentos(caminho_inadimplentes):
    dados = parse_inadimplentes(caminho_inadimplentes)
    soma = dados.unidades["total"].sum()
    assert round(soma, 2) == round(dados.total_geral, 2)


def test_extrai_unidades_com_codigo_numerico_sem_prefixo_ap(caminho_inadimplentes_horizontal):
    # Regressão: um formato real de PDF usa codigo de unidade so numerico
    # ("05 - NOME", sem "AP"), as vezes com uma tag de status apos o nome
    # ("Juridico", "1a Notificacao") - o parser nao pode ficar com a tabela de
    # unidades vazia so porque o codigo nao comeca com "AP".
    dados = parse_inadimplentes(caminho_inadimplentes_horizontal)
    assert "CONDOMINIO" in dados.condominio.upper()
    assert not dados.unidades.empty
    assert dados.unidades["unidade"].nunique() == 6
    # A unidade "16" tem 3 lançamentos em atraso (tres meses) mesmo com a tag "1° Notificação".
    assert len(dados.unidades[dados.unidades["unidade"] == "16"]) == 3
    # A unidade "07" tem a tag "Jurídico" e continua sendo extraída corretamente.
    assert len(dados.unidades[dados.unidades["unidade"] == "07"]) == 3
    # O nome do proprietario nunca deve aparecer - so o codigo da unidade.
    assert not dados.unidades["unidade"].str.contains(" - ").any()


def test_total_geral_bate_com_soma_dos_lancamentos_formato_horizontal(caminho_inadimplentes_horizontal):
    dados = parse_inadimplentes(caminho_inadimplentes_horizontal)
    soma = dados.unidades["total"].sum()
    assert round(soma, 2) == round(dados.total_geral, 2)


def test_percentual_inadimplencia_com_rodape_no_singular(caminho_inadimplentes_singular):
    # Regressão: com só 1 unidade inadimplente, o rodapé real do sistema usa
    # o singular ("1 unidade inadimplente"), não o plural ("unidades
    # inadimplentes") - o percentual não pode ficar em 0% só por isso.
    dados = parse_inadimplentes(caminho_inadimplentes_singular)
    assert dados.qtd_unidades_inadimplentes == 1
    assert dados.percentual_inadimplencia == pytest.approx(0.125)
    assert dados.total_principal == pytest.approx(710.0)
    assert dados.total_geral == pytest.approx(949.10)


def test_extrai_unidades_com_codigo_lote_e_coluna_de_atualizacao(caminho_inadimplentes_lote):
    # Regressão: um formato real usa o codigo de unidade "Lote NN" (nao "AP"/
    # "APTO"/"LOJA"/"SALA" nem so numero), incluindo codigos alfanumericos
    # ("Lote 07A"), e uma coluna extra de "Atualizacao" entre multa e
    # honorarios que o formato mais comum nao tem.
    dados = parse_inadimplentes(caminho_inadimplentes_lote)
    assert dados.qtd_unidades_inadimplentes == 4
    assert dados.percentual_inadimplencia == pytest.approx(0.2667)
    assert not dados.unidades.empty
    assert dados.unidades["unidade"].nunique() == 4
    assert (dados.unidades["unidade"] == "Lote 07A").sum() == 2
    assert not dados.unidades["unidade"].str.contains(" - ").any()
    assert "atualizacao" in dados.unidades.columns
    assert (dados.unidades["atualizacao"] == 0.0).all()
    soma = dados.unidades["total"].sum()
    assert round(soma, 2) == round(dados.total_geral, 2)


def test_extrai_unidades_com_codigo_sigla_hifen_numero(caminho_inadimplentes_sigla):
    # Regressão: um formato real usa o codigo de unidade como sigla-hifen-numero
    # ("C-34", "R-02", "R-13"), diferente de "AP"/"APTO"/"LOJA"/"SALA"/"Lote"/
    # numero puro. Como o proprio codigo tem um hifen interno (sem espacos) e o
    # separador codigo-nome e " - " (com espacos), o parser precisa distinguir
    # os dois - senao a tabela sai vazia (bug relatado: rodape lido, mas nenhuma
    # linha de unidade reconhecida).
    dados = parse_inadimplentes(caminho_inadimplentes_sigla)
    assert dados.qtd_unidades_inadimplentes == 3
    assert dados.percentual_inadimplencia == pytest.approx(0.125)
    assert not dados.unidades.empty
    assert sorted(dados.unidades["unidade"].unique().tolist()) == ["C-34", "R-02", "R-13"]
    # A tag de status ("Juridico") nao deve virar parte do codigo da unidade.
    assert not dados.unidades["unidade"].str.contains("Juridico", case=False).any()
    assert not dados.unidades["unidade"].str.contains(" - ").any()
    soma = dados.unidades["total"].sum()
    assert round(soma, 2) == round(dados.total_geral, 2)
