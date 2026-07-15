import pandas as pd

from src.calculo.analise import (
    classificar_despesas,
    classificar_receitas,
    concentracao_inadimplencia_por_competencia,
    mes_pico_inadimplencia,
    valor_por_unidade_inadimplente,
)
from src.models.schema import DadosDemonstrativo, DadosInadimplencia


def _demonstrativo_para_classificacao() -> DadosDemonstrativo:
    meses = ["Jan/2026", "Fev/2026"]
    df_receitas = pd.DataFrame(
        [
            {"categoria": "Rateio Mensal", "Jan/2026": 100.0, "Fev/2026": 100.0, "total": 200.0},
            {"categoria": "Juros", "Jan/2026": 5.0, "Fev/2026": 0.0, "total": 5.0},
        ]
    )
    df_despesas = pd.DataFrame(
        [
            {"categoria_pai": "Mensais", "subcategoria": "Água", "Jan/2026": 50.0, "Fev/2026": 50.0, "total": 100.0},
            {"categoria_pai": "Diversas", "subcategoria": "Obra Emergencial", "Jan/2026": 500.0, "Fev/2026": 0.0, "total": 500.0},
        ]
    )
    return DadosDemonstrativo(
        condominio="Condomínio Teste", meses=meses, df_receitas=df_receitas, df_despesas=df_despesas,
        total_receitas=205.0, total_despesas=600.0,
    )


def test_classificar_receitas_marca_so_as_categorias_indicadas_como_extraordinarias():
    demonstrativo = _demonstrativo_para_classificacao()
    df = classificar_receitas(demonstrativo, ["Juros"])
    classificacoes = dict(zip(df["categoria"], df["classificacao"]))
    assert classificacoes["Rateio Mensal"] == "ordinaria"
    assert classificacoes["Juros"] == "extraordinaria"


def test_classificar_receitas_sem_marcacoes_tudo_ordinaria():
    demonstrativo = _demonstrativo_para_classificacao()
    df = classificar_receitas(demonstrativo, [])
    assert (df["classificacao"] == "ordinaria").all()


def test_classificar_despesas_marca_so_as_subcategorias_indicadas_como_extraordinarias():
    demonstrativo = _demonstrativo_para_classificacao()
    df = classificar_despesas(demonstrativo, ["Obra Emergencial"])
    classificacoes = dict(zip(df["subcategoria"], df["classificacao"]))
    assert classificacoes["Água"] == "ordinaria"
    assert classificacoes["Obra Emergencial"] == "extraordinaria"


def _inadimplencia_com_competencias(competencias_e_totais: list[tuple[str, float]]) -> DadosInadimplencia:
    df = pd.DataFrame(
        [{"unidade": f"AP {i}", "competencia": comp, "total": total} for i, (comp, total) in enumerate(competencias_e_totais)]
    )
    return DadosInadimplencia(
        condominio="Condomínio Teste",
        unidades=df,
        qtd_unidades_inadimplentes=len(competencias_e_totais),
        percentual_inadimplencia=0.1,
        total_principal=0.0,
        total_geral=sum(t for _, t in competencias_e_totais),
    )


def test_concentracao_inadimplencia_agrupa_por_competencia_em_ordem_cronologica():
    inadimplencia = _inadimplencia_com_competencias(
        [("03/2026", 100.0), ("01/2026", 200.0), ("03/2026", 50.0), ("02/2026", 10.0)]
    )
    resultado = concentracao_inadimplencia_por_competencia(inadimplencia)
    assert resultado["competencia"].tolist() == ["01/2026", "02/2026", "03/2026"]
    assert resultado["valor_total"].tolist() == [200.0, 10.0, 150.0]


def test_concentracao_inadimplencia_vazia_quando_nao_ha_dados():
    inadimplencia = _inadimplencia_com_competencias([])
    resultado = concentracao_inadimplencia_por_competencia(inadimplencia)
    assert resultado.empty


def test_mes_pico_inadimplencia_identifica_maior_valor():
    inadimplencia = _inadimplencia_com_competencias(
        [("01/2026", 100.0), ("02/2026", 900.0), ("03/2026", 50.0)]
    )
    concentracao = concentracao_inadimplencia_por_competencia(inadimplencia)
    assert mes_pico_inadimplencia(concentracao) == "02/2026"


def test_mes_pico_inadimplencia_none_quando_vazio():
    assert mes_pico_inadimplencia(pd.DataFrame(columns=["competencia", "valor_total"])) is None


def _inadimplencia_com_unidades(lancamentos: list[tuple[str, str, float]]) -> DadosInadimplencia:
    df = pd.DataFrame(
        [{"unidade": unidade, "competencia": comp, "total": total} for unidade, comp, total in lancamentos]
    )
    return DadosInadimplencia(
        condominio="Condomínio Teste",
        unidades=df,
        qtd_unidades_inadimplentes=df["unidade"].nunique() if not df.empty else 0,
        percentual_inadimplencia=0.1,
        total_principal=0.0,
        total_geral=sum(t for _, _, t in lancamentos),
    )


def test_valor_por_unidade_inadimplente_agrupa_valor_e_conta_meses():
    inadimplencia = _inadimplencia_com_unidades(
        [
            ("AP 01", "01/2026", 100.0),
            ("AP 01", "02/2026", 100.0),
            ("AP 02", "01/2026", 500.0),
        ]
    )
    resultado = valor_por_unidade_inadimplente(inadimplencia)
    linha_ap01 = resultado[resultado["unidade"] == "AP 01"].iloc[0]
    linha_ap02 = resultado[resultado["unidade"] == "AP 02"].iloc[0]
    assert linha_ap01["valor_total"] == 200.0
    assert linha_ap01["meses_em_atraso"] == 2
    assert linha_ap02["valor_total"] == 500.0
    assert linha_ap02["meses_em_atraso"] == 1
    # Ordenado do maior para o menor valor em aberto.
    assert resultado["unidade"].tolist() == ["AP 02", "AP 01"]


def test_valor_por_unidade_inadimplente_vazio_sem_dados():
    assert valor_por_unidade_inadimplente(None).empty
    assert valor_por_unidade_inadimplente(_inadimplencia_com_unidades([])).empty
