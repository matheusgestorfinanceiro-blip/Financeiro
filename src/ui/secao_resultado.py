"""Tela 3: as páginas finais da previsão (receitas, despesas, inadimplência,
balanço consolidado, reajuste) + botão de download do PDF completo (6 páginas,
incluindo a capa)."""
import streamlit as st

from src.relatorio.graficos import (
    grafico_despesas_ordinaria_x_extraordinaria,
    grafico_evolucao_inadimplencia,
    grafico_receitas_ordinaria_x_extraordinaria,
)
from src.relatorio.pdf_export import _calcular_balanco, _despesas_previstas_ordinarias, gerar_pdf_previsao
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
    st.header("📊 3. Previsão orçamentária — resultado final")
    st.caption(f"Relatório gerado em {resultado.data_geracao}")

    abas = st.tabs(["💰 1. Arrecadações", "🧾 2. Despesas", "⚠️ 3. Inadimplência", "⚖️ 4. Balanço", "📈 5. Reajuste"])

    with abas[0]:
        totais = _total_por_classificacao(resultado.receitas_classificadas)
        col1, col2 = st.columns(2)
        col1.metric("Ordinário (recorrente ou mensal)", fmt_moeda(totais["ordinaria"]))
        col2.metric("Extraordinário (eventual)", fmt_moeda(totais["extraordinaria"]))
        col1.metric("Arrecadação prevista mensalmente", fmt_moeda(resultado.arrecadacao_prevista_mensal))
        col2.metric("Outras receitas (identificadas no período)", fmt_moeda(resultado.total_outras_receitas_previsto))
        if resultado.possui_desconto_pontualidade and resultado.desconto_pontualidade_total_mensal:
            descricao_desconto = (
                fmt_moeda(resultado.desconto_pontualidade_valor) + " por unidade"
                if resultado.desconto_pontualidade_modo == "valor_fixo"
                else fmt_pct(resultado.desconto_pontualidade_valor)
            )
            st.caption(
                f"Já descontado o desconto de pontualidade configurado ({descricao_desconto}): "
                f"{fmt_moeda(resultado.desconto_pontualidade_total_mensal)} a menos por mês no total."
            )
        if resultado.unidades_isentas:
            nomes_isentas = ", ".join(
                f"{unidade} ({fmt_pct(percentual)})" for unidade, percentual in resultado.unidades_isentas
            )
            st.caption(
                f"Já descontada a isenção configurada para {nomes_isentas}: "
                f"{fmt_moeda(resultado.isencao_total_mensal)} a menos por mês no total."
            )
        if resultado.desconto_receita_historico_anual:
            st.caption(
                f"O valor previsto já está líquido de {fmt_moeda(resultado.desconto_receita_historico_anual / 12)} "
                "por mês em descontos identificados no campo de receita do histórico (ex: isenções, compensações "
                "bancárias)."
            )
        st.pyplot(grafico_receitas_ordinaria_x_extraordinaria(resultado))
        col_legenda1, col_legenda2, _ = st.columns([1, 1, 4])
        col_legenda1.badge("Ordinária", icon="🔵", color="blue")
        col_legenda2.badge("Extraordinária", icon="⚪", color="gray")
        st.caption(
            "Classificação definida manualmente pelo usuário na tela de upload dos documentos: receitas "
            "marcadas como extraordinárias entram nesse grupo; as demais, não marcadas, são tratadas "
            "como ordinárias."
        )

        if resultado.outras_arrecadacoes_detalhe:
            st.markdown("💧 **Outras arrecadações configuradas**")
            cols = st.columns(len(resultado.outras_arrecadacoes_detalhe))
            for col, (nome, valor) in zip(cols, resultado.outras_arrecadacoes_detalhe):
                col.metric(nome, fmt_moeda(valor))

        if resultado.valores_por_unidade is not None and not resultado.valores_por_unidade.empty:
            st.markdown("🏠 **Valores por unidade**")
            nomes_outras_arrecadacoes = [nome for nome, _ in resultado.outras_arrecadacoes_detalhe]
            colunas_tabela = ["unidade", "rateio", "fundo_reserva", *nomes_outras_arrecadacoes, "total"]
            column_config = {
                "unidade": st.column_config.TextColumn("Unidade"),
                "rateio": st.column_config.NumberColumn("Rateio mensal", format="R$ %.2f"),
                "fundo_reserva": st.column_config.NumberColumn("Fundo de reserva", format="R$ %.2f"),
                "total": st.column_config.NumberColumn("Total", format="R$ %.2f"),
            }
            for nome in nomes_outras_arrecadacoes:
                column_config[nome] = st.column_config.NumberColumn(nome, format="R$ %.2f")
            st.dataframe(
                resultado.valores_por_unidade[colunas_tabela],
                use_container_width=True,
                hide_index=True,
                column_config=column_config,
            )

    with abas[1]:
        totais = _total_por_classificacao(resultado.despesas_classificadas)
        col1, col2, col3 = st.columns(3)
        col1.metric("Ordinárias (recorrente ou mensal)", fmt_moeda(totais["ordinaria"]))
        col2.metric("Extraordinárias (eventuais)", fmt_moeda(totais["extraordinaria"]))
        col3.metric("Total apurado no período", fmt_moeda(resultado.total_despesas_historico))
        st.pyplot(grafico_despesas_ordinaria_x_extraordinaria(resultado))
        col_legenda1, col_legenda2, _ = st.columns([1, 1, 4])
        col_legenda1.badge("Ordinária", icon="🔵", color="blue")
        col_legenda2.badge("Extraordinária", icon="⚪", color="gray")

        import pandas as pd

        df = pd.DataFrame(
            [
                {
                    "Categoria": l.categoria_pai,
                    "Subcategoria": l.subcategoria,
                    "Histórico": l.valor_historico,
                }
                for l in resultado.despesas_previstas
            ]
        )
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Histórico": st.column_config.NumberColumn("Histórico", format="R$ %.2f"),
            },
        )

    with abas[2]:
        tem_unidades = resultado.inadimplencia_valor_por_unidade is not None and not resultado.inadimplencia_valor_por_unidade.empty
        tem_concentracao = resultado.concentracao_inadimplencia is not None and not resultado.concentracao_inadimplencia.empty
        qtd_unidades = len(resultado.inadimplencia_unidades)
        max_meses_atraso = int(resultado.inadimplencia_valor_por_unidade["meses_em_atraso"].max()) if tem_unidades else 0
        tem_grafico = tem_concentracao and (max_meses_atraso > 1 or qtd_unidades > 1)

        col1, col2 = st.columns(2)
        col1.metric("Percentual de inadimplência apurado", fmt_pct(resultado.percentual_inadimplencia))
        col2.metric("Valor principal em aberto", fmt_moeda(resultado.inadimplencia_valor_total))

        if tem_grafico:
            st.pyplot(grafico_evolucao_inadimplencia(resultado))
            st.caption(
                f"Mês de competência com maior concentração de cobranças em aberto: "
                f"**{resultado.mes_pico_inadimplencia}**."
            )

        if tem_unidades:
            st.markdown("📋 **Unidades inadimplentes**")
            st.dataframe(
                resultado.inadimplencia_valor_por_unidade.rename(
                    columns={"unidade": "Unidade", "valor_total": "Valor em aberto", "meses_em_atraso": "Meses em atraso"}
                ),
                use_container_width=True,
                hide_index=True,
                column_config={"Valor em aberto": st.column_config.NumberColumn("Valor em aberto", format="R$ %.2f")},
            )
        else:
            st.caption("Não há unidades inadimplentes identificadas no relatório de inadimplentes enviado.")

    with abas[3]:
        import pandas as pd

        balanco = _calcular_balanco(resultado)

        st.markdown("💰 **Receita (anual)**")
        df_receita = pd.DataFrame(
            [
                {"Item": nome, "Anual": valor, "Mensal": valor / 12, "% do total": valor / balanco["receita_total"] if balanco["receita_total"] else 0.0}
                for nome, valor in balanco["receita_itens"]
            ]
        )
        st.dataframe(
            df_receita,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Anual": st.column_config.NumberColumn("Anual", format="R$ %.2f"),
                "Mensal": st.column_config.NumberColumn("Mensal", format="R$ %.2f"),
                "% do total": st.column_config.NumberColumn("% do total", format="percent"),
            },
        )
        st.metric("Total da receita (12 meses)", fmt_moeda(balanco["receita_total"]))

        st.markdown("🧾 **Despesas ordinárias por categoria (anual)**")
        despesas_previstas_ordinarias = _despesas_previstas_ordinarias(resultado)
        despesas_total = balanco["despesas_total"]
        df_despesas = pd.DataFrame(
            [
                {
                    "Categoria": l.categoria_pai,
                    "Subcategoria": l.subcategoria,
                    "Anual": l.valor_historico,
                    "Mensal": l.valor_historico / 12,
                    "% do total": l.valor_historico / despesas_total if despesas_total else 0.0,
                }
                for l in despesas_previstas_ordinarias
            ]
        )
        st.dataframe(
            df_despesas,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Anual": st.column_config.NumberColumn("Anual", format="R$ %.2f"),
                "Mensal": st.column_config.NumberColumn("Mensal", format="R$ %.2f"),
                "% do total": st.column_config.NumberColumn("% do total", format="percent"),
            },
        )
        st.metric("Total das despesas ordinárias (12 meses)", fmt_moeda(despesas_total))

        st.markdown("⚖️ **Inadimplência e saldo final**")
        col1, col2 = st.columns(2)
        col1.metric(f"Inadimplência ({fmt_pct(resultado.percentual_inadimplencia)})", fmt_moeda(balanco["inadimplencia_valor"]))
        col2.metric("Total geral (despesas + inadimplência)", fmt_moeda(balanco["total_geral"]))
        if balanco["saldo_final"] >= 0:
            st.badge("Superávit", icon="✅", color="green")
            st.success(f"A previsão fecha em superávit de {fmt_moeda(balanco['saldo_final'])}, sem considerar reajuste.", icon="✅")
        else:
            st.badge("Déficit", icon="⚠️", color="orange")
            st.warning(
                f"A previsão fecha em déficit de {fmt_moeda(abs(balanco['saldo_final']))}, sem considerar "
                "reajuste — consulte a aba de Reajuste para o percentual proposto.",
                icon="⚠️",
            )

    with abas[4]:
        if resultado.percentual_reajuste_automatico > 0:
            st.badge("Reajuste necessário", icon="📈", color="orange")
        else:
            st.badge("Sem reajuste necessário", icon="✅", color="green")
        st.metric("Percentual de reajuste apurado", fmt_pct(resultado.percentual_reajuste_automatico))
        st.caption(
            "Calculado comparando a receita total prevista (rateio + fundo de reserva + outras "
            "arrecadações configuradas, sem receitas extraordinárias ou taxas extras do histórico) "
            "com as despesas ordinárias (sem despesas extraordinárias) e a inadimplência esperada "
            "do período."
        )
        if resultado.observacoes:
            st.markdown("📝 **Observações**")
            st.write(escapar_markdown(resultado.observacoes))

    st.divider()
    pdf_bytes = gerar_pdf_previsao(resultado)
    st.download_button(
        "📄 Baixar relatório completo em PDF",
        data=pdf_bytes,
        file_name=f"previsao_orcamentaria_{resultado.nome_condominio}.pdf".replace(" ", "_"),
        mime="application/pdf",
    )
