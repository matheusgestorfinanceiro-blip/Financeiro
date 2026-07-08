"""Calendário: em que dia cada despesa vence e cada receita é esperada."""
from datetime import date

import streamlit as st

from src.pessoal.armazenamento import listar_todos
from src.pessoal.calendario import DIAS_SEMANA, NOMES_MESES, mes_anterior, mes_seguinte, semanas_do_mes
from src.pessoal.modelos import TIPO_RECEITA
from src.pessoal.projecao import lancamentos_do_mes, proximos_meses
from src.pessoal.ui.estilo import aplicar_estilo, fmt_moeda
from src.pessoal.ui.sessao import obter_conexao, selecionar_usuario

aplicar_estilo()
conexao = obter_conexao()
selecionar_usuario()

st.title("🗓️ Calendário")
st.caption("🔵 receita · 🔴 despesa. Clique nas setas para ver outros meses.")

hoje = date.today()
st.session_state.setdefault("cal_ano", hoje.year)
st.session_state.setdefault("cal_mes", hoje.month)

col_prev, col_titulo, col_hoje, col_next = st.columns([1, 3, 1, 1])
with col_prev:
    if st.button("◀", use_container_width=True):
        st.session_state.cal_ano, st.session_state.cal_mes = mes_anterior(
            st.session_state.cal_ano, st.session_state.cal_mes
        )
with col_next:
    if st.button("▶", use_container_width=True):
        st.session_state.cal_ano, st.session_state.cal_mes = mes_seguinte(
            st.session_state.cal_ano, st.session_state.cal_mes
        )
with col_hoje:
    if st.button("Hoje", use_container_width=True):
        st.session_state.cal_ano, st.session_state.cal_mes = hoje.year, hoje.month
with col_titulo:
    ano, mes = st.session_state.cal_ano, st.session_state.cal_mes
    st.markdown(
        f"<h3 style='text-align:center;margin:0'>{NOMES_MESES[mes]} de {ano}</h3>",
        unsafe_allow_html=True,
    )

todos = listar_todos(conexao)
ocorrencias = lancamentos_do_mes(todos, ano, mes)
por_dia: dict[int, list] = {}
for oc in ocorrencias:
    por_dia.setdefault(oc.data.day, []).append(oc)

cabecalho = st.columns(7)
for col, nome in zip(cabecalho, DIAS_SEMANA):
    col.markdown(f"<div style='text-align:center;font-weight:600;color:#6B7280'>{nome}</div>", unsafe_allow_html=True)

for semana in semanas_do_mes(ano, mes):
    colunas = st.columns(7)
    for coluna, dia in zip(colunas, semana):
        with coluna:
            if dia == 0:
                st.markdown("&nbsp;")
                continue
            eh_hoje = date(ano, mes, dia) == hoje
            fundo = "background-color:#EFF6FF;border-radius:8px;" if eh_hoje else ""
            linhas = ""
            for oc in sorted(por_dia.get(dia, []), key=lambda o: o.tipo):
                cor = "#1D4ED8" if oc.tipo == TIPO_RECEITA else "#DC2626"
                texto = oc.descricao_completa
                if len(texto) > 13:
                    texto = texto[:12] + "…"
                linhas += (
                    f"<div style='font-size:0.68rem;color:{cor};line-height:1.15;"
                    f"margin-top:2px;' title='{oc.descricao_completa} — {fmt_moeda(oc.valor)}'>"
                    f"● {texto}</div>"
                )
            st.markdown(
                f"<div style='{fundo}padding:4px;min-height:70px'>"
                f"<div style='font-weight:600'>{dia}</div>{linhas}</div>",
                unsafe_allow_html=True,
            )

st.divider()
st.subheader("Próximos vencimentos e receitas previstas")

meses_futuros = proximos_meses(hoje.year, hoje.month, 3)
futuras = []
for a, m in meses_futuros:
    futuras.extend(lancamentos_do_mes(todos, a, m))
futuras = [o for o in futuras if o.data >= hoje]

despesas_futuras = sorted((o for o in futuras if o.tipo != TIPO_RECEITA), key=lambda o: o.data)[:12]
receitas_futuras = sorted((o for o in futuras if o.tipo == TIPO_RECEITA), key=lambda o: o.data)[:12]

col_desp, col_rec = st.columns(2)
with col_desp:
    st.markdown("**🔴 Despesas a vencer**")
    if not despesas_futuras:
        st.caption("Nenhuma despesa futura cadastrada.")
    for oc in despesas_futuras:
        st.markdown(f"{oc.data.strftime('%d/%m/%Y')} — {oc.descricao_completa} · {fmt_moeda(oc.valor)}")
with col_rec:
    st.markdown("**🔵 Receitas previstas**")
    if not receitas_futuras:
        st.caption("Nenhuma receita futura cadastrada.")
    for oc in receitas_futuras:
        st.markdown(f"{oc.data.strftime('%d/%m/%Y')} — {oc.descricao_completa} · {fmt_moeda(oc.valor)}")
