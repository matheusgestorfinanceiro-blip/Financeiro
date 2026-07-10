"""Gráficos (matplotlib) do sistema de finanças pessoais.

Paleta semântica pedida: despesas em tons de vermelho, receitas em tons de
azul, saldo em verde (positivo) ou vermelho (negativo).
"""
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

AZUL = "#1D4ED8"
AZUL_CLARO = "#93C5FD"
VERMELHO = "#DC2626"
VERMELHO_CLARO = "#FCA5A5"
VERDE = "#16A34A"
CINZA = "#6B7280"


def _tons(mapa_cores: str, quantidade: int) -> list[str]:
    """Gera `quantidade` tons a partir de um colormap (Reds ou Blues)."""
    colormap = matplotlib.colormaps[mapa_cores]
    if quantidade == 1:
        return [colormap(0.65)]
    return [colormap(0.35 + 0.55 * i / max(quantidade - 1, 1)) for i in range(quantidade)]


def _estilo_figura(fig, ax):
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    for spine in ax.spines.values():
        spine.set_color(CINZA)


def grafico_pizza_categoria(por_categoria: dict, tipo: str):
    """tipo: 'despesa' (tons de vermelho) ou 'receita' (tons de azul)."""
    fig, ax = plt.subplots(figsize=(5, 4))
    _estilo_figura(fig, ax)
    if not por_categoria:
        ax.text(0.5, 0.5, "Sem lançamentos", ha="center", va="center", color=CINZA)
        ax.axis("off")
        return fig

    categorias = list(por_categoria.keys())
    valores = list(por_categoria.values())
    mapa = "Reds" if tipo == "despesa" else "Blues"
    cores = _tons(mapa, len(categorias))
    ax.pie(
        valores,
        labels=categorias,
        autopct="%1.1f%%",
        colors=cores,
        textprops={"color": "#1F2937", "fontsize": 8},
    )
    ax.set_title(
        "Despesas por categoria" if tipo == "despesa" else "Receitas por categoria",
        color="#1F2937",
    )
    return fig


def grafico_evolucao_mensal(resumos: list):
    """Barras de receita (azul) x despesa (vermelho) e linha de saldo (verde/vermelho)."""
    fig, ax = plt.subplots(figsize=(8, 4.2))
    _estilo_figura(fig, ax)

    rotulos = [f"{r.mes:02d}/{r.ano}" for r in resumos]
    receitas = [r.total_receitas for r in resumos]
    despesas = [r.total_despesas for r in resumos]
    saldos = [r.saldo for r in resumos]

    x = range(len(resumos))
    largura = 0.35
    ax.bar([i - largura / 2 for i in x], receitas, largura, label="Receitas", color=AZUL)
    ax.bar([i + largura / 2 for i in x], despesas, largura, label="Despesas", color=VERMELHO)

    ax2 = ax.twinx()
    cores_saldo = [VERDE if s >= 0 else VERMELHO for s in saldos]
    ax2.plot(x, saldos, color=CINZA, linewidth=1.5, zorder=3)
    ax2.scatter(x, saldos, color=cores_saldo, zorder=4, s=40, label="Saldo")
    ax2.set_ylabel("Saldo (R$)", color="#1F2937")
    ax2.tick_params(colors="#1F2937")

    ax.set_xticks(list(x))
    ax.set_xticklabels(rotulos, rotation=0, color="#1F2937")
    ax.tick_params(colors="#1F2937")
    ax.set_ylabel("R$", color="#1F2937")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    return fig


def grafico_por_pessoa(por_usuario: dict):
    """Barras comparando receita (azul) e despesa (vermelho) de cada pessoa."""
    from src.pessoal.modelos import TIPO_DESPESA, TIPO_RECEITA

    fig, ax = plt.subplots(figsize=(6.5, 4))
    _estilo_figura(fig, ax)
    if not por_usuario:
        ax.text(0.5, 0.5, "Sem lançamentos", ha="center", va="center", color=CINZA)
        ax.axis("off")
        return fig

    pessoas = list(por_usuario.keys())
    receitas = [por_usuario[p].get(TIPO_RECEITA, 0.0) for p in pessoas]
    despesas = [por_usuario[p].get(TIPO_DESPESA, 0.0) for p in pessoas]

    x = range(len(pessoas))
    largura = 0.35
    ax.bar([i - largura / 2 for i in x], receitas, largura, label="Receitas", color=AZUL)
    ax.bar([i + largura / 2 for i in x], despesas, largura, label="Despesas", color=VERMELHO)
    ax.set_xticks(list(x))
    ax.set_xticklabels(pessoas, color="#1F2937")
    ax.tick_params(colors="#1F2937")
    ax.set_ylabel("R$", color="#1F2937")
    ax.set_title("Receitas e despesas por pessoa", color="#1F2937")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    return fig
