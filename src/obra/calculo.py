"""Cálculos e agregações sobre os gastos lançados da obra."""
import datetime

import pandas as pd


def fmt_data_br(data_iso: str) -> str:
    """Converte 'AAAA-MM-DD' para 'DD/MM/AAAA'. Retorna vazio se não houver data."""
    if not data_iso:
        return ""
    return datetime.date.fromisoformat(str(data_iso)).strftime("%d/%m/%Y")


def total_geral(df: pd.DataFrame) -> float:
    return float(df["valor"].sum()) if not df.empty else 0.0


def total_por_categoria(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["categoria", "valor"])
    return df.groupby("categoria", as_index=False)["valor"].sum().sort_values("valor", ascending=False)


def total_por_mes(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["mes", "valor", "acumulado"])
    temp = df.copy()
    datas = pd.to_datetime(temp["data"])
    temp["mes"] = datas.dt.strftime("%m/%Y")
    temp["ordenacao"] = datas.dt.to_period("M")
    agrupado = temp.groupby(["ordenacao", "mes"], as_index=False)["valor"].sum().sort_values("ordenacao")
    agrupado["acumulado"] = agrupado["valor"].cumsum()
    return agrupado[["mes", "valor", "acumulado"]].reset_index(drop=True)


def resumo_pagamento(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"pago": 0.0, "pendente": 0.0}
    return {
        "pago": float(df.loc[df["pago"], "valor"].sum()),
        "pendente": float(df.loc[~df["pago"], "valor"].sum()),
    }


def percentual_orcamento(total_gasto: float, orcamento_previsto: float) -> float | None:
    if not orcamento_previsto:
        return None
    return total_gasto / orcamento_previsto


def resumo_proprietario_inquilino(total_gasto: float, orcamento_previsto: float) -> dict:
    """O proprietário cobre até o orçamento previsto; o que passar disso é
    considerado gasto do inquilino."""
    proprietario = min(total_gasto, orcamento_previsto) if orcamento_previsto else total_gasto
    inquilino = max(0.0, total_gasto - orcamento_previsto) if orcamento_previsto else 0.0
    return {"proprietario": proprietario, "inquilino": inquilino}


def periodo_coberto(df: pd.DataFrame) -> tuple[str, str] | None:
    if df.empty:
        return None
    datas = pd.to_datetime(df["data"])
    return datas.min().strftime("%d/%m/%Y"), datas.max().strftime("%d/%m/%Y")
