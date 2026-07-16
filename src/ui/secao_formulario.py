"""Tela 2: dados obrigatórios + área de análise (dados opcionais).

Não usa st.form: os campos precisam reagir imediatamente uns aos outros
(ex: escolher "Sim" no fundo de reserva precisa abrir o campo seguinte na
hora), o que um st.form não permite, já que só reprocessa a tela no envio.
"""
import pandas as pd
import streamlit as st

from src.calculo.periodo import limpar_nome_condominio, sugerir_periodo
from src.calculo.previsao import _resolver_configuracao
from src.models.schema import RESPONSAVEL_TECNICO_NOME, AjusteManual, ConfiguracaoArrecadacao, DadosFormulario, TipoUnidade
from src.parsers.fracoes_parser import parse_fracoes
from src.ui.arquivos_temp import salvar_temp


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
            tabela_inicial,
            num_rows="dynamic",
            use_container_width=True,
            key=f"{key_prefix}_tabela_tipos",
            column_config={
                "valor": st.column_config.NumberColumn("Valor (R$/mês)", format="R$ %.2f"),
            },
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
            caminho = salvar_temp(arquivo)
            st.session_state[tabela_key] = parse_fracoes(caminho)
            st.session_state[f"{key_prefix}_arquivo_processado"] = arquivo.name
        except Exception as erro:
            st.warning(f"Não foi possível ler o arquivo automaticamente ({erro})")

    n = max(numero_unidades_sugerido, 1)
    tabela_padrao = pd.DataFrame(
        {"unidade": [f"Unidade {i + 1}" for i in range(n)], "fracao": [100 / n] * n, "proprietario": [""] * n}
    )
    tabela_inicial = st.session_state.get(tabela_key, tabela_padrao)
    tabela = st.data_editor(
        tabela_inicial,
        num_rows="dynamic",
        use_container_width=True,
        key=f"{key_prefix}_editor_fracoes",
        column_config={
            "fracao": st.column_config.NumberColumn("Fração (%)", format="%.3f%%"),
        },
    )
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

        st.markdown("**Isenção de unidades**")
        possui_isencao_label = st.radio(
            "Existe isenção de alguma unidade?", ["Não", "Sim"], horizontal=True, key="isencao_possui"
        )
        unidades_isentas = []
        if possui_isencao_label == "Sim":
            nomes_unidades = _resolver_configuracao(configuracao_rateio, numero_unidades)["unidade"].tolist()
            selecao_previa = [u for u in st.session_state.get("isencao_unidades", []) if u in nomes_unidades]
            unidades_selecionadas = st.multiselect(
                "Quais unidades são isentas da taxa condominial?", nomes_unidades, default=selecao_previa, key="isencao_unidades"
            )
            for unidade in unidades_selecionadas:
                percentual = st.number_input(
                    f"Percentual de isenção de {unidade} (%)", min_value=0.0, max_value=100.0, value=100.0, step=5.0,
                    key=f"isencao_pct_{unidade}",
                ) / 100
                unidades_isentas.append((unidade, percentual))
            st.caption(
                "A isenção é deduzida do rateio da(s) unidade(s) selecionada(s) antes de calcular a arrecadação "
                "prevista mensalmente e o percentual de reajuste."
            )

        st.markdown("**Desconto de pontualidade**")
        possui_desconto_pontualidade_label = st.radio(
            "Existe desconto de pontualidade no rateio?", ["Não", "Sim"], horizontal=True, key="desconto_pontualidade_possui"
        )
        possui_desconto_pontualidade = possui_desconto_pontualidade_label == "Sim"
        desconto_pontualidade_modo = "valor_fixo"
        desconto_pontualidade_valor = 0.0
        if possui_desconto_pontualidade:
            desconto_pontualidade_modo_label = st.radio(
                "O desconto é valor fixo ou percentual?", ["Valor fixo", "Percentual"], horizontal=True, key="desconto_pontualidade_modo"
            )
            if desconto_pontualidade_modo_label == "Valor fixo":
                desconto_pontualidade_modo = "valor_fixo"
                desconto_pontualidade_valor = st.number_input(
                    "Valor do desconto por unidade (R$/mês)", min_value=0.0, value=0.0, step=5.0, key="desconto_pontualidade_valor_fixo"
                )
            else:
                desconto_pontualidade_modo = "percentual"
                desconto_pontualidade_valor = st.number_input(
                    "Percentual do desconto (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key="desconto_pontualidade_valor_pct"
                ) / 100
            st.caption(
                "O desconto é deduzido do rateio de cada unidade antes de calcular a arrecadação prevista mensalmente "
                "(não afeta o fundo de reserva nem outras arrecadações)."
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
                        "Reajuste manual (%)", help="Deixe em branco para usar o reajuste automático.", format="%.2f%%"
                    )
                },
            )

    with st.container(border=True):
        st.subheader("Assinatura do relatório")
        emitido_pelo_responsavel_label = st.radio(
            f"Você é {RESPONSAVEL_TECNICO_NOME}, responsável técnico pelo sistema?",
            ["Sim", "Não"], horizontal=True, key="emitido_pelo_responsavel_tecnico",
        )
        emitido_pelo_responsavel_tecnico = emitido_pelo_responsavel_label == "Sim"
        nome_emissor = ""
        if not emitido_pelo_responsavel_tecnico:
            nome_emissor = st.text_input("Nome de quem está emitindo este relatório")
            st.caption(
                f"O relatório será assinado com o nome informado acima, com um rodapé creditando "
                f"{RESPONSAVEL_TECNICO_NOME} pela construção e formatação do sistema."
            )

    enviado = st.button("Confirmar dados", type="primary")

    if enviado:
        receitas_extraordinarias = st.session_state.get("receitas_extraordinarias_marcadas", [])
        despesas_extraordinarias = st.session_state.get("despesas_extraordinarias_marcadas", [])
        if not receitas_extraordinarias or not despesas_extraordinarias:
            st.error(
                "Marque pelo menos 1 receita e pelo menos 1 despesa como extraordinária (tela 1, tabelas "
                "'Ver e marcar receitas/despesas extraídas') antes de confirmar os dados."
            )
        elif not emitido_pelo_responsavel_tecnico and not nome_emissor.strip():
            st.error("Informe o nome de quem está emitindo este relatório antes de confirmar os dados.")
        else:
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
                unidades_isentas=unidades_isentas,
                receitas_extraordinarias=receitas_extraordinarias,
                despesas_extraordinarias=despesas_extraordinarias,
                possui_desconto_pontualidade=possui_desconto_pontualidade,
                desconto_pontualidade_modo=desconto_pontualidade_modo,
                desconto_pontualidade_valor=desconto_pontualidade_valor,
                possui_fundo_reserva=possui_fundo_reserva,
                configuracao_fundo_reserva=configuracao_fundo_reserva,
                outras_arrecadacoes=outras_arrecadacoes,
                observacoes=observacoes,
                ajustes_manuais=ajustes_manuais,
                emitido_pelo_responsavel_tecnico=emitido_pelo_responsavel_tecnico,
                nome_emissor=nome_emissor,
            )
            st.session_state["dados_formulario"] = formulario

    return st.session_state.get("dados_formulario")
