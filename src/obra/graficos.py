"""Gera as figuras (matplotlib) dos gastos da obra, reaproveitadas na tela e no PDF final."""
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from src.obra.calculo import total_por_categoria, total_por_mes

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


def _fmt_eixo_moeda(valor, _pos=None):
    if valor >= 1000:
        return f"R$ {valor / 1000:,.1f} mil".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {valor:,.0f}".replace(",", ".")


def grafico_evolucao_gastos(df):
    agrupado = total_por_mes(df)
    if agrupado.empty:
        return _grafico_vazio("Evolução dos gastos ao longo da obra")

    fig, ax1 = plt.subplots(figsize=(9, 4.8))
    ax2 = ax1.twinx()

    posicoes = range(len(agrupado))
    barras = ax1.bar(posicoes, agrupado["valor"], color=NAVY2, label="Gasto no mês", width=0.55, zorder=2)
    linha = ax2.plot(
        posicoes, agrupado["acumulado"], marker="o", markersize=6, color=CYAN, linewidth=2.5, label="Acumulado", zorder=3
    )

    for pos, valor in zip(posicoes, agrupado["valor"]):
        ax1.annotate(
            _fmt_eixo_moeda(valor),
            (pos, valor),
            textcoords="offset points",
            xytext=(0, 4),
            ha="center",
            fontsize=7.5,
            color=NAVY2,
        )

    # A linha acumulada so recebe rotulo no primeiro e no ultimo ponto: com
    # muitos meses, rotular cada ponto da linha colide com os proprios
    # rotulos das barras e entre si, poluindo o grafico.
    ultimo_indice = len(agrupado) - 1
    indices_rotulados = {0, ultimo_indice} if ultimo_indice > 0 else {0}
    for pos, valor in zip(posicoes, agrupado["acumulado"]):
        if pos not in indices_rotulados:
            continue
        ax2.annotate(
            _fmt_eixo_moeda(valor),
            (pos, valor),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=8.5,
            color="#0A5C73",
            fontweight="bold",
        )

    ax1.set_xticks(list(posicoes))
    ax1.set_xticklabels(agrupado["mes"], rotation=0)
    ax1.set_ylabel("Gasto no mês", color=NAVY2)
    ax2.set_ylabel("Total acumulado", color="#0A5C73")
    ax1.yaxis.set_major_formatter(FuncFormatter(_fmt_eixo_moeda))
    ax2.yaxis.set_major_formatter(FuncFormatter(_fmt_eixo_moeda))
    ax1.set_ylim(0, agrupado["valor"].max() * 1.35)
    ax2.set_ylim(0, agrupado["acumulado"].max() * 1.2)
    ax1.grid(axis="y", color=GRAY, alpha=0.25, linestyle="--", zorder=0)
    ax1.set_axisbelow(True)
    ax1.set_title("Evolução dos gastos ao longo da obra")

    linhas = [barras, linha[0]]
    ax1.legend(linhas, [l.get_label() for l in linhas], loc="upper left", frameon=False)

    _aplicar_estilo_figura(fig, ax1)
    ax2.tick_params(colors="#0A5C73")
    ax2.spines["right"].set_color(GRAY)
    for spine in ax2.spines.values():
        spine.set_visible(False)
    fig.tight_layout()
    return fig
