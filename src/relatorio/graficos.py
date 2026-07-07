"""Gera as figuras (matplotlib) reaproveitadas na tela e no PDF final."""
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.use("Agg")

NAVY = "#0A1628"
NAVY2 = "#102447"
CYAN = "#00B4D8"
CYAN2 = "#38BDF8"
GRAY = "#94A3B8"
TOMATO = "#F25C54"

CORES_CATEGORICAS = [CYAN, NAVY2, CYAN2, GRAY]


def _aplicar_estilo_figura(fig, ax):
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.title.set_color(NAVY)
    ax.xaxis.label.set_color(NAVY)
    ax.yaxis.label.set_color(NAVY)
    ax.tick_params(colors=NAVY)
    for spine in ax.spines.values():
        spine.set_color(GRAY)


def grafico_despesas_por_categoria(resultado):
    df = pd.DataFrame(
        [
            {
                "categoria": l.categoria_pai,
                "historico": l.valor_historico,
                "previsto": l.valor_previsto,
            }
            for l in resultado.despesas_previstas
        ]
    )
    agrupado = df.groupby("categoria", as_index=False).sum()
    agrupado = agrupado.sort_values("previsto", ascending=True)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    y = range(len(agrupado))
    altura = 0.35
    ax.barh([i + altura / 2 for i in y], agrupado["historico"], height=altura, label="Histórico (12 meses)", color=NAVY2)
    ax.barh([i - altura / 2 for i in y], agrupado["previsto"], height=altura, label="Previsto", color=CYAN)
    ax.set_yticks(list(y))
    ax.set_yticklabels(agrupado["categoria"])
    ax.set_xlabel("R$")
    ax.set_title("Despesas: histórico x previsto, por categoria")
    ax.legend()
    _aplicar_estilo_figura(fig, ax)
    fig.tight_layout()
    return fig


def grafico_evolucao_mensal(resultado):
    meses = list(resultado.total_despesas_historico_por_mes.keys())
    despesas = list(resultado.total_despesas_historico_por_mes.values())
    receitas = list(resultado.total_receitas_historico_por_mes.values())

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(meses, receitas, marker="o", label="Receitas", color=CYAN)
    ax.plot(meses, despesas, marker="o", label="Despesas", color=NAVY2)
    ax.set_ylabel("R$")
    ax.set_title("Evolução mensal (últimos 12 meses)")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    _aplicar_estilo_figura(fig, ax)
    fig.tight_layout()
    return fig


def grafico_composicao_taxa_condominial(resultado):
    despesa_pura = resultado.total_despesas_previsto - resultado.total_outras_receitas_previsto
    fatias = {
        "Despesas (líq. outras receitas)": max(despesa_pura, 0),
        "Fundo de reserva": resultado.fundo_reserva_valor,
    }
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(fatias.values(), labels=fatias.keys(), autopct="%1.1f%%", colors=[NAVY2, CYAN])
    ax.set_title("Composição da taxa condominial prevista")
    ax.title.set_color(NAVY)
    fig.tight_layout()
    return fig


def grafico_indicador_inadimplencia(resultado):
    fig, ax = plt.subplots(figsize=(5, 3))
    pct = resultado.percentual_inadimplencia * 100
    ax.barh([""], [pct], color=TOMATO)
    ax.set_xlim(0, max(30, pct + 5))
    ax.set_xlabel("% de unidades inadimplentes")
    ax.set_title(f"Inadimplência considerada: {pct:.2f}%")
    _aplicar_estilo_figura(fig, ax)
    fig.tight_layout()
    return fig


def _total_por_classificacao(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {"ordinaria": 0.0, "extraordinaria": 0.0}
    agrupado = df.groupby("classificacao")["total"].sum()
    return {
        "ordinaria": float(agrupado.get("ordinaria", 0.0)),
        "extraordinaria": float(agrupado.get("extraordinaria", 0.0)),
    }


def grafico_receitas_ordinaria_x_extraordinaria(resultado):
    totais = _total_por_classificacao(resultado.receitas_classificadas)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(
        [totais["ordinaria"], totais["extraordinaria"]],
        labels=["Ordinária (recorrente)", "Extraordinária/eventual"],
        autopct="%1.1f%%",
        colors=[CYAN, GRAY],
    )
    ax.set_title("Receitas: ordinárias x extraordinárias")
    ax.title.set_color(NAVY)
    fig.tight_layout()
    return fig


def grafico_despesas_ordinaria_x_extraordinaria(resultado):
    totais = _total_por_classificacao(resultado.despesas_classificadas)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(
        [totais["ordinaria"], totais["extraordinaria"]],
        labels=["Ordinária (recorrente)", "Extraordinária/eventual"],
        autopct="%1.1f%%",
        colors=[NAVY2, GRAY],
    )
    ax.set_title("Despesas: ordinárias x extraordinárias")
    ax.title.set_color(NAVY)
    fig.tight_layout()
    return fig


def grafico_evolucao_inadimplencia(resultado):
    df = resultado.concentracao_inadimplencia
    fig, ax = plt.subplots(figsize=(8, 4))
    if df is None or df.empty:
        ax.text(0.5, 0.5, "Sem cobranças em aberto no período", ha="center", va="center", color=GRAY)
        ax.set_xticks([])
        ax.set_yticks([])
    else:
        cores = [TOMATO if comp == resultado.mes_pico_inadimplencia else NAVY2 for comp in df["competencia"]]
        ax.bar(df["competencia"], df["valor_total"], color=cores)
        ax.set_ylabel("R$ em aberto")
        ax.set_title("Concentração de inadimplência por mês de competência")
        ax.tick_params(axis="x", rotation=45)
    _aplicar_estilo_figura(fig, ax)
    fig.tight_layout()
    return fig
