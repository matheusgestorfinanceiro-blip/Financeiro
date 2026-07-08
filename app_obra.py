"""Registro de Obra — controle simples dos gastos de uma reforma residencial
e geração do relatório final para o proprietário do imóvel.

Para rodar: streamlit run app_obra.py
"""
import datetime

import streamlit as st

from src.obra.armazenamento import (
    adicionar_gasto,
    carregar_dados_obra,
    carregar_gastos,
    remover_gasto,
    salvar_dados_obra,
)
from src.obra.calculo import fmt_data_br, percentual_orcamento, resumo_pagamento, total_geral
from src.obra.relatorio_pdf import gerar_pdf_obra
from src.obra.schema import CATEGORIAS_GASTO, STATUS_OBRA, DadosObra, GastoObra
from src.ui.estilo import aplicar_estilo_azul
from src.ui.formatacao import escapar_markdown, fmt_moeda, fmt_pct

FORMATO_DATA = "DD/MM/YYYY"

st.set_page_config(page_title="Registro de Obra", layout="wide", page_icon="🏗️")
aplicar_estilo_azul()

st.title("🏗️ Registro de Obra")
st.caption("Anote os gastos da reforma no dia a dia e gere, quando quiser, um relatório para o proprietário.")

dados_obra = carregar_dados_obra() or DadosObra()

with st.expander("Dados da obra (preencha uma vez)", expanded=not dados_obra.nome_obra):
    with st.form("form_dados_obra"):
        col1, col2 = st.columns(2)
        with col1:
            nome_obra = st.text_input("Nome da obra/reforma", value=dados_obra.nome_obra)
            proprietario = st.text_input("Proprietário do imóvel", value=dados_obra.proprietario)
            endereco = st.text_input("Endereço (opcional)", value=dados_obra.endereco)
        with col2:
            data_inicio = st.date_input(
                "Início",
                value=datetime.date.fromisoformat(dados_obra.data_inicio) if dados_obra.data_inicio else datetime.date.today(),
                format=FORMATO_DATA,
            )
            orcamento_previsto = st.number_input(
                "Orçamento previsto (R$, opcional)", min_value=0.0, value=dados_obra.orcamento_previsto, step=100.0
            )
            status_obra = st.selectbox(
                "Status atual",
                STATUS_OBRA,
                index=STATUS_OBRA.index(dados_obra.status_obra) if dados_obra.status_obra in STATUS_OBRA else 0,
            )
        observacoes_gerais = st.text_input("Observação geral (opcional, aparece no relatório)", value=dados_obra.observacoes_gerais)
        if st.form_submit_button("Salvar"):
            dados_obra = DadosObra(
                nome_obra=nome_obra,
                proprietario=proprietario,
                endereco=endereco,
                data_inicio=data_inicio.isoformat(),
                previsao_termino=dados_obra.previsao_termino,
                orcamento_previsto=orcamento_previsto,
                status_obra=status_obra,
                observacoes_gerais=observacoes_gerais,
            )
            salvar_dados_obra(dados_obra)
            st.success("Dados salvos.")
            st.rerun()

st.divider()

st.header("Lançar gasto")
with st.form("form_novo_gasto", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        descricao = st.text_input("O que foi gasto?", placeholder="Ex: Cimento, Pedreiro, Torneira...")
    with col2:
        valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
    with col3:
        data = st.date_input("Data", value=datetime.date.today(), format=FORMATO_DATA)

    col4, col5 = st.columns(2)
    with col4:
        categoria = st.selectbox("Categoria", CATEGORIAS_GASTO)
    with col5:
        pago = st.checkbox("Já foi pago", value=True)

    with st.expander("Mais detalhes (opcional)"):
        fornecedor = st.text_input("Fornecedor/prestador")
        observacoes = st.text_input("Observação")

    if st.form_submit_button("Adicionar", type="primary"):
        if not descricao or valor <= 0:
            st.error("Preencha ao menos o que foi gasto e um valor maior que zero.")
        else:
            adicionar_gasto(
                GastoObra(
                    data=data.isoformat(),
                    categoria=categoria,
                    descricao=descricao,
                    valor=valor,
                    fornecedor=fornecedor,
                    pago=pago,
                    observacoes=observacoes,
                )
            )
            st.success("Gasto lançado!")
            st.rerun()

st.divider()

st.header("Gastos lançados")
df_gastos = carregar_gastos()

if df_gastos.empty:
    st.info("Nenhum gasto lançado ainda.")
else:
    total = total_geral(df_gastos)
    pagamento = resumo_pagamento(df_gastos)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total gasto", fmt_moeda(total))
    col2.metric("Lançamentos", len(df_gastos))
    col3.metric("Já pago", fmt_moeda(pagamento["pago"]))
    col4.metric("Pendente", fmt_moeda(pagamento["pendente"]))

    if dados_obra.orcamento_previsto:
        pct = percentual_orcamento(total, dados_obra.orcamento_previsto)
        st.progress(
            min(pct, 1.0),
            text=escapar_markdown(f"{fmt_pct(pct)} do orçamento previsto ({fmt_moeda(dados_obra.orcamento_previsto)})"),
        )

    df_exibicao = df_gastos.copy()
    df_exibicao["data"] = df_exibicao["data"].apply(fmt_data_br)
    df_exibicao["valor"] = df_exibicao["valor"].apply(fmt_moeda)
    df_exibicao["pago"] = df_exibicao["pago"].map({True: "Pago", False: "Pendente"})
    st.dataframe(
        df_exibicao[["data", "descricao", "categoria", "valor", "pago", "fornecedor"]],
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Remover um lançamento"):
        opcoes = {
            f"{fmt_data_br(row.data)} — {row.descricao} — {fmt_moeda(row.valor)}": row.id
            for row in df_gastos.itertuples()
        }
        escolha = st.selectbox("Selecione o lançamento", list(opcoes.keys()))
        if st.button("Remover"):
            remover_gasto(opcoes[escolha])
            st.success("Lançamento removido.")
            st.rerun()

st.divider()

st.header("Relatório final")
st.caption("Gera um PDF com o resumo, gráficos e todos os lançamentos — pronto para mostrar ao proprietário.")
if st.button("Gerar relatório em PDF", type="primary"):
    if df_gastos.empty:
        st.warning("Lance ao menos um gasto antes de gerar o relatório.")
    else:
        pdf_bytes = gerar_pdf_obra(dados_obra, df_gastos)
        st.download_button(
            "Baixar relatório em PDF",
            data=pdf_bytes,
            file_name=f"relatorio_obra_{datetime.date.today().isoformat()}.pdf",
            mime="application/pdf",
        )
