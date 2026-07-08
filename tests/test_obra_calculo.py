import pandas as pd
import pytest

from src.obra.calculo import (
    fmt_data_br,
    percentual_orcamento,
    periodo_coberto,
    resumo_pagamento,
    total_geral,
    total_por_categoria,
    total_por_fase,
    total_por_mes,
)


@pytest.fixture
def df_gastos():
    return pd.DataFrame(
        [
            {"id": 1, "data": "2026-01-10", "categoria": "Material de construção", "fase": "Estrutura", "valor": 1000.0, "status_pagamento": "Pago"},
            {"id": 2, "data": "2026-01-20", "categoria": "Mão de obra", "fase": "Estrutura", "valor": 2000.0, "status_pagamento": "Pendente"},
            {"id": 3, "data": "2026-02-05", "categoria": "Material de construção", "fase": "Acabamento", "valor": 500.0, "status_pagamento": "Pago"},
        ]
    )


def test_fmt_data_br():
    assert fmt_data_br("2026-07-08") == "08/07/2026"
    assert fmt_data_br("") == ""


def test_total_geral(df_gastos):
    assert total_geral(df_gastos) == 3500.0


def test_total_geral_vazio():
    assert total_geral(pd.DataFrame(columns=["valor"])) == 0.0


def test_total_por_categoria(df_gastos):
    agrupado = total_por_categoria(df_gastos)
    mapa = dict(zip(agrupado["categoria"], agrupado["valor"]))
    assert mapa["Material de construção"] == 1500.0
    assert mapa["Mão de obra"] == 2000.0


def test_total_por_fase(df_gastos):
    agrupado = total_por_fase(df_gastos)
    mapa = dict(zip(agrupado["fase"], agrupado["valor"]))
    assert mapa["Estrutura"] == 3000.0
    assert mapa["Acabamento"] == 500.0


def test_total_por_mes_acumulado(df_gastos):
    agrupado = total_por_mes(df_gastos)
    assert list(agrupado["mes"]) == ["01/2026", "02/2026"]
    assert list(agrupado["valor"]) == [3000.0, 500.0]
    assert list(agrupado["acumulado"]) == [3000.0, 3500.0]


def test_resumo_pagamento(df_gastos):
    resumo = resumo_pagamento(df_gastos)
    assert resumo == {"pago": 1500.0, "pendente": 2000.0}


def test_percentual_orcamento():
    assert percentual_orcamento(5000.0, 10000.0) == 0.5
    assert percentual_orcamento(5000.0, 0.0) is None


def test_periodo_coberto(df_gastos):
    inicio, fim = periodo_coberto(df_gastos)
    assert inicio == "10/01/2026"
    assert fim == "05/02/2026"


def test_periodo_coberto_vazio():
    assert periodo_coberto(pd.DataFrame(columns=["data"])) is None
