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


def _descricao_fundo_reserva(resultado) -> str:
    if not resultado.possui_fundo_reserva:
        return "Este condomínio não possui fundo de reserva nesta previsão."
    if resultado.fundo_reserva_modo == "valor_fixo":
        return "Fundo de reserva: valor fixo por unidade."
    return f"Fundo de reserva: {fmt_pct(resultado.fundo_reserva_percentual)} sobre a receita de rateio."


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

    abas = st.tabs(["1. Receitas", "2. Despesas", "3. Inadimplência", "4. Reajuste"])

    with abas[0]:
        totais = _total_por_classificacao(resultado.receitas_classificadas)
        col1, col2 = st.columns(2)
        col1.metric("Receita ordinária (histórico)", fmt_moeda(totais["ordinaria"]))
        col2.metric("Receita extraordinária/eventual (histórico)", fmt_moeda(totais["extraordinaria"]))
        col1.metric("Receita de rateio necessária (previsto)", fmt_moeda(resultado.receita_rateio_necessaria))
        col2.metric("Outras receitas previstas", fmt_moeda(resultado.total_outras_receitas_previsto))
        st.pyplot(grafico_receitas_ordinaria_x_extraordinaria(resultado))
        st.caption(
            "Classificação baseada na regularidade mensal do histórico (não é uma classificação contábil "
            "oficial): receitas com valores parecidos ao longo dos 12 meses são tratadas como ordinárias; "
            "receitas concentradas em poucos meses, como extraordinárias/eventuais."
        )

    with abas[1]:
        totais = _total_por_classificacao(resultado.despesas_classificadas)
        col1, col2 = st.columns(2)
        col1.metric("Despesa ordinária (histórico)", fmt_moeda(totais["ordinaria"]))
        col2.metric("Despesa extraordinária/eventual (histórico)", fmt_moeda(totais["extraordinaria"]))
        col1.metric("Total de despesas previsto", fmt_moeda(resultado.total_despesas_previsto))
        col2.metric("Total de despesas no histórico", fmt_moeda(resultado.total_despesas_historico))
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
        st.metric("Percentual de inadimplência considerado", fmt_pct(resultado.percentual_inadimplencia))
        st.pyplot(grafico_evolucao_inadimplencia(resultado))
        if resultado.mes_pico_inadimplencia:
            st.caption(
                f"Mês de competência com maior concentração de cobranças em aberto: "
                f"**{resultado.mes_pico_inadimplencia}**."
            )
        else:
            st.caption("Não há cobranças em aberto registradas no relatório de inadimplentes enviado.")

    with abas[3]:
        st.metric("Percentual de reajuste apurado", fmt_pct(resultado.percentual_reajuste_automatico))
        st.markdown("**Fundo de reserva**")
        st.write(fmt_moeda(resultado.fundo_reserva_valor))
        st.caption(_descricao_fundo_reserva(resultado))
        if resultado.valor_por_unidade_sugerido_pelo_sistema is not None:
            st.info(
                "Você definiu um valor único por unidade. Para comparação, o sistema calcularia "
                f"automaticamente **{fmt_moeda(resultado.valor_por_unidade_sugerido_pelo_sistema)}** por unidade "
                "com base nas despesas, fundo de reserva e outras receitas."
            )
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
