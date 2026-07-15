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
    assert len(dados.unidades[dados.unidades["unidade"].str.startswith("16 -")]) == 3
    # A unidade "07" tem a tag "Jurídico" e continua sendo extraída corretamente.
    assert len(dados.unidades[dados.unidades["unidade"].str.startswith("07 -")]) == 3


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
