"""Tela 3: as páginas finais da previsão (receitas, despesas, inadimplência,
reajuste) + botão de download do PDF completo (5 páginas, incluindo a capa)."""
import streamlit as st

from src.relatorio.graficos import (
    grafico_despesas_ordinaria_x_extraordinaria,
    grafico_evolucao_inadimplencia,
    grafico_receitas_ordinaria_x_extraordinaria,
)
from src.relatorio.pdf_export import gerar_pdf_previsao
from src.ui.formatacao import escapar_markdown, fmt_moeda, fmt_pct


def _total_por_classificacao(df) -> dict:
    if df is None or df.empty:
        return {"ordinaria": 0.0, "extraordinaria": 0.0}
    agrupado = df.groupby("classificacao")["total"].sum()
    return {
        "ordinaria": float(agrupado.get("ordinaria", 0.0)),
        "extraordinaria": float(agrupado.get("extraordinaria", 0.0)),
    }


def renderizar_secao_resultado(resultado):
    st.header("3. Previsão orçamentária — resultado final")
    st.caption(f"Relatório gerado em {resultado.data_geracao}")

    abas = st.tabs(["1. Arrecadações", "2. Despesas", "3. Inadimplência", "4. Reajuste"])

    with abas[0]:
        totais = _total_por_classificacao(resultado.receitas_classificadas)
        col1, col2 = st.columns(2)
        col1.metric("Ordinário (recorrente ou mensal)", fmt_moeda(totais["ordinaria"]))
        col2.metric("Extraordinário (eventual)", fmt_moeda(totais["extraordinaria"]))
        col1.metric("Arrecadação prevista mensalmente", fmt_moeda(resultado.arrecadacao_prevista_mensal))
        col2.metric("Outras receitas (identificadas no período)", fmt_moeda(resultado.total_outras_receitas_previsto))
        st.pyplot(grafico_receitas_ordinaria_x_extraordinaria(resultado))
        st.caption(
            "Classificação baseada na regularidade mensal do histórico (não é uma classificação contábil "
            "oficial): receitas com valores parecidos ao longo dos 12 meses são tratadas como ordinárias; "
            "receitas concentradas em poucos meses, como extraordinárias/eventuais."
        )

        if resultado.outras_arrecadacoes_detalhe:
            st.markdown("**Outras arrecadações configuradas**")
            cols = st.columns(len(resultado.outras_arrecadacoes_detalhe))
            for col, (nome, valor) in zip(cols, resultado.outras_arrecadacoes_detalhe):
                col.metric(nome, fmt_moeda(valor))

        if resultado.valores_por_unidade is not None and not resultado.valores_por_unidade.empty:
            st.markdown("**Valores por unidade**")
            st.dataframe(resultado.valores_por_unidade, use_container_width=True)

    with abas[1]:
        totais = _total_por_classificacao(resultado.despesas_classificadas)
        col1, col2 = st.columns(2)
        col1.metric("Ordinárias (recorrente ou mensal)", fmt_moeda(totais["ordinaria"]))
        col2.metric("Extraordinárias (eventuais)", fmt_moeda(totais["extraordinaria"]))
        col1.metric("Despesas totais previstas para 12 meses", fmt_moeda(resultado.total_despesas_previsto))
        col2.metric("Total das despesas apuradas na análise", fmt_moeda(resultado.total_despesas_historico))
        st.pyplot(grafico_despesas_ordinaria_x_extraordinaria(resultado))

        import pandas as pd

        df = pd.DataFrame(
            [
                {
                    "Categoria": l.categoria_pai,
                    "Subcategoria": l.subcategoria,
                    "Histórico": l.valor_historico,
                    "Reajuste": fmt_pct(l.percentual_reajuste_aplicado),
                    "Previsto": l.valor_previsto,
                    "Ajuste manual": "Sim" if l.ajuste_manual else "",
                }
                for l in resultado.despesas_previstas
            ]
        )
        st.dataframe(df, use_container_width=True)

    with abas[2]:
        tem_grafico = resultado.concentracao_inadimplencia is not None and not resultado.concentracao_inadimplencia.empty
        if tem_grafico:
            st.metric("Percentual de inadimplência apurado", fmt_pct(resultado.percentual_inadimplencia))
            st.pyplot(grafico_evolucao_inadimplencia(resultado))
            st.caption(
                f"Mês de competência com maior concentração de cobranças em aberto: "
                f"**{resultado.mes_pico_inadimplencia}**."
            )
        else:
            col1, col2 = st.columns(2)
            col1.metric("Percentual de inadimplência apurado", fmt_pct(resultado.percentual_inadimplencia))
            col2.metric("Valor total em aberto", fmt_moeda(resultado.inadimplencia_valor_total))
            if resultado.inadimplencia_unidades:
                st.markdown("**Unidades inadimplentes**")
                st.write(", ".join(resultado.inadimplencia_unidades))
            st.caption("Não há dados suficientes no relatório de inadimplentes para montar um gráfico de concentração por mês de competência.")

    with abas[3]:
        st.metric("Percentual de reajuste apurado", fmt_pct(resultado.percentual_reajuste_automatico))
        if resultado.observacoes:
            st.markdown("**Observações**")
            st.write(escapar_markdown(resultado.observacoes))

    st.divider()
    pdf_bytes = gerar_pdf_previsao(resultado)
    st.download_button(
        "Baixar relatório completo em PDF",
        data=pdf_bytes,
        file_name=f"previsao_orcamentaria_{resultado.nome_condominio}.pdf".replace(" ", "_"),
        mime="application/pdf",
    )
