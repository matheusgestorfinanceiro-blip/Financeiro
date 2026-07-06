"""Tela 2: dados obrigatórios + área de análise (dados opcionais)."""
import pandas as pd
import streamlit as st

from src.calculo.periodo import limpar_nome_condominio, sugerir_periodo
from src.models.schema import AjusteManual, DadosFormulario


def renderizar_secao_formulario(dados_demonstrativo):
    st.header("2. Dados da previsão orçamentária")

    nome_padrao = limpar_nome_condominio(dados_demonstrativo.condominio) if dados_demonstrativo else ""
    periodo_inicio_padrao, periodo_fim_padrao = (
        sugerir_periodo(dados_demonstrativo.meses) if dados_demonstrativo else ("", "")
    )

    with st.form("form_previsao"):
        st.subheader("Dados obrigatórios")

        nome_condominio = st.text_input("Nome do condomínio", value=nome_padrao)

        col1, col2 = st.columns(2)
        with col1:
            periodo_inicio = st.text_input("Início do período (ex: 2026-08)", value=periodo_inicio_padrao)
        with col2:
            periodo_fim = st.text_input("Fim do período (ex: 2027-07)", value=periodo_fim_padrao)

        st.caption(
            "O reajuste das despesas e o percentual do fundo de reserva são calculados "
            "automaticamente a partir do Demonstrativo de Receitas e Despesas."
        )

        numero_unidades = st.number_input("Número de unidades", min_value=1, value=40, step=1)

        st.markdown("**Rateio entre unidades**")
        rateio_tipo_label = st.radio("Tipo de rateio", ["Taxa única por unidade", "Por fração ideal"], horizontal=True)
        fracoes_ideais = None
        valor_unico_por_unidade = None
        if rateio_tipo_label == "Taxa única por unidade":
            st.caption(
                "Informe o valor que será cobrado de cada unidade. Esse valor substitui o "
                "cálculo automático (que continua sendo mostrado como referência no resumo executivo)."
            )
            valor_informado = st.number_input("Valor por unidade (R$)", min_value=0.0, value=0.0, step=10.0)
            valor_unico_por_unidade = valor_informado if valor_informado > 0 else None
        else:
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
            "(sobrescreve o reajuste automático só na categoria escolhida)"
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
                        "Reajuste manual (%)", help="Deixe em branco para usar o reajuste automático."
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

    formulario = DadosFormulario(
        nome_condominio=nome_condominio,
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        numero_unidades=int(numero_unidades),
        rateio_tipo="fracao_ideal" if rateio_tipo_label == "Por fração ideal" else "igualitario",
        valor_unico_por_unidade=valor_unico_por_unidade,
        fracoes_ideais=fracoes_ideais,
        observacoes=observacoes,
        ajustes_manuais=ajustes_manuais,
    )
    st.session_state["dados_formulario"] = formulario
    return formulario
