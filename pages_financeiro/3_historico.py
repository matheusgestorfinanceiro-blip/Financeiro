"""Histórico: evolução dos últimos meses e gestão de todos os lançamentos."""
from datetime import date

import streamlit as st

from src.pessoal.analise import historico_mensal
from src.pessoal.graficos import grafico_evolucao_mensal
from src.pessoal.modelos import REPETICAO_FIXA, REPETICAO_PARCELADA, REPETICAO_UNICA, TIPO_DESPESA, TIPO_RECEITA
from src.pessoal.repositorio import encerrar_fixa, excluir, listar_todos
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

st.divider()
st.subheader("Todos os lançamentos cadastrados")

col_f1, col_f2 = st.columns(2)
with col_f1:
    st.caption("Filtrar por tipo")
    filtro_tipo = st.pills(
        "Filtrar por tipo",
        [TIPO_RECEITA, TIPO_DESPESA],
        format_func=lambda t: "Receita 🔵" if t == TIPO_RECEITA else "Despesa 🔴",
        selection_mode="multi",
        default=[TIPO_RECEITA, TIPO_DESPESA],
        key="filtro_tipo",
        label_visibility="collapsed",
    )
with col_f2:
    usuarios_existentes = sorted({l.usuario for l in todos})
    st.caption("Filtrar por usuário")
    filtro_usuario = st.pills(
        "Filtrar por usuário",
        usuarios_existentes,
        selection_mode="multi",
        default=usuarios_existentes,
        key="filtro_usuario",
        label_visibility="collapsed",
    )

filtrados = [l for l in todos if l.tipo in (filtro_tipo or []) and l.usuario in (filtro_usuario or [])]

for lanc in filtrados:
    cor = "🔵" if lanc.tipo == TIPO_RECEITA else "🔴"
    rotulo_repeticao = {
        REPETICAO_UNICA: "única",
        REPETICAO_FIXA: "fixa" + (" (ativa)" if lanc.ativa and not lanc.data_fim else " (encerrada)" if lanc.data_fim else ""),
        REPETICAO_PARCELADA: f"parcelada em {lanc.parcela_total}x",
    }[lanc.repeticao]
    with st.container(border=True):
        c1, c2, c3 = st.columns([5, 2, 2])
        with c1:
            st.markdown(f"{cor} **{lanc.descricao}** — {lanc.categoria}")
            st.caption(f"{lanc.usuario} · {rotulo_repeticao} · a partir de {lanc.data.strftime('%d/%m/%Y')}" + (f" · obs: {lanc.observacao}" if lanc.observacao else ""))
        with c2:
            st.markdown(fmt_moeda(lanc.valor))
        with c3:
            botoes = st.columns(2)
            if lanc.repeticao == REPETICAO_FIXA and lanc.ativa and not lanc.data_fim:
                if botoes[0].button("Encerrar", key=f"encerrar_{lanc.id}", help="Para de repetir a partir do próximo mês"):
                    encerrar_fixa(conexao, lanc.id, date.today())
                    st.rerun()
            if botoes[1].button("Excluir", key=f"excluir_{lanc.id}"):
                excluir(conexao, lanc.id)
                st.rerun()
