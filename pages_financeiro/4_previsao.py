"""Previsão futura: projeta gastos fixos, parcelas em andamento e receitas fixas."""
from datetime import date

import streamlit as st

from src.pessoal.analise import previsao_futura
from src.pessoal.graficos import grafico_evolucao_mensal
from src.pessoal.modelos import REPETICAO_PARCELADA
from src.pessoal.repositorio import listar_todos
from src.pessoal.ui.estilo import aplicar_estilo, fmt_moeda
from src.pessoal.ui.sessao import obter_conexao, selecionar_usuario

aplicar_estilo()
conexao = obter_conexao()
selecionar_usuario()

st.title("🔮 Previsão futura")
st.caption(
    "Projeta os próximos meses considerando receitas e despesas fixas já cadastradas "
    "e parcelas em andamento. Gastos variáveis ainda não lançados não entram na conta."
)

hoje = date.today()
quantidade = st.slider("Quantos meses à frente?", min_value=1, max_value=24, value=6)

todos = listar_todos(conexao)
if not todos:
    st.info("Nenhum lançamento cadastrado ainda.")
    st.stop()

resumos = previsao_futura(todos, hoje.year, hoje.month, quantidade)

st.pyplot(grafico_evolucao_mensal(resumos), use_container_width=True)

st.divider()
st.subheader("Detalhe mês a mês")
for r in resumos:
    cor_saldo = "green" if r.saldo >= 0 else "red"
    with st.expander(f"{r.mes:02d}/{r.ano} — Saldo previsto: {fmt_moeda(r.saldo)}"):
        st.markdown(
            f":blue[Receitas previstas: {fmt_moeda(r.total_receitas)}] · "
            f":red[Despesas previstas: {fmt_moeda(r.total_despesas)}] · "
            f":{cor_saldo}[Saldo: {fmt_moeda(r.saldo)}]"
        )
        for oc in r.ocorrencias:
            cor = "🔵" if oc.tipo == "receita" else "🔴"
            st.markdown(f"{cor} {oc.descricao_completa} — {oc.categoria} · {fmt_moeda(oc.valor)}")

st.divider()
st.subheader("Parcelas em andamento")
todos_parcelados = [l for l in todos if l.repeticao == REPETICAO_PARCELADA]
if not todos_parcelados:
    st.caption("Nenhuma compra parcelada cadastrada.")
for lanc in todos_parcelados:
    meses_pagas = (hoje.year - lanc.data.year) * 12 + (hoje.month - lanc.data.month) + 1
    restantes = max((lanc.parcela_total or 0) - meses_pagas, 0)
    st.markdown(
        f"🔴 **{lanc.descricao}** — {fmt_moeda(lanc.valor)}/mês · "
        f"faltam **{restantes}** de {lanc.parcela_total} parcelas"
    )
