from src.parsers.demonstrativo_parser import parse_demonstrativo


def test_extrai_condominio_e_meses(caminho_demonstrativo):
    dados = parse_demonstrativo(caminho_demonstrativo)
    assert "CONDOMINIO" in dados.condominio.upper()
    assert len(dados.meses) == 12


def test_soma_das_linhas_de_receita_bate_com_total_do_periodo(caminho_demonstrativo):
    dados = parse_demonstrativo(caminho_demonstrativo)
    soma = dados.df_receitas["total"].sum()
    assert round(soma, 2) == round(dados.total_receitas, 2)


def test_soma_das_linhas_de_despesa_bate_com_total_do_periodo(caminho_demonstrativo):
    dados = parse_demonstrativo(caminho_demonstrativo)
    soma = dados.df_despesas["total"].sum()
    assert round(soma, 2) == round(dados.total_despesas, 2)


def test_categorias_pai_conhecidas_estao_presentes(caminho_demonstrativo):
    dados = parse_demonstrativo(caminho_demonstrativo)
    categorias = set(dados.df_despesas["categoria_pai"].unique())
    assert {"Com Pessoal", "Mensais", "Manutenção", "Diversas"}.issubset(categorias)


def test_saldo_anterior_e_final_sao_extraidos(caminho_demonstrativo):
    dados = parse_demonstrativo(caminho_demonstrativo)
    assert dados.saldo_anterior is not None
    assert dados.saldo_final is not None
