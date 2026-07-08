"""Dashboard do mês: totais, saldo e gráficos."""
from datetime import date

import streamlit as st

from src.pessoal.analise import resumir_mes
from src.pessoal.armazenamento import listar_todos
from src.pessoal.graficos import grafico_pizza_categoria
from src.pessoal.modelos import TIPO_DESPESA, TIPO_RECEITA
from src.pessoal.ui.estilo import aplicar_estilo, cartao, fmt_moeda
from src.pessoal.ui.sessao import obter_conexao, selecionar_usuario

aplicar_estilo()
conexao = obter_conexao()
selecionar_usuario()

st.title("📊 Dashboard do mês")

hoje = date.today()
col_ano, col_mes = st.columns(2)
ano = col_ano.number_input("Ano", min_value=2000, max_value=2100, value=hoje.year, step=1)
mes = col_mes.selectbox("Mês", list(range(1, 13)), index=hoje.month - 1, format_func=lambda m: f"{m:02d}")

todos = listar_todos(conexao)
resumo = resumir_mes(todos, ano, mes)

c1, c2, c3 = st.columns(3)
with c1:
    cartao("Receitas do mês", resumo.total_receitas, "receita")
with c2:
    cartao("Despesas do mês", resumo.total_despesas, "despesa")
with c3:
    cartao("Saldo do mês", resumo.saldo, "saldo")

st.divider()

if not resumo.ocorrencias:
    st.info("Nenhum lançamento neste mês.")
    st.stop()

col_g1, col_g2 = st.columns(2)
with col_g1:
    st.pyplot(grafico_pizza_categoria(resumo.por_categoria_despesa, "despesa"), use_container_width=True)
with col_g2:
    st.pyplot(grafico_pizza_categoria(resumo.por_categoria_receita, "receita"), use_container_width=True)

if resumo.por_usuario:
    st.subheader("Por pessoa")
    cols = st.columns(len(resumo.por_usuario))
    for col, (usuario, valores) in zip(cols, resumo.por_usuario.items()):
        with col:
            st.markdown(f"**{usuario}**")
            st.markdown(f":blue[Receitas: {fmt_moeda(valores[TIPO_RECEITA])}]")
            st.markdown(f":red[Despesas: {fmt_moeda(valores[TIPO_DESPESA])}]")

st.divider()
st.subheader("Lançamentos do mês")
for oc in resumo.ocorrencias:
    cor = "🔵" if oc.tipo == TIPO_RECEITA else "🔴"
    st.markdown(
        f"{cor} **{oc.descricao_completa}** — {oc.categoria} · {oc.usuario} · "
        f"{oc.data.strftime('%d/%m/%Y')} · {fmt_moeda(oc.valor)}"
    )
