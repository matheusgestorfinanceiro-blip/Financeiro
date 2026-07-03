"""Tela 2: dados obrigatórios + área de análise (dados opcionais)."""
import pandas as pd
import streamlit as st

from src.models.schema import AjusteManual, DadosFormulario


def renderizar_secao_formulario(dados_demonstrativo):
    st.header("2. Dados da previsão orçamentária")

    with st.form("form_previsao"):
        st.subheader("Dados obrigatórios")

        nome_padrao = dados_demonstrativo.condominio if dados_demonstrativo else ""
        nome_condominio = st.text_input("Nome do condomínio", value=nome_padrao)

        col1, col2 = st.columns(2)
        with col1:
            periodo_inicio = st.text_input("Início do período (ex: 2026-08)")
        with col2:
            periodo_fim = st.text_input("Fim do período (ex: 2027-07)")

        percentual_reajuste = st.number_input(
            "Percentual de reajuste/inflação esperado (%)", min_value=0.0, max_value=200.0, value=6.0, step=0.5
        ) / 100

        numero_unidades = st.number_input("Número de unidades", min_value=1, value=40, step=1)

        st.markdown("**Fundo de reserva**")
        col3, col4 = st.columns(2)
        with col3:
            fundo_reserva_base = st.radio(
                "Calculado sobre", ["Receita de rateio", "Total de despesas previstas"], horizontal=True
            )
        with col4:
            fundo_reserva_percentual = st.number_input(
                "Percentual do fundo de reserva (%)", min_value=0.0, max_value=90.0, value=5.0, step=0.5
            ) / 100

        st.markdown("**Taxa de administração**")
        taxa_administracao_modo_label = st.radio(
            "Modo de cálculo",
            ["Percentual sobre despesas", "Percentual sobre rateio", "Valor fixo por unidade (R$/mês)"],
            horizontal=True,
        )
        if taxa_administracao_modo_label == "Valor fixo por unidade (R$/mês)":
            taxa_administracao_valor = st.number_input("Valor fixo por unidade (R$)", min_value=0.0, value=25.0, step=1.0)
        else:
            taxa_administracao_valor = st.number_input(
                "Percentual da taxa de administração (%)", min_value=0.0, max_value=90.0, value=8.0, step=0.5
            ) / 100

        st.markdown("**Rateio entre unidades**")
        rateio_tipo_label = st.radio("Tipo de rateio", ["Igualitário", "Por fração ideal"], horizontal=True)
        fracoes_ideais = None
        if rateio_tipo_label == "Por fração ideal":
            st.caption("Preencha a fração ideal de cada unidade (a soma não precisa ser exatamente 1,0).")
            tabela_inicial = pd.DataFrame(
                {"unidade": [f"Unidade {i+1}" for i in range(int(numero_unidades))], "fracao": [1 / numero_unidades] * int(numero_unidades)}
            )
            fracoes_ideais = st.data_editor(
                tabela_inicial, num_rows="dynamic", use_container_width=True, key="tabela_fracoes_ideais"
            )

        st.divider()
        st.subheader("Ambiente de análise (opcional)")
        observacoes = st.text_area("Observações para o resumo executivo")

        quer_ajustes = st.checkbox(
            "Quero fazer ajustes manuais de reajuste em categorias específicas de despesa "
            "(sobrescreve o reajuste padrão só na categoria escolhida)"
        )
        ajustes_tabela = None
        if quer_ajustes and dados_demonstrativo is not None and not dados_demonstrativo.df_despesas.empty:
            subcategorias = dados_demonstrativo.df_despesas["subcategoria"].tolist()
            tabela_ajustes = pd.DataFrame(
                {
                    "subcategoria": subcategorias,
                    "reajuste_manual_percentual": pd.Series([float("nan")] * len(subcategorias), dtype="float64"),
                }
            )
            ajustes_tabela = st.data_editor(
                tabela_ajustes,
                use_container_width=True,
                height=200,
                disabled=["subcategoria"],
                key="tabela_ajustes_manuais",
                column_config={
                    "reajuste_manual_percentual": st.column_config.NumberColumn(
                        "Reajuste manual (%)", help="Deixe em branco para usar o reajuste padrão."
                    )
                },
            )

        enviado = st.form_submit_button("Confirmar dados")

    if not enviado:
        return None

    ajustes_manuais = []
    if ajustes_tabela is not None:
        for _, row in ajustes_tabela.iterrows():
            if pd.notna(row["reajuste_manual_percentual"]):
                ajustes_manuais.append(
                    AjusteManual(subcategoria=row["subcategoria"], percentual_reajuste=float(row["reajuste_manual_percentual"]) / 100)
                )

    modo_map = {
        "Percentual sobre despesas": "percentual_despesas",
        "Percentual sobre rateio": "percentual_rateio",
        "Valor fixo por unidade (R$/mês)": "valor_fixo",
    }

    formulario = DadosFormulario(
        nome_condominio=nome_condominio,
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        percentual_reajuste=percentual_reajuste,
        numero_unidades=int(numero_unidades),
        fundo_reserva_percentual=fundo_reserva_percentual,
        fundo_reserva_base="rateio" if fundo_reserva_base == "Receita de rateio" else "despesas",
        taxa_administracao_modo=modo_map[taxa_administracao_modo_label],
        taxa_administracao_valor=taxa_administracao_valor,
        rateio_tipo="fracao_ideal" if rateio_tipo_label == "Por fração ideal" else "igualitario",
        fracoes_ideais=fracoes_ideais,
        observacoes=observacoes,
        ajustes_manuais=ajustes_manuais,
    )
    st.session_state["dados_formulario"] = formulario
    return formulario
