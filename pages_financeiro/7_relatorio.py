"""Relatório filtrável: período, pessoa, categoria e tipo — com gráficos e PDF."""
from datetime import date, timedelta

import streamlit as st

from src.pessoal.graficos import grafico_evolucao_mensal, grafico_pizza_categoria, grafico_por_pessoa
from src.pessoal.modelos import CATEGORIAS_DESPESA, CATEGORIAS_RECEITA, TIPO_DESPESA, TIPO_RECEITA, USUARIOS_PADRAO
from src.pessoal.relatorio import evolucao_mensal, ocorrencias_no_periodo, resumir_periodo
from src.pessoal.relatorio_pdf import gerar_pdf_relatorio
from src.pessoal.repositorio import listar_todos
from src.pessoal.ui.estilo import aplicar_estilo, cartao, fmt_moeda
from src.pessoal.ui.sessao import obter_conexao, selecionar_usuario

aplicar_estilo()
conexao = obter_conexao()
selecionar_usuario()

st.title("🧾 Relatório")
st.caption("Escolha o período e, se quiser, filtre por pessoa, categoria e tipo. O relatório pode ser baixado em PDF.")

todos = listar_todos(conexao)
if not todos:
    st.info("Nenhum lançamento cadastrado ainda.")
    st.stop()

hoje = date.today()

st.markdown("**Período**")
st.session_state.setdefault("rel_periodo", "Este mês")
periodo_escolhido = st.segmented_control(
    "Período",
    ["Este mês", "Mês passado", "Este ano", "Tudo", "Personalizado"],
    key="rel_periodo",
    label_visibility="collapsed",
)

data_mais_antiga = min((l.data for l in todos), default=hoje)
if periodo_escolhido == "Este mês":
    data_inicio, data_fim = hoje.replace(day=1), hoje
elif periodo_escolhido == "Mês passado":
    fim_mes_passado = hoje.replace(day=1) - timedelta(days=1)
    data_inicio, data_fim = fim_mes_passado.replace(day=1), fim_mes_passado
elif periodo_escolhido == "Este ano":
    data_inicio, data_fim = hoje.replace(month=1, day=1), hoje
elif periodo_escolhido == "Tudo":
    data_inicio, data_fim = data_mais_antiga, hoje
else:
    col_de, col_ate = st.columns(2)
    with col_de:
        data_inicio = st.date_input("De", value=data_mais_antiga, format="DD/MM/YYYY")
    with col_ate:
        data_fim = st.date_input("Até", value=hoje, format="DD/MM/YYYY")

if data_inicio > data_fim:
    st.error("A data \"De\" não pode ser depois da data \"Até\".")
    st.stop()

st.markdown("**Pessoa** (deixe tudo desmarcado para incluir todas)")
usuarios_existentes = sorted({l.usuario for l in todos} | set(USUARIOS_PADRAO))
filtro_pessoas = st.pills(
    "Pessoa", usuarios_existentes, selection_mode="multi", key="rel_pessoas", label_visibility="collapsed"
)

st.markdown("**Tipo** (deixe tudo desmarcado para incluir os dois)")
filtro_tipos = st.pills(
    "Tipo",
    [TIPO_RECEITA, TIPO_DESPESA],
    format_func=lambda t: "Receita 🔵" if t == TIPO_RECEITA else "Despesa 🔴",
    selection_mode="multi",
    key="rel_tipos",
    label_visibility="collapsed",
)

st.markdown("**Categoria** (deixe tudo desmarcado para incluir todas)")
todas_categorias = sorted(set(CATEGORIAS_RECEITA) | set(CATEGORIAS_DESPESA))
filtro_categorias = st.pills(
    "Categoria", todas_categorias, selection_mode="multi", key="rel_categorias", label_visibility="collapsed"
)

ocorrencias = ocorrencias_no_periodo(
    todos,
    data_inicio,
    data_fim,
    usuarios=set(filtro_pessoas) if filtro_pessoas else None,
    categorias=set(filtro_categorias) if filtro_categorias else None,
    tipos=set(filtro_tipos) if filtro_tipos else None,
)
resumo = resumir_periodo(ocorrencias, data_inicio, data_fim)

st.divider()

if not ocorrencias:
    st.warning("Nenhum lançamento encontrado com esses filtros.")
    st.stop()

c1, c2, c3 = st.columns(3)
with c1:
    cartao("Receitas no período", resumo.total_receitas, "receita")
with c2:
    cartao("Despesas no período", resumo.total_despesas, "despesa")
with c3:
    cartao("Saldo do período", resumo.saldo, "saldo")
st.caption(f"{len(ocorrencias)} lançamento(s) no período de {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}.")

col_g1, col_g2 = st.columns(2)
with col_g1:
    st.pyplot(grafico_pizza_categoria(resumo.por_categoria_despesa, "despesa"), use_container_width=True)
with col_g2:
    st.pyplot(grafico_pizza_categoria(resumo.por_categoria_receita, "receita"), use_container_width=True)

if len(resumo.por_usuario) >= 2:
    st.pyplot(grafico_por_pessoa(resumo.por_usuario), use_container_width=True)

resumos_mensais = evolucao_mensal(ocorrencias)
if len(resumos_mensais) >= 2:
    st.subheader("Evolução no período")
    st.pyplot(grafico_evolucao_mensal(resumos_mensais), use_container_width=True)

st.divider()

filtros_legiveis = {
    "pessoas": ", ".join(filtro_pessoas) if filtro_pessoas else None,
    "categorias": ", ".join(filtro_categorias) if filtro_categorias else None,
    "tipos": ", ".join("Receita" if t == TIPO_RECEITA else "Despesa" for t in filtro_tipos) if filtro_tipos else None,
}
pdf_bytes = gerar_pdf_relatorio(resumo, filtros_legiveis)
st.download_button(
    "📄 Baixar relatório em PDF",
    pdf_bytes,
    file_name=f"relatorio_financeiro_{data_inicio.isoformat()}_a_{data_fim.isoformat()}.pdf",
    mime="application/pdf",
    type="primary",
    use_container_width=True,
)

with st.expander("Ver lançamentos do período"):
    for oc in ocorrencias:
        cor = "🔵" if oc.tipo == TIPO_RECEITA else "🔴"
        st.markdown(
            f"{cor} {oc.data.strftime('%d/%m/%Y')} — **{oc.descricao_completa}** — {oc.categoria} · "
            f"{oc.usuario} · {fmt_moeda(oc.valor)}"
        )
