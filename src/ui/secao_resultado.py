"""Tela 3: as 5 páginas finais da previsão + botão de download do PDF."""
import streamlit as st

from src.relatorio.graficos import (
    grafico_composicao_taxa_condominial,
    grafico_despesas_por_categoria,
    grafico_evolucao_mensal,
    grafico_indicador_inadimplencia,
)
from src.relatorio.pdf_export import gerar_pdf_previsao
from src.ui.formatacao import escapar_markdown, fmt_moeda, fmt_pct


def renderizar_secao_resultado(resultado):
    st.header("3. Previsão orçamentária — resultado final")

    abas = st.tabs(
        [
            "1. Resumo executivo",
            "2. Despesas por categoria",
            "3. Receitas e rateio",
            "4. Fundo de reserva",
            "5. Gráficos",
        ]
    )

    with abas[0]:
        col1, col2 = st.columns(2)
        col1.metric("Total de despesas previsto", fmt_moeda(resultado.total_despesas_previsto))
        col2.metric("Total de despesas no histórico", fmt_moeda(resultado.total_despesas_historico))
        col1.metric("Reajuste aplicado (automático)", fmt_pct(resultado.percentual_reajuste_automatico))
        col2.metric("Fundo de reserva previsto", fmt_moeda(resultado.fundo_reserva_valor))
        col1.metric("Valor por unidade (sem ajuste)", fmt_moeda(resultado.valor_por_unidade_sem_ajuste))
        col2.metric(
            f"Valor por unidade (c/ inadimplência {fmt_pct(resultado.percentual_inadimplencia)})",
            fmt_moeda(resultado.valor_por_unidade_com_inadimplencia),
        )
        if resultado.valor_por_unidade_sugerido_pelo_sistema is not None:
            st.info(
                "Você definiu um valor único por unidade. Para comparação, o sistema calcularia "
                f"automaticamente **{fmt_moeda(resultado.valor_por_unidade_sugerido_pelo_sistema)}** por unidade "
                "com base nas despesas, fundo de reserva e outras receitas."
            )
        if not resultado.fundo_reserva_linha_encontrada:
            st.warning(
                "Nenhuma linha de receita de 'fundo de reserva' foi encontrada no demonstrativo — "
                "o percentual do fundo de reserva foi considerado 0%."
            )
        if resultado.fundo_reserva_percentual_limitado:
            st.warning(
                "O percentual do fundo de reserva calculado automaticamente a partir do histórico "
                "ficou muito alto (maior ou igual a 50%) — provavelmente por causa de alguma "
                "contribuição extraordinária pontual nos últimos 12 meses, não uma mensalidade "
                "recorrente. Para o cálculo não travar, o percentual foi limitado a 50%. Vale a "
                "pena conferir manualmente a linha de 'fundo de reserva' no demonstrativo original."
            )
        if resultado.observacoes:
            st.markdown("**Observações**")
            st.write(escapar_markdown(resultado.observacoes))

    with abas[1]:
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
        st.write(f"Tipo de rateio: **{'Fração ideal' if resultado.rateio_tipo == 'fracao_ideal' else 'Taxa única por unidade'}**")
        st.write(f"Inadimplência considerada: **{fmt_pct(resultado.percentual_inadimplencia)}**")
        st.dataframe(resultado.rateio_por_unidade, use_container_width=True)

    with abas[3]:
        st.markdown("**Fundo de reserva**")
        st.write(fmt_moeda(resultado.fundo_reserva_valor))
        st.write(f"Percentual automático: **{fmt_pct(resultado.fundo_reserva_percentual_automatico)}**")
        if not resultado.fundo_reserva_linha_encontrada:
            st.caption("Nenhuma linha de 'fundo de reserva' encontrada no demonstrativo — considerado 0%.")
        if resultado.fundo_reserva_percentual_limitado:
            st.caption(
                "O percentual calculado automaticamente ficou muito alto e foi limitado a 50%. "
                "Confira a linha de 'fundo de reserva' no demonstrativo original."
            )

    with abas[4]:
        st.pyplot(grafico_despesas_por_categoria(resultado))
        st.pyplot(grafico_evolucao_mensal(resultado))
        col1, col2 = st.columns(2)
        with col1:
            st.pyplot(grafico_composicao_taxa_condominial(resultado))
        with col2:
            st.pyplot(grafico_indicador_inadimplencia(resultado))

    st.divider()
    pdf_bytes = gerar_pdf_previsao(resultado)
    st.download_button(
        "Baixar relatório completo em PDF",
        data=pdf_bytes,
        file_name=f"previsao_orcamentaria_{resultado.nome_condominio}.pdf".replace(" ", "_"),
        mime="application/pdf",
    )
