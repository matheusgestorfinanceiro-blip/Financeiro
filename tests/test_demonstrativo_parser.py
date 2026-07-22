from src.parsers.demonstrativo_parser import (
    _detectar_cabecalhos_repetidos,
    _e_transferencia_entre_contas,
    _extrair_condominio,
    parse_demonstrativo,
)


def test_extrai_condominio_e_meses(caminho_demonstrativo):
    dados = parse_demonstrativo(caminho_demonstrativo)
    assert "CONDOMINIO" in dados.condominio.upper()
    assert len(dados.meses) == 12


def test_extrai_condominio_mesmo_sem_a_palavra_condominio():
    linhas = ["W020A RESIDENCIAL JARDIM DAS FLORES (10)", "Demonstrativo de Receitas e Despesas"]
    assert _extrair_condominio(linhas) == "W020A RESIDENCIAL JARDIM DAS FLORES (10)"


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


def test_e_transferencia_entre_contas_identifica_linhas_de_transferencia():
    assert _e_transferencia_entre_contas(
        "(+) Transf. da conta 'Digital PJBank' para a conta 'INVEST PJBANK'"
    )
    assert _e_transferencia_entre_contas(
        "(+) Transf. da conta 'INVEST PJBANK' para a conta 'Digital PJBank' Pix Recebido"
    )


def test_e_transferencia_entre_contas_nao_marca_categoria_normal():
    assert not _e_transferencia_entre_contas("Rateio Mensal - Taxa de Condomínio")
    assert not _e_transferencia_entre_contas("Sistema de Segurança")
    assert not _e_transferencia_entre_contas("Conservação e Limpeza em Geral")


def test_detectar_cabecalhos_repetidos_encontra_bloco_comum():
    # Regressao: o endereco do imovel repete no topo de cada pagina, em
    # formatos variados (rua, avenida, praca, com CEP etc.) que uma lista
    # fixa de palavras nunca cobre por completo - a deteccao por repeticao
    # entre paginas funciona para qualquer formato de endereco.
    paginas = [
        ["W099X SOCIEDADE TESTE (99)", "PRACA SAO JOAO, 151, 151 , TRANCOSO CEP. 45818000", "Receitas"],
        ["W099X SOCIEDADE TESTE (99)", "PRACA SAO JOAO, 151, 151 , TRANCOSO CEP. 45818000", "Despesas"],
        ["W099X SOCIEDADE TESTE (99)", "PRACA SAO JOAO, 151, 151 , TRANCOSO CEP. 45818000", "Total de Receitas"],
    ]
    assert set(_detectar_cabecalhos_repetidos(paginas)) == {
        "W099X SOCIEDADE TESTE (99)",
        "PRACA SAO JOAO, 151, 151 , TRANCOSO CEP. 45818000",
    }


def test_detectar_cabecalhos_repetidos_pega_endereco_mesmo_com_topo_diferente():
    # O endereco se repete no topo, mas numa pagina ele veio colado no meio de
    # uma linha de dados (quebra de pagina) - a abordagem de prefixo identico
    # falhava aqui; a de frequencia no topo continua reconhecendo o endereco.
    paginas = [
        ["W099X SOCIEDADE TESTE (99)", "PRACA SAO JOAO, 151 CEP. 45818000", "Receitas"],
        ["W099X SOCIEDADE TESTE (99)", "PRACA SAO JOAO, 151 CEP. 45818000", "Despesas"],
    ]
    repetidos = _detectar_cabecalhos_repetidos(paginas)
    assert "PRACA SAO JOAO, 151 CEP. 45818000" in repetidos
    assert "W099X SOCIEDADE TESTE (99)" in repetidos


def test_detectar_cabecalhos_repetidos_ignora_linhas_com_valores():
    # Uma linha de subtotal repetida (com valores) nao deve ser tratada como
    # cabecalho - so linhas sem valores monetarios.
    paginas = [
        ["Cabecalho comum", "Total geral 1.000,00 1.000,00"],
        ["Cabecalho comum", "Total geral 1.000,00 1.000,00"],
    ]
    assert _detectar_cabecalhos_repetidos(paginas) == ["Cabecalho comum"]


def test_detectar_cabecalhos_repetidos_vazio_com_menos_de_2_paginas():
    assert _detectar_cabecalhos_repetidos([["Unica pagina"]]) == []
    assert _detectar_cabecalhos_repetidos([]) == []


def test_endereco_colado_no_meio_de_categoria_e_removido():
    # Regressao real: quando a quebra de pagina cai no meio de uma linha de
    # categoria, o endereco (repetido no topo de cada pagina) podia colar no
    # texto sem espaco, corrompendo o nome da categoria/subcategoria - tanto
    # no grafico quanto no "livro-razao" da pagina de Balanco.
    meses = [f"Mes{i}" for i in range(1, 13)]
    cabecalho1 = "W099X SOCIEDADE TESTE (99)"
    cabecalho2 = "PRACA SAO JOAO, 151, 151 , TRANCOSO CEP. 45818000"

    def pagina(linhas):
        return "\n".join([cabecalho1, cabecalho2, *linhas])

    class _PaginaFalsa:
        def __init__(self, texto):
            self._texto = texto

        def extract_text(self):
            return self._texto

    class _PdfFalso:
        def __init__(self, paginas):
            self.pages = paginas

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    valores = " ".join(f"{100.0:.2f}".replace(".", ",") for _ in meses)
    linha_receita = f"Rateio Mensal - Taxa de Condomínio {valores} 1.200,00"
    # A subcategoria corrompida: o rotulo colado direto ao cabecalho repetido
    # (sem espaco), simulando exatamente o bug relatado.
    linha_despesa = f"{cabecalho1}{cabecalho2}Servicos Tercerizados {valores} 1.200,00"

    paginas = [
        _PaginaFalsa(pagina(["Receitas", linha_receita, "Despesas", "Com Pessoal"])),
        _PaginaFalsa(pagina([linha_despesa, "Total de Despesas 1.200,00", "Total de Receitas 1.200,00"])),
    ]

    import src.parsers.demonstrativo_parser as demonstrativo_parser

    original_open = demonstrativo_parser.pdfplumber.open
    demonstrativo_parser.pdfplumber.open = lambda _: _PdfFalso(paginas)
    try:
        dados = parse_demonstrativo("caminho-fake.pdf")
    finally:
        demonstrativo_parser.pdfplumber.open = original_open

    subcategorias = dados.df_despesas["subcategoria"].tolist()
    assert any(s.strip() == "Servicos Tercerizados" for s in subcategorias)
    assert not any("PRACA" in s or "CEP" in s for s in subcategorias)


class _PaginaFalsa:
    def __init__(self, linhas):
        self._texto = "\n".join(linhas)

    def extract_text(self):
        return self._texto


class _PdfFalso:
    def __init__(self, paginas):
        self.pages = paginas

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _parse_paginas_sinteticas(paginas_linhas):
    import src.parsers.demonstrativo_parser as demonstrativo_parser

    paginas = [_PaginaFalsa(linhas) for linhas in paginas_linhas]
    original_open = demonstrativo_parser.pdfplumber.open
    demonstrativo_parser.pdfplumber.open = lambda _: _PdfFalso(paginas)
    try:
        return parse_demonstrativo("caminho-fake.pdf")
    finally:
        demonstrativo_parser.pdfplumber.open = original_open


def test_endereco_no_rodape_nao_vira_categoria_de_despesa():
    # Regressao real (condominio "SAM"): neste sistema o endereco do imovel
    # fica no RODAPE de cada pagina (nao no topo). Quando a quebra de pagina
    # cai no meio da lista de despesas, o rodape entra no fluxo e o endereco
    # (uma linha sem valores) era interpretado como o nome de uma categoria de
    # despesa - aparecendo como categoria no grafico, no balanco e na lista de
    # maiores despesas extraordinarias. O nome do condominio (topo) deve ser
    # preservado; a categoria real ("Diversas") nao pode ser substituida pelo
    # endereco.
    meses = [f"Mes{i}" for i in range(1, 13)]
    valores = " ".join(f"{100.0:.2f}".replace(".", ",") for _ in meses)
    cond_topo = "W003A SOCIEDADE EXEMPLO DO VALE (303)"
    endereco = "PRACA SAO JOAO, 151, 151 , TRANCOSO CEP. 45818000"
    rodape = ["SOCIEDADE EXEMPLO DO VALE", endereco, "PORTO SEGURO / BA - Tel: (73)3268-2508", "1 de 2"]

    pagina1 = [
        cond_topo, "Receitas", f"Rateio Mensal - Taxa de Condominio {valores} 1.200,00",
        "Despesas", "Com Pessoal", f"Salario {valores} 1.200,00",
        "Diversas", f"Honorarios de Assessoria {valores} 1.200,00", *rodape,
    ]
    pagina2 = [
        cond_topo, f"Despesas Diversas {valores} 1.200,00", f"Honorarios Advocaticios {valores} 1.200,00",
        "Total de Despesas 4.800,00", "Total de Receitas 1.200,00", *rodape,
    ]

    dados = _parse_paginas_sinteticas([pagina1, pagina2])

    assert dados.condominio == cond_topo
    categorias = set(dados.df_despesas["categoria_pai"])
    assert not any("PRACA" in c or "CEP" in c for c in categorias)
    assert "Diversas" in categorias
    # As subcategorias da secao Diversas (que caiu na quebra de pagina) devem
    # ficar sob "Diversas", nao sob o endereco.
    diversas = dados.df_despesas[dados.df_despesas["categoria_pai"] == "Diversas"]["subcategoria"].tolist()
    assert "Honorarios Advocaticios" in diversas
