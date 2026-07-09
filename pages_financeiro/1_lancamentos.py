"""Cadastro de lançamentos — pensado para ser feito quase todo clicando."""
from datetime import date, timedelta

import streamlit as st

from src.pessoal.modelos import (
    CATEGORIAS_DESPESA,
    CATEGORIAS_RECEITA,
    REPETICAO_FIXA,
    REPETICAO_PARCELADA,
    REPETICAO_UNICA,
    TIPO_DESPESA,
    TIPO_RECEITA,
    USUARIOS_PADRAO,
    Lancamento,
)
from src.pessoal.repositorio import inserir
from src.pessoal.ui.estilo import aplicar_estilo
from src.pessoal.ui.sessao import obter_conexao, selecionar_usuario

OPCOES_PARCELAS = [2, 3, 4, 5, 6, 10, 12, 18, 24]

aplicar_estilo()
conexao = obter_conexao()
usuario_atual = selecionar_usuario()

st.title("📝 Novo lançamento")
st.caption("Clique nas opções abaixo. Só precisa digitar o valor (e a descrição, se quiser).")

# Cada lançamento salvo avança essa "versão", trocando as chaves de todos os
# campos do formulário — assim cada widget nasce de novo, com valor zerado,
# em vez de arriscar ficar com texto/número da vez anterior (comportamento
# conhecido do Streamlit ao só remover a chave do session_state).
st.session_state.setdefault("nl_versao", 0)
v = st.session_state.nl_versao


def campo(nome: str) -> str:
    return f"nl_{nome}_{v}"


st.session_state.setdefault(campo("tipo"), "Despesa 🔴")
st.session_state.setdefault(campo("repeticao"), "Única")
st.session_state.setdefault(campo("quando"), "Hoje")
st.session_state.setdefault(campo("usuario"), usuario_atual)

st.markdown("**O que você quer lançar?**")
tipo_escolhido = st.segmented_control(
    "Tipo", ["Receita 🔵", "Despesa 🔴"], key=campo("tipo"), label_visibility="collapsed"
)
tipo = TIPO_RECEITA if tipo_escolhido == "Receita 🔵" else TIPO_DESPESA

if st.session_state.get(campo("tipo_anterior")) != tipo:
    st.session_state.pop(campo("categoria"), None)
    st.session_state[campo("tipo_anterior")] = tipo

st.markdown("**Categoria**")
categorias = CATEGORIAS_RECEITA if tipo == TIPO_RECEITA else CATEGORIAS_DESPESA
categoria = st.pills("Categoria", categorias, key=campo("categoria"), label_visibility="collapsed")

col_valor, col_desc = st.columns(2)
with col_valor:
    valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f", key=campo("valor"))
with col_desc:
    descricao = st.text_input(
        "Descrição (opcional)",
        key=campo("descricao"),
        placeholder="Se deixar em branco, usamos a categoria",
    )

st.markdown("**Quando?**")
quando = st.segmented_control(
    "Quando", ["Hoje", "Amanhã", "Escolher data"], key=campo("quando"), label_visibility="collapsed"
)
if quando == "Amanhã":
    data_lancamento = date.today() + timedelta(days=1)
elif quando == "Escolher data":
    data_lancamento = st.date_input(
        "Data", value=date.today(), format="DD/MM/YYYY", key=campo("data_escolhida"), label_visibility="collapsed"
    )
else:
    data_lancamento = date.today()

st.markdown("**Isso se repete?**")
repeticao_escolhida = st.segmented_control(
    "Repetição",
    ["Única", "Fixa (todo mês)", "Parcelada"],
    key=campo("repeticao"),
    label_visibility="collapsed",
)
repeticao = {
    "Única": REPETICAO_UNICA,
    "Fixa (todo mês)": REPETICAO_FIXA,
    "Parcelada": REPETICAO_PARCELADA,
}[repeticao_escolhida]

parcela_total = None
if repeticao == REPETICAO_PARCELADA:
    st.markdown("**Em quantas parcelas?**")
    parcela_total = st.pills(
        "Parcelas", OPCOES_PARCELAS, key=campo("parcelas"), format_func=lambda n: f"{n}x", label_visibility="collapsed"
    )
    with st.expander("Outra quantidade de parcelas"):
        usar_quantidade_personalizada = st.checkbox("Usar outra quantidade", key=campo("usa_parcelas_custom"))
        if usar_quantidade_personalizada:
            parcela_total = st.number_input("Quantidade", min_value=2, step=1, value=2, key=campo("parcelas_custom"))

st.markdown("**Quem lançou?**")
usuario = st.segmented_control("Usuário", USUARIOS_PADRAO, key=campo("usuario"), label_visibility="collapsed")

with st.expander("+ Observação (opcional)"):
    observacao = st.text_input("Observação", key=campo("observacao"), label_visibility="collapsed")

st.divider()
pode_salvar = bool(categoria) and valor > 0 and bool(usuario)
if repeticao == REPETICAO_PARCELADA and not parcela_total:
    pode_salvar = False

if st.button("💾 Salvar lançamento", type="primary", disabled=not pode_salvar, use_container_width=True):
    novo = Lancamento(
        descricao=(descricao or "").strip() or categoria,
        categoria=categoria,
        tipo=tipo,
        valor=valor,
        data=data_lancamento,
        usuario=usuario,
        repeticao=repeticao,
        parcela_total=int(parcela_total) if parcela_total else None,
        observacao=(observacao or "").strip(),
    )
    inserir(conexao, novo)
    for chave in list(st.session_state.keys()):
        if chave.startswith("nl_") and chave.endswith(f"_{v}"):
            st.session_state.pop(chave, None)
    st.session_state["nl_versao"] = v + 1
    st.session_state["mensagem_sucesso"] = f"Lançamento \"{novo.descricao}\" salvo!"
    st.rerun()

if not categoria:
    st.caption("👆 Escolha uma categoria para poder salvar.")

if "mensagem_sucesso" in st.session_state:
    st.toast(st.session_state.pop("mensagem_sucesso"), icon="✅")

st.caption("Para ver, editar ou excluir lançamentos já cadastrados, acesse a aba **Histórico**.")
