"""Gera as figuras (matplotlib) reaproveitadas na tela e no PDF final."""
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.use("Agg")

# Paleta da Azul Administradora (navy petróleo + azul-céu). NAVY e CYAN são
# as cores exatas extraídas da logo (data/assets/logo_azul.png), amostradas
# por pixel: navy = RGB(0,84,116), ciano = RGB(65,171,211). NAVY2/CYAN2 são
# variações (mais clara/escura) usadas em elementos secundários.
NAVY = "#005474"
NAVY2 = "#0A6E93"
CYAN = "#41ABD3"
CYAN2 = "#6FC3E0"
GRAY = "#8FA6B2"
TOMATO = "#F25C54"

# Paleta vívida para gráficos com várias categorias (pizza/barras) - cores bem
# distintas entre si (não apenas variações de azul), para as fatias/barras
# pequenas continuarem legíveis mesmo quando várias categorias têm valores
# próximos ou baixos.
AMARELO = "#F2A93B"
VERDE = "#3DBE7A"
ROXO = "#8B5FBF"
ROSA = "#E0559B"

CORES_CATEGORICAS = [CYAN, TOMATO, AMARELO, VERDE, ROXO, NAVY, ROSA]


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


def _grafico_ordinaria_x_extraordinaria(totais: dict, titulo: str):
    """Barras horizontais (em vez de pizza) para as 2 categorias
    ordinária/extraordinária - evita o corte de rótulo que a pizza sofria
    quando uma fatia era muito maior que a outra (rótulo posicionado perto
    da borda da figura)."""
    fig, ax = plt.subplots(figsize=(8, 3))
    categorias = ["Ordinária (recorrente)", "Extraordinária/eventual"]
    valores = [totais["ordinaria"], totais["extraordinaria"]]
    total = sum(valores) or 1
    barras = ax.barh(categorias, valores, color=[CYAN, TOMATO], height=0.55)
    for barra, valor in zip(barras, valores):
        pct = valor / total * 100
        ax.text(
            barra.get_width() + total * 0.015, barra.get_y() + barra.get_height() / 2,
            f"{pct:.1f}%", va="center", ha="left", color=NAVY, fontweight="bold",
        )
    ax.set_xlim(0, total * 1.2)
    ax.invert_yaxis()
    ax.set_xlabel("R$")
    ax.set_title(titulo)
    _aplicar_estilo_figura(fig, ax)
    fig.tight_layout()
    return fig


def grafico_receitas_ordinaria_x_extraordinaria(resultado):
    totais = _total_por_classificacao(resultado.receitas_classificadas)
    return _grafico_ordinaria_x_extraordinaria(totais, "Receitas: ordinárias x extraordinárias")


def grafico_despesas_por_categoria_pai(resultado):
    """Percentual das despesas apuradas por categoria (Com Pessoal, Mensais,
    Manutenção, Diversas, Serviços Terceirizados etc.) - barras horizontais
    (em vez de pizza) para as categorias pequenas nao terem seus rotulos/
    percentuais sobrepostos, o que acontecia com muitas fatias pequenas."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if not resultado.despesas_previstas:
        ax.text(0.5, 0.5, "Sem despesas no período", ha="center", va="center", color=GRAY)
        ax.set_xticks([])
        ax.set_yticks([])
        fig.tight_layout()
        return fig

    df = pd.DataFrame(
        [{"categoria_pai": l.categoria_pai, "valor": l.valor_historico} for l in resultado.despesas_previstas]
    )
    agrupado = df.groupby("categoria_pai", as_index=False)["valor"].sum().sort_values("valor", ascending=True)
    total = agrupado["valor"].sum() or 1
    cores = [CORES_CATEGORICAS[i % len(CORES_CATEGORICAS)] for i in range(len(agrupado))]

    barras = ax.barh(agrupado["categoria_pai"], agrupado["valor"], color=cores, height=0.6)
    for barra, valor in zip(barras, agrupado["valor"]):
        pct = valor / total * 100
        ax.text(
            barra.get_width() + total * 0.015, barra.get_y() + barra.get_height() / 2,
            f"{pct:.1f}%", va="center", ha="left", color=NAVY, fontweight="bold", fontsize=9,
        )
    ax.set_xlim(0, total * 1.18)
    ax.set_xlabel("R$")
    ax.set_title("Despesas por categoria")
    _aplicar_estilo_figura(fig, ax)
    fig.tight_layout()
    return fig


def grafico_despesas_ordinaria_x_extraordinaria(resultado):
    totais = _total_por_classificacao(resultado.despesas_classificadas)
    return _grafico_ordinaria_x_extraordinaria(totais, "Despesas: ordinárias x extraordinárias")


def grafico_evolucao_inadimplencia(resultado):
    df = resultado.concentracao_inadimplencia
    fig, ax = plt.subplots(figsize=(8, 4))
    if df is None or df.empty:
        ax.text(0.5, 0.5, "Sem cobranças em aberto no período", ha="center", va="center", color=GRAY)
        ax.set_xticks([])
        ax.set_yticks([])
    else:
        ax.plot(df["competencia"], df["valor_total"], color=NAVY, linewidth=2.5, marker="o", markersize=6)
        ax.fill_between(range(len(df)), df["valor_total"], color=CYAN, alpha=0.3)
        if resultado.mes_pico_inadimplencia in set(df["competencia"]):
            idx_pico = df.index[df["competencia"] == resultado.mes_pico_inadimplencia][0]
            ax.plot(
                df.loc[idx_pico, "competencia"], df.loc[idx_pico, "valor_total"],
                marker="o", markersize=9, color=TOMATO, zorder=5,
            )
        ax.set_ylabel("R$ em aberto")
        ax.set_title("Evolução da inadimplência por mês de competência")
        ax.tick_params(axis="x", rotation=45)
    _aplicar_estilo_figura(fig, ax)
    fig.tight_layout()
    return fig
