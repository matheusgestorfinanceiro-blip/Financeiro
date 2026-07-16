"""Tela 1: upload dos 2 PDFs e preview dos dados extraídos."""
import streamlit as st

from src.parsers.demonstrativo_parser import parse_demonstrativo
from src.parsers.inadimplentes_parser import parse_inadimplentes
from src.ui.arquivos_temp import salvar_temp
from src.ui.formatacao import escapar_markdown, fmt_moeda, fmt_pct


def renderizar_secao_upload():
    st.header("📤 1. Envie os 2 arquivos do condomínio")
    st.caption(
        "Envie o relatório de **Inadimplentes** e o **Demonstrativo de Receitas e Despesas** "
        "(mesmo formato gerado pelo sistema de gestão condominial)."
    )

    col1, col2 = st.columns(2)
    with col1:
        arquivo_inadimplentes = st.file_uploader("Relatório de Inadimplentes (PDF)", type="pdf", key="upload_inadimplentes")
    with col2:
        arquivo_demonstrativo = st.file_uploader(
            "Demonstrativo de Receitas e Despesas (PDF)", type="pdf", key="upload_demonstrativo"
        )

    if arquivo_inadimplentes is not None:
        try:
            caminho = salvar_temp(arquivo_inadimplentes)
            st.session_state["dados_inadimplencia"] = parse_inadimplentes(caminho)
            dados = st.session_state["dados_inadimplencia"]
            st.success(
                escapar_markdown(
                    f"Inadimplentes lido: {dados.condominio} — "
                    f"{dados.qtd_unidades_inadimplentes} unidades inadimplentes "
                    f"({fmt_pct(dados.percentual_inadimplencia)})"
                ),
                icon="✅",
            )
            usar_percentual_pdf = st.radio(
                f"Usar o percentual de inadimplência informado no PDF ({fmt_pct(dados.percentual_inadimplencia)})?",
                ["Sim", "Não"], horizontal=True, key="inadimplencia_usar_percentual_pdf",
            )
            if usar_percentual_pdf == "Não":
                percentual_manual = st.number_input(
                    "Qual percentual de inadimplência deve ser considerado (%)?",
                    min_value=0.0, max_value=100.0,
                    value=round(dados.percentual_inadimplencia * 100, 2), step=0.5,
                    key="inadimplencia_percentual_manual",
                )
                dados.percentual_inadimplencia = percentual_manual / 100
                st.caption(
                    f"Será considerado {fmt_pct(dados.percentual_inadimplencia)} de inadimplência em todo "
                    "o formulário e no relatório, no lugar do percentual lido do PDF."
                )
            with st.expander("🔎 Ver unidades inadimplentes extraídas"):
                st.dataframe(dados.unidades, use_container_width=True, key="tabela_unidades_inadimplentes")
        except Exception as e:
            st.error(f"Não consegui ler o arquivo de inadimplentes: {e}", icon="⚠️")
            st.session_state.pop("dados_inadimplencia", None)

    if arquivo_demonstrativo is not None:
        try:
            caminho = salvar_temp(arquivo_demonstrativo)
            st.session_state["dados_demonstrativo"] = parse_demonstrativo(caminho)
            dados = st.session_state["dados_demonstrativo"]
            st.success(
                escapar_markdown(
                    f"Demonstrativo lido: {dados.condominio} — "
                    f"receitas {fmt_moeda(dados.total_receitas)} / despesas {fmt_moeda(dados.total_despesas)}"
                ),
                icon="✅",
            )
            st.caption(
                "Marque abaixo as receitas e despesas que são **extraordinárias** (eventuais, sem "
                "recorrência mensal — ex: juros, obras pontuais, receitas ou despesas que não se repetem "
                "todo mês). As linhas não marcadas são tratadas como **ordinárias** (recorrentes). Essa "
                "classificação define o que entra no cálculo do reajuste automático e é usada nas páginas "
                "de Arrecadações, Despesas e Reajuste do relatório final. É necessário marcar pelo menos "
                "1 receita e pelo menos 1 despesa como extraordinária para gerar o relatório."
            )
            with st.expander("💵 Ver e marcar receitas extraídas", expanded=True):
                df_receitas_editavel = dados.df_receitas.copy()
                df_receitas_editavel["extraordinaria"] = False
                colunas_travadas = [c for c in df_receitas_editavel.columns if c != "extraordinaria"]
                df_receitas_editado = st.data_editor(
                    df_receitas_editavel,
                    use_container_width=True,
                    hide_index=True,
                    key="tabela_receitas_extraidas",
                    disabled=colunas_travadas,
                    column_config={
                        "extraordinaria": st.column_config.CheckboxColumn("Extraordinária?", default=False),
                    },
                )
                st.session_state["receitas_extraordinarias_marcadas"] = (
                    df_receitas_editado[df_receitas_editado["extraordinaria"]]["categoria"].tolist()
                )
            with st.expander("🧾 Ver e marcar despesas extraídas", expanded=True):
                df_despesas_editavel = dados.df_despesas.copy()
                df_despesas_editavel["extraordinaria"] = False
                colunas_travadas = [c for c in df_despesas_editavel.columns if c != "extraordinaria"]
                df_despesas_editado = st.data_editor(
                    df_despesas_editavel,
                    use_container_width=True,
                    hide_index=True,
                    key="tabela_despesas_extraidas",
                    disabled=colunas_travadas,
                    column_config={
                        "categoria_pai": None,
                        "extraordinaria": st.column_config.CheckboxColumn("Extraordinária?", default=False),
                    },
                )
                st.session_state["despesas_extraordinarias_marcadas"] = (
                    df_despesas_editado[df_despesas_editado["extraordinaria"]]["subcategoria"].tolist()
                )
        except Exception as e:
            st.error(f"Não consegui ler o demonstrativo: {e}", icon="⚠️")
            st.session_state.pop("dados_demonstrativo", None)

    return (
        st.session_state.get("dados_inadimplencia"),
        st.session_state.get("dados_demonstrativo"),
    )
