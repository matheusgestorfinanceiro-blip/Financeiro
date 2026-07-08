"""Calendário: só as despesas a vencer, mês a mês."""
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

st.title("🗓️ Calendário de despesas")
st.caption("Só as despesas a vencer. Clique nas setas para ver outros meses.")

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
despesas_do_mes = [oc for oc in lancamentos_do_mes(todos, ano, mes) if oc.tipo != TIPO_RECEITA]
por_dia: dict[int, list] = {}
total_mes = 0.0
for oc in despesas_do_mes:
    por_dia.setdefault(oc.data.day, []).append(oc)
    total_mes += oc.valor

st.markdown(f"**Total de despesas no mês: :red[{fmt_moeda(total_mes)}]**")

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
            ocorrencias_dia = sorted(por_dia.get(dia, []), key=lambda o: -o.valor)
            total_dia = sum(o.valor for o in ocorrencias_dia)
            fundo = "background-color:#EFF6FF;border-radius:8px;" if eh_hoje else ""
            if ocorrencias_dia:
                fundo = "background-color:#FEF2F2;border-radius:8px;" if not eh_hoje else fundo

            linhas = ""
            for oc in ocorrencias_dia[:3]:
                texto = oc.descricao_completa
                if len(texto) > 14:
                    texto = texto[:13] + "…"
                linhas += (
                    f"<div style='font-size:0.72rem;color:#B91C1C;line-height:1.2;margin-top:2px;' "
                    f"title='{oc.descricao_completa} — {fmt_moeda(oc.valor)}'>{texto}</div>"
                )
            if len(ocorrencias_dia) > 3:
                linhas += f"<div style='font-size:0.68rem;color:#B91C1C;'>+{len(ocorrencias_dia) - 3}</div>"

            cabecalho_dia = f"<div style='font-weight:700'>{dia}</div>"
            total_html = (
                f"<div style='font-size:0.75rem;font-weight:700;color:#DC2626;margin-top:2px'>{fmt_moeda(total_dia)}</div>"
                if total_dia > 0
                else ""
            )
            st.markdown(
                f"<div style='{fundo}padding:5px;min-height:78px'>{cabecalho_dia}{total_html}{linhas}</div>",
                unsafe_allow_html=True,
            )

st.divider()
st.subheader("Próximas despesas a vencer")

meses_futuros = proximos_meses(hoje.year, hoje.month, 3)
futuras = []
for a, m in meses_futuros:
    futuras.extend(lancamentos_do_mes(todos, a, m))
despesas_futuras = sorted(
    (o for o in futuras if o.tipo != TIPO_RECEITA and o.data >= hoje), key=lambda o: o.data
)[:15]

if not despesas_futuras:
    st.caption("Nenhuma despesa futura cadastrada.")
for oc in despesas_futuras:
    st.markdown(f":red[{oc.data.strftime('%d/%m/%Y')} — {oc.descricao_completa} · {fmt_moeda(oc.valor)}]")
