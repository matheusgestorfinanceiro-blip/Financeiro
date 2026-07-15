"""Análises estatísticas usadas no relatório final: classificação de receitas/despesas
em ordinárias x extraordinárias, e concentração de inadimplência por competência.

Nenhuma função aqui depende de Streamlit ou fpdf, para poder ser testada isoladamente.
"""
import re

import pandas as pd


def classificar_receitas(demonstrativo, categorias_extraordinarias: list[str] | None = None) -> pd.DataFrame:
    """Retorna uma cópia de df_receitas com a coluna `classificacao` adicionada:
    "extraordinaria" para as linhas cuja `categoria` está em
    `categorias_extraordinarias` (marcadas manualmente pelo usuário na tela de
    upload), "ordinaria" para todas as demais."""
    categorias_extraordinarias = categorias_extraordinarias or []
    df = demonstrativo.df_receitas.copy()
    if df.empty:
        df["classificacao"] = []
        return df
    df["classificacao"] = df["categoria"].apply(
        lambda categoria: "extraordinaria" if categoria in categorias_extraordinarias else "ordinaria"
    )
    return df


def classificar_despesas(demonstrativo, subcategorias_extraordinarias: list[str] | None = None) -> pd.DataFrame:
    """Retorna uma cópia de df_despesas com a coluna `classificacao` adicionada:
    "extraordinaria" para as linhas cuja `subcategoria` está em
    `subcategorias_extraordinarias` (marcadas manualmente pelo usuário na tela
    de upload), "ordinaria" para todas as demais."""
    subcategorias_extraordinarias = subcategorias_extraordinarias or []
    df = demonstrativo.df_despesas.copy()
    if df.empty:
        df["classificacao"] = []
        return df
    df["classificacao"] = df["subcategoria"].apply(
        lambda subcategoria: "extraordinaria" if subcategoria in subcategorias_extraordinarias else "ordinaria"
    )
    return df


def _competencia_para_ordenacao(competencia: str) -> tuple[int, int]:
    m = re.match(r"^(\d{2})/(\d{4})$", competencia.strip())
    if not m:
        return (0, 0)
    mes, ano = m.groups()
    return (int(ano), int(mes))


def concentracao_inadimplencia_por_competencia(inadimplencia) -> pd.DataFrame:
    """Agrupa o valor total em aberto por mês de competência das cobranças
    atualmente inadimplentes. Retorna colunas `competencia` e `valor_total`,
    ordenadas cronologicamente quando possível."""
    if inadimplencia is None or inadimplencia.unidades.empty:
        return pd.DataFrame(columns=["competencia", "valor_total"])
    agrupado = (
        inadimplencia.unidades.groupby("competencia", as_index=False)["total"]
        .sum()
        .rename(columns={"total": "valor_total"})
    )
    agrupado = agrupado.sort_values(
        by="competencia", key=lambda col: col.map(_competencia_para_ordenacao)
    ).reset_index(drop=True)
    return agrupado


def mes_pico_inadimplencia(df_concentracao: pd.DataFrame) -> str | None:
    """Identifica a competência com maior valor total em aberto."""
    if df_concentracao.empty:
        return None
    linha_pico = df_concentracao.loc[df_concentracao["valor_total"].idxmax()]
    return str(linha_pico["competencia"])


def valor_por_unidade_inadimplente(inadimplencia) -> pd.DataFrame:
    """Agrupa o valor total em aberto e a quantidade de meses de competência
    em atraso por unidade. Retorna colunas `unidade`, `valor_total` e
    `meses_em_atraso`, ordenadas do maior para o menor valor em aberto."""
    if inadimplencia is None or inadimplencia.unidades.empty:
        return pd.DataFrame(columns=["unidade", "valor_total", "meses_em_atraso"])
    agrupado = inadimplencia.unidades.groupby("unidade", as_index=False).agg(
        valor_total=("total", "sum"), meses_em_atraso=("competencia", "nunique")
    )
    return agrupado.sort_values(by="valor_total", ascending=False).reset_index(drop=True)
