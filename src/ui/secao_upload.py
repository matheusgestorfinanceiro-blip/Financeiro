"""Tela 1: upload dos 2 PDFs e preview dos dados extraídos."""
import tempfile

import streamlit as st

from src.parsers.demonstrativo_parser import parse_demonstrativo
from src.parsers.inadimplentes_parser import parse_inadimplentes
from src.ui.formatacao import escapar_markdown, fmt_moeda, fmt_pct


def _salvar_temp(arquivo_enviado) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(arquivo_enviado.getvalue())
        return tmp.name


def renderizar_secao_upload():
    st.header("1. Envie os 2 arquivos do condomínio")
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
            caminho = _salvar_temp(arquivo_inadimplentes)
            st.session_state["dados_inadimplencia"] = parse_inadimplentes(caminho)
            dados = st.session_state["dados_inadimplencia"]
            st.success(
                escapar_markdown(
                    f"Inadimplentes lido: {dados.condominio} — "
                    f"{dados.qtd_unidades_inadimplentes} unidades inadimplentes "
                    f"({fmt_pct(dados.percentual_inadimplencia)})"
                )
            )
            with st.expander("Ver unidades inadimplentes extraídas"):
                st.dataframe(dados.unidades, use_container_width=True, key="tabela_unidades_inadimplentes")
        except Exception as e:
            st.error(f"Não consegui ler o arquivo de inadimplentes: {e}")
            st.session_state.pop("dados_inadimplencia", None)

    if arquivo_demonstrativo is not None:
        try:
            caminho = _salvar_temp(arquivo_demonstrativo)
            st.session_state["dados_demonstrativo"] = parse_demonstrativo(caminho)
            dados = st.session_state["dados_demonstrativo"]
            st.success(
                escapar_markdown(
                    f"Demonstrativo lido: {dados.condominio} — "
                    f"receitas {fmt_moeda(dados.total_receitas)} / despesas {fmt_moeda(dados.total_despesas)}"
                )
            )
            with st.expander("Ver receitas extraídas"):
                st.dataframe(dados.df_receitas, use_container_width=True, key="tabela_receitas_extraidas")
            with st.expander("Ver despesas extraídas"):
                st.dataframe(dados.df_despesas, use_container_width=True, key="tabela_despesas_extraidas")
        except Exception as e:
            st.error(f"Não consegui ler o demonstrativo: {e}")
            st.session_state.pop("dados_demonstrativo", None)

    return (
        st.session_state.get("dados_inadimplencia"),
        st.session_state.get("dados_demonstrativo"),
    )
