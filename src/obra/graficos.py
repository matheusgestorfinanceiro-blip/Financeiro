"""Gera as figuras (matplotlib) dos gastos da obra, reaproveitadas na tela e no PDF final."""
import matplotlib
import matplotlib.pyplot as plt

from src.obra.calculo import total_por_categoria, total_por_fase, total_por_mes

matplotlib.use("Agg")

NAVY = "#0A1628"
NAVY2 = "#102447"
CYAN = "#00B4D8"
CYAN2 = "#38BDF8"
GRAY = "#94A3B8"

CORES_CATEGORICAS = [CYAN, NAVY2, CYAN2, GRAY, "#0A5C73", "#7DB9CC", "#1E3A5F", "#F25C54", "#E8A628"]


def _aplicar_estilo_figura(fig, ax):
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.title.set_color(NAVY)
    ax.xaxis.label.set_color(NAVY)
    ax.yaxis.label.set_color(NAVY)
    ax.tick_params(colors=NAVY)
    for spine in ax.spines.values():
        spine.set_color(GRAY)


def _grafico_vazio(titulo: str):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.text(0.5, 0.5, "Sem lançamentos", ha="center", va="center", color=GRAY)
    ax.set_title(titulo)
    ax.axis("off")
    _aplicar_estilo_figura(fig, ax)
    fig.tight_layout()
    return fig


def grafico_gastos_por_categoria(df):
    agrupado = total_por_categoria(df)
    if agrupado.empty:
        return _grafico_vazio("Gastos por categoria")

    agrupado = agrupado.sort_values("valor")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    cores = [CORES_CATEGORICAS[i % len(CORES_CATEGORICAS)] for i in range(len(agrupado))]
    ax.barh(agrupado["categoria"], agrupado["valor"], color=cores)
    ax.set_xlabel("R$")
    ax.set_title("Gastos por categoria")
    _aplicar_estilo_figura(fig, ax)
    fig.tight_layout()
    return fig


def grafico_gastos_por_fase(df):
    agrupado = total_por_fase(df)
    if agrupado.empty:
        return _grafico_vazio("Gastos por fase da obra")

    agrupado = agrupado.sort_values("valor")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    cores = [CORES_CATEGORICAS[i % len(CORES_CATEGORICAS)] for i in range(len(agrupado))]
    ax.barh(agrupado["fase"], agrupado["valor"], color=cores)
    ax.set_xlabel("R$")
    ax.set_title("Gastos por fase da obra")
    _aplicar_estilo_figura(fig, ax)
    fig.tight_layout()
    return fig


def grafico_evolucao_gastos(df):
    agrupado = total_por_mes(df)
    if agrupado.empty:
        return _grafico_vazio("Evolução dos gastos ao longo da obra")

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(agrupado["mes"], agrupado["valor"], color=NAVY2, label="Gasto no mês")
    ax.plot(agrupado["mes"], agrupado["acumulado"], marker="o", color=CYAN, label="Acumulado")
    ax.set_ylabel("R$")
    ax.set_title("Evolução dos gastos ao longo da obra")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    _aplicar_estilo_figura(fig, ax)
    fig.tight_layout()
    return fig
