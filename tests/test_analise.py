import pandas as pd

from src.calculo.analise import (
    classificar_regularidade,
    concentracao_inadimplencia_por_competencia,
    mes_pico_inadimplencia,
)
from src.models.schema import DadosInadimplencia


def test_classificar_regularidade_valores_uniformes_e_ordinaria():
    valores = [100.0] * 12
    assert classificar_regularidade(valores) == "ordinaria"


def test_classificar_regularidade_concentrada_em_poucos_meses_e_extraordinaria():
    valores = [0.0] * 10 + [5000.0, 5000.0]
    assert classificar_regularidade(valores) == "extraordinaria"


def test_classificar_regularidade_media_zero_e_extraordinaria():
    assert classificar_regularidade([0.0] * 12) == "extraordinaria"


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
