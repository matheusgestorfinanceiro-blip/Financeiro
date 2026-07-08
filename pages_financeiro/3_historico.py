"""Histórico dos últimos meses: evolução de receitas, despesas e saldo."""
from datetime import date

import streamlit as st

from src.pessoal.analise import historico_mensal
from src.pessoal.armazenamento import listar_todos
from src.pessoal.graficos import grafico_evolucao_mensal
from src.pessoal.ui.estilo import aplicar_estilo, fmt_moeda
from src.pessoal.ui.sessao import obter_conexao, selecionar_usuario

aplicar_estilo()
conexao = obter_conexao()
selecionar_usuario()

st.title("📅 Histórico")
st.caption("Evolução dos últimos meses, comparando com o mês atual.")

hoje = date.today()
quantidade = st.slider("Quantos meses para trás?", min_value=3, max_value=24, value=6)

todos = listar_todos(conexao)
if not todos:
    st.info("Nenhum lançamento cadastrado ainda.")
    st.stop()

resumos = historico_mensal(todos, hoje.year, hoje.month, quantidade)

st.pyplot(grafico_evolucao_mensal(resumos), use_container_width=True)

st.divider()
st.subheader("Tabela mensal")
for r in resumos:
    cor_saldo = "green" if r.saldo >= 0 else "red"
    st.markdown(
        f"**{r.mes:02d}/{r.ano}** — :blue[Receitas: {fmt_moeda(r.total_receitas)}] · "
        f":red[Despesas: {fmt_moeda(r.total_despesas)}] · "
        f":{cor_saldo}[Saldo: {fmt_moeda(r.saldo)}]"
    )
