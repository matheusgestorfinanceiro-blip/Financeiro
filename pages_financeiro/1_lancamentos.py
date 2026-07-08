"""Cadastro de lançamentos: únicos, fixos (recorrentes) ou parcelados."""
from datetime import date

import pandas as pd
import streamlit as st

from src.pessoal.armazenamento import encerrar_fixa, excluir, inserir, listar_todos
from src.pessoal.modelos import (
    CATEGORIAS_DESPESA,
    CATEGORIAS_RECEITA,
    REPETICAO_FIXA,
    REPETICAO_PARCELADA,
    REPETICAO_UNICA,
    TIPO_DESPESA,
    TIPO_RECEITA,
    Lancamento,
)
from src.pessoal.ui.estilo import aplicar_estilo, fmt_moeda
from src.pessoal.ui.sessao import obter_conexao, selecionar_usuario

aplicar_estilo()
conexao = obter_conexao()
usuario_atual = selecionar_usuario()

st.title("📝 Lançamentos")
st.caption("Cadastre receitas e despesas: únicas, fixas (repetem todo mês) ou parceladas.")

with st.form("novo_lancamento", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        descricao = st.text_input("Descrição *", placeholder="Ex: Aluguel, Salário, Mercado...")
        tipo = st.radio("Tipo *", [TIPO_RECEITA, TIPO_DESPESA], format_func=lambda t: "Receita 🔵" if t == TIPO_RECEITA else "Despesa 🔴", horizontal=True)
        categorias = CATEGORIAS_RECEITA if tipo == TIPO_RECEITA else CATEGORIAS_DESPESA
        categoria = st.selectbox("Categoria *", categorias)
        valor = st.number_input("Valor (R$) *", min_value=0.0, step=10.0, format="%.2f")
    with col2:
        data_lancamento = st.date_input("Data (1ª ocorrência) *", value=date.today())
        repeticao = st.selectbox(
            "Repetição *",
            [REPETICAO_UNICA, REPETICAO_FIXA, REPETICAO_PARCELADA],
            format_func=lambda r: {
                REPETICAO_UNICA: "Única (acontece só neste mês)",
                REPETICAO_FIXA: "Fixa (repete todo mês)",
                REPETICAO_PARCELADA: "Parcelada (repete por N meses)",
            }[r],
        )
        parcela_total = None
        if repeticao == REPETICAO_PARCELADA:
            parcela_total = st.number_input("Total de parcelas *", min_value=2, step=1, value=2)
        usuario = st.selectbox("Lançado por", [usuario_atual, *[u for u in ["Matheus", "Esposa"] if u != usuario_atual]])
        observacao = st.text_input("Observação (opcional)")

    enviado = st.form_submit_button("Salvar lançamento", type="primary")
    if enviado:
        if not descricao.strip():
            st.error("Preencha a descrição.")
        elif valor <= 0:
            st.error("O valor deve ser maior que zero.")
        else:
            novo = Lancamento(
                descricao=descricao.strip(),
                categoria=categoria,
                tipo=tipo,
                valor=valor,
                data=data_lancamento,
                usuario=usuario,
                repeticao=repeticao,
                parcela_total=int(parcela_total) if parcela_total else None,
                observacao=observacao.strip(),
            )
            inserir(conexao, novo)
            st.success("Lançamento salvo!")
            st.rerun()

st.divider()
st.subheader("Lançamentos cadastrados")

todos = listar_todos(conexao)
if not todos:
    st.info("Nenhum lançamento cadastrado ainda.")
    st.stop()

col_f1, col_f2 = st.columns(2)
with col_f1:
    filtro_tipo = st.multiselect("Filtrar por tipo", [TIPO_RECEITA, TIPO_DESPESA], default=[TIPO_RECEITA, TIPO_DESPESA])
with col_f2:
    filtro_usuario = st.multiselect("Filtrar por usuário", sorted({l.usuario for l in todos}), default=sorted({l.usuario for l in todos}))

filtrados = [l for l in todos if l.tipo in filtro_tipo and l.usuario in filtro_usuario]

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
