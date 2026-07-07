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
