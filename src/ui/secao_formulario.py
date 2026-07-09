"""Tela 2: dados obrigatórios + área de análise (dados opcionais).

Não usa st.form: os campos precisam reagir imediatamente uns aos outros
(ex: escolher "Sim" no fundo de reserva precisa abrir o campo seguinte na
hora), o que um st.form não permite, já que só reprocessa a tela no envio.
"""
import pandas as pd
import streamlit as st

from src.calculo.periodo import limpar_nome_condominio, sugerir_periodo
from src.models.schema import AjusteManual, ConfiguracaoArrecadacao, DadosFormulario, TipoUnidade
from src.parsers.fracoes_parser import parse_fracoes


def _bloco_configuracao_arrecadacao(
    titulo: str, key_prefix: str, numero_unidades_sugerido: int = 1, permitir_definir_numero_unidades: bool = True
) -> tuple[ConfiguracaoArrecadacao, int]:
    """Pergunta em cascata (igual -> tipos/fração ideal/indexador) reaproveitada
    no rateio principal, no fundo de reserva e em cada "outra arrecadação".

    Retorna a configuração escolhida e o número de unidades resultante dela
    (para o rateio principal, esse número vira a referência para os blocos
    seguintes).
    """
    st.markdown(f"**{titulo}**")
    iguais = st.radio("As unidades são iguais?", ["Sim", "Não"], horizontal=True, key=f"{key_prefix}_iguais")

    if iguais == "Sim":
        col1, col2 = st.columns(2)
        if permitir_definir_numero_unidades:
            numero_unidades = int(
                col1.number_input(
                    "Número de unidades", min_value=1, value=numero_unidades_sugerido, step=1, key=f"{key_prefix}_num_unidades"
                )
            )
        else:
            numero_unidades = numero_unidades_sugerido
            col1.caption(f"{numero_unidades} unidade(s), conforme definido no rateio principal.")
        valor_unico = col2.number_input(
            "Valor por unidade (R$/mês)", min_value=0.0, value=0.0, step=10.0, key=f"{key_prefix}_valor_unico"
        )
        return ConfiguracaoArrecadacao(modo="igual", valor_unico=valor_unico), numero_unidades

    modo_label = st.radio(
        "O rateio é por:", ["Valor fixo por tipo", "Fração ideal", "Indexador"], horizontal=True, key=f"{key_prefix}_modo"
    )

    if modo_label == "Valor fixo por tipo":
        st.caption("Informe os tipos de unidade, a quantidade de cada tipo e o valor mensal por tipo.")
        tabela_inicial = pd.DataFrame({"tipo": ["Tipo 1"], "quantidade": [1], "valor": [0.0]})
        tabela = st.data_editor(
            tabela_inicial, num_rows="dynamic", use_container_width=True, key=f"{key_prefix}_tabela_tipos"
        )
        tipos = [
            TipoUnidade(nome=str(row["tipo"]), quantidade=int(row["quantidade"]), valor=float(row["valor"]))
            for _, row in tabela.iterrows()
            if pd.notna(row["tipo"]) and pd.notna(row["quantidade"]) and row["quantidade"] > 0
        ]
        numero_unidades = sum(t.quantidade for t in tipos)
        return ConfiguracaoArrecadacao(modo="tipos", tipos=tipos), numero_unidades

    # Fração ideal e indexador seguem exatamente a mesma lógica, só muda o rótulo.
    modo = "fracao_ideal" if modo_label == "Fração ideal" else "indexador"
    valor_total_mensal = st.number_input(
        "Valor total mensal a arrecadar (R$)", min_value=0.0, value=0.0, step=100.0, key=f"{key_prefix}_valor_total"
    )
    st.caption(
        f"Envie um arquivo (PDF ou Excel) com unidade/{modo_label.lower()}/proprietário, ou preencha a tabela abaixo manualmente."
    )
    arquivo = st.file_uploader(
        "Arquivo de frações (opcional)", type=["pdf", "xlsx", "xls"], key=f"{key_prefix}_upload_fracoes"
    )
    tabela_key = f"{key_prefix}_tabela_fracoes"
    if arquivo is not None and st.session_state.get(f"{key_prefix}_arquivo_processado") != arquivo.name:
        try:
            st.session_state[tabela_key] = parse_fracoes(arquivo)
            st.session_state[f"{key_prefix}_arquivo_processado"] = arquivo.name
        except Exception as erro:
            st.warning(f"Não foi possível ler o arquivo automaticamente ({erro})")

    n = max(numero_unidades_sugerido, 1)
    tabela_padrao = pd.DataFrame(
        {"unidade": [f"Unidade {i + 1}" for i in range(n)], "fracao": [1 / n] * n, "proprietario": [""] * n}
    )
    tabela_inicial = st.session_state.get(tabela_key, tabela_padrao)
    tabela = st.data_editor(tabela_inicial, num_rows="dynamic", use_container_width=True, key=f"{key_prefix}_editor_fracoes")
    numero_unidades = len(tabela)
    return ConfiguracaoArrecadacao(modo=modo, valor_total_mensal=valor_total_mensal, fracoes=tabela), numero_unidades


def renderizar_secao_formulario(dados_demonstrativo):
    st.header("2. Dados da previsão orçamentária")

    nome_padrao = limpar_nome_condominio(dados_demonstrativo.condominio) if dados_demonstrativo else ""
    periodo_padrao = sugerir_periodo(dados_demonstrativo.meses) if dados_demonstrativo else ""

    with st.container(border=True):
        st.subheader("Dados obrigatórios")

        col1, col2 = st.columns(2)
        nome_condominio = col1.text_input("Nome do condomínio", value=nome_padrao)
        periodo = col2.text_input("Período de avaliação", value=periodo_padrao)

        st.caption("O reajuste das despesas é calculado automaticamente a partir do Demonstrativo de Receitas e Despesas.")

        configuracao_rateio, numero_unidades = _bloco_configuracao_arrecadacao(
            "Rateio entre unidades", key_prefix="rateio", numero_unidades_sugerido=40
        )

        st.markdown("**Fundo de reserva**")
        possui_fundo_reserva_label = st.radio("O condomínio possui fundo de reserva?", ["Não", "Sim"], horizontal=True)
        possui_fundo_reserva = possui_fundo_reserva_label == "Sim"
        configuracao_fundo_reserva = None
        if possui_fundo_reserva:
            configuracao_fundo_reserva, _ = _bloco_configuracao_arrecadacao(
                "Como o fundo de reserva é dividido entre as unidades",
                key_prefix="fundo_reserva",
                numero_unidades_sugerido=numero_unidades,
                permitir_definir_numero_unidades=False,
            )

        st.markdown("**Outras arrecadações**")
        quer_outras_arrecadacoes = st.radio(
            "Haverá outras arrecadações (ex: rateio de água, rateio extra anual)?", ["Não", "Sim"], horizontal=True
        )
        outras_arrecadacoes = []
        if quer_outras_arrecadacoes == "Sim":
            quantidade_outras = st.number_input(
                "Quantas outras arrecadações deseja configurar?", min_value=1, value=1, step=1, key="qtd_outras_arrecadacoes"
            )
            for i in range(int(quantidade_outras)):
                with st.container(border=True):
                    nome_arrecadacao = st.text_input(
                        f"Nome da arrecadação #{i + 1}", value=f"Arrecadação {i + 1}", key=f"outra_arrecadacao_nome_{i}"
                    )
                    config_outra, _ = _bloco_configuracao_arrecadacao(
                        f"Como '{nome_arrecadacao}' é dividida entre as unidades",
                        key_prefix=f"outra_arrecadacao_{i}",
                        numero_unidades_sugerido=numero_unidades,
                        permitir_definir_numero_unidades=False,
                    )
                    outras_arrecadacoes.append((nome_arrecadacao, config_outra))

    with st.container(border=True):
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

    enviado = st.button("Confirmar dados", type="primary")

    if enviado:
        ajustes_manuais = []
        if ajustes_tabela is not None:
            for _, row in ajustes_tabela.iterrows():
                if pd.notna(row["reajuste_manual_percentual"]):
                    ajustes_manuais.append(
                        AjusteManual(subcategoria=row["subcategoria"], percentual_reajuste=float(row["reajuste_manual_percentual"]) / 100)
                    )

        formulario = DadosFormulario(
            nome_condominio=nome_condominio,
            periodo=periodo,
            numero_unidades=int(numero_unidades),
            configuracao_rateio=configuracao_rateio,
            possui_fundo_reserva=possui_fundo_reserva,
            configuracao_fundo_reserva=configuracao_fundo_reserva,
            outras_arrecadacoes=outras_arrecadacoes,
            observacoes=observacoes,
            ajustes_manuais=ajustes_manuais,
        )
        st.session_state["dados_formulario"] = formulario

    return st.session_state.get("dados_formulario")
