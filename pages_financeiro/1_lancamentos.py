"""Cadastro de lançamentos — pensado para ser feito quase todo clicando."""
from datetime import date, timedelta

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
    USUARIOS_PADRAO,
    Lancamento,
)
from src.pessoal.ui.estilo import aplicar_estilo, fmt_moeda
from src.pessoal.ui.sessao import obter_conexao, selecionar_usuario

OPCOES_PARCELAS = [2, 3, 4, 5, 6, 10, 12, 18, 24]

aplicar_estilo()
conexao = obter_conexao()
usuario_atual = selecionar_usuario()

st.title("📝 Novo lançamento")
st.caption("Clique nas opções abaixo. Só precisa digitar o valor (e a descrição, se quiser).")

st.session_state.setdefault("nl_tipo", "Despesa 🔴")
st.session_state.setdefault("nl_repeticao", "Única")
st.session_state.setdefault("nl_quando", "Hoje")
st.session_state.setdefault("nl_usuario", usuario_atual)

st.markdown("**O que você quer lançar?**")
tipo_escolhido = st.segmented_control(
    "Tipo", ["Receita 🔵", "Despesa 🔴"], key="nl_tipo", label_visibility="collapsed"
)
tipo = TIPO_RECEITA if tipo_escolhido == "Receita 🔵" else TIPO_DESPESA

if st.session_state.get("nl_tipo_anterior") != tipo:
    st.session_state.pop("nl_categoria", None)
    st.session_state["nl_tipo_anterior"] = tipo

st.markdown("**Categoria**")
categorias = CATEGORIAS_RECEITA if tipo == TIPO_RECEITA else CATEGORIAS_DESPESA
categoria = st.pills("Categoria", categorias, key="nl_categoria", label_visibility="collapsed")

col_valor, col_desc = st.columns(2)
with col_valor:
    valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f", key="nl_valor")
with col_desc:
    descricao = st.text_input(
        "Descrição (opcional)",
        key="nl_descricao",
        placeholder="Se deixar em branco, usamos a categoria",
    )

st.markdown("**Quando?**")
quando = st.segmented_control(
    "Quando", ["Hoje", "Amanhã", "Escolher data"], key="nl_quando", label_visibility="collapsed"
)
if quando == "Amanhã":
    data_lancamento = date.today() + timedelta(days=1)
elif quando == "Escolher data":
    data_lancamento = st.date_input("Data", value=date.today(), format="DD/MM/YYYY", label_visibility="collapsed")
else:
    data_lancamento = date.today()

st.markdown("**Isso se repete?**")
repeticao_escolhida = st.segmented_control(
    "Repetição",
    ["Única", "Fixa (todo mês)", "Parcelada"],
    key="nl_repeticao",
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
        "Parcelas", OPCOES_PARCELAS, key="nl_parcelas", format_func=lambda n: f"{n}x", label_visibility="collapsed"
    )
    with st.expander("Outra quantidade de parcelas"):
        usar_quantidade_personalizada = st.checkbox("Usar outra quantidade", key="nl_usa_parcelas_custom")
        if usar_quantidade_personalizada:
            parcela_total = st.number_input("Quantidade", min_value=2, step=1, value=2, key="nl_parcelas_custom")

st.markdown("**Quem lançou?**")
usuario = st.segmented_control("Usuário", USUARIOS_PADRAO, key="nl_usuario", label_visibility="collapsed")

with st.expander("+ Observação (opcional)"):
    observacao = st.text_input("Observação", key="nl_observacao", label_visibility="collapsed")

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
    for chave in [
        "nl_categoria",
        "nl_valor",
        "nl_descricao",
        "nl_parcelas",
        "nl_usa_parcelas_custom",
        "nl_parcelas_custom",
        "nl_observacao",
    ]:
        st.session_state.pop(chave, None)
    st.session_state["mensagem_sucesso"] = f"Lançamento \"{novo.descricao}\" salvo!"
    st.rerun()

if not categoria:
    st.caption("👆 Escolha uma categoria para poder salvar.")

if "mensagem_sucesso" in st.session_state:
    st.toast(st.session_state.pop("mensagem_sucesso"), icon="✅")

st.divider()
st.subheader("Lançamentos cadastrados")

todos = listar_todos(conexao)
if not todos:
    st.info("Nenhum lançamento cadastrado ainda.")
    st.stop()

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
