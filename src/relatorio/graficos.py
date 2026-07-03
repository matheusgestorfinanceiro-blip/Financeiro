"""Gera as figuras (matplotlib) reaproveitadas na tela e no PDF final."""
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.use("Agg")


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
    ax.barh([i + altura / 2 for i in y], agrupado["historico"], height=altura, label="Histórico (12 meses)")
    ax.barh([i - altura / 2 for i in y], agrupado["previsto"], height=altura, label="Previsto")
    ax.set_yticks(list(y))
    ax.set_yticklabels(agrupado["categoria"])
    ax.set_xlabel("R$")
    ax.set_title("Despesas: histórico x previsto, por categoria")
    ax.legend()
    fig.tight_layout()
    return fig


def grafico_evolucao_mensal(resultado):
    meses = list(resultado.total_despesas_historico_por_mes.keys())
    despesas = list(resultado.total_despesas_historico_por_mes.values())
    receitas = list(resultado.total_receitas_historico_por_mes.values())

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(meses, receitas, marker="o", label="Receitas")
    ax.plot(meses, despesas, marker="o", label="Despesas")
    ax.set_ylabel("R$")
    ax.set_title("Evolução mensal (últimos 12 meses)")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    fig.tight_layout()
    return fig


def grafico_composicao_taxa_condominial(resultado):
    despesa_pura = resultado.total_despesas_previsto - resultado.total_outras_receitas_previsto
    fatias = {
        "Despesas (líq. outras receitas)": max(despesa_pura, 0),
        "Fundo de reserva": resultado.fundo_reserva_valor,
        "Taxa de administração": resultado.taxa_administracao_valor,
    }
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(fatias.values(), labels=fatias.keys(), autopct="%1.1f%%")
    ax.set_title("Composição da taxa condominial prevista")
    fig.tight_layout()
    return fig


def grafico_indicador_inadimplencia(resultado):
    fig, ax = plt.subplots(figsize=(5, 3))
    pct = resultado.percentual_inadimplencia * 100
    ax.barh([""], [pct], color="tomato")
    ax.set_xlim(0, max(30, pct + 5))
    ax.set_xlabel("% de unidades inadimplentes")
    ax.set_title(f"Inadimplência considerada: {pct:.2f}%")
    fig.tight_layout()
    return fig
