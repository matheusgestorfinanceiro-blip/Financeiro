"""Registro de gastos da obra/reforma e geração do relatório final para o proprietário."""
import datetime

import streamlit as st

from src.obra.armazenamento import (
    adicionar_gasto,
    carregar_dados_obra,
    carregar_gastos,
    remover_gasto,
    salvar_dados_obra,
)
from src.obra.calculo import fmt_data_br, percentual_orcamento, resumo_pagamento, total_geral
from src.obra.relatorio_pdf import gerar_pdf_obra
from src.obra.schema import (
    CATEGORIAS_GASTO,
    FASES_OBRA,
    FORMAS_PAGAMENTO,
    STATUS_OBRA,
    STATUS_PAGAMENTO,
    DadosObra,
    GastoObra,
)
from src.ui.estilo import aplicar_estilo_azul
from src.ui.formatacao import escapar_markdown, fmt_moeda, fmt_pct

st.set_page_config(page_title="Registro de Obra", layout="wide")
aplicar_estilo_azul()

st.title("Registro de Gastos da Obra")
st.caption(
    "Lance aqui todos os gastos da reforma para acompanhar o andamento e, ao final, "
    "gerar um relatório detalhado para apresentar ao proprietário do imóvel."
)

dados_obra = carregar_dados_obra() or DadosObra()

with st.expander("Dados da obra", expanded=not dados_obra.nome_obra):
    with st.form("form_dados_obra"):
        col1, col2 = st.columns(2)
        with col1:
            nome_obra = st.text_input("Nome da obra/reforma", value=dados_obra.nome_obra)
            proprietario = st.text_input("Proprietário do imóvel", value=dados_obra.proprietario)
            endereco = st.text_input("Endereço do imóvel", value=dados_obra.endereco)
        with col2:
            data_inicio = st.date_input(
                "Data de início",
                value=datetime.date.fromisoformat(dados_obra.data_inicio)
                if dados_obra.data_inicio
                else datetime.date.today(),
            )
            previsao_termino = st.date_input(
                "Previsão de término",
                value=datetime.date.fromisoformat(dados_obra.previsao_termino)
                if dados_obra.previsao_termino
                else datetime.date.today(),
            )
            orcamento_previsto = st.number_input(
                "Orçamento previsto (R$, opcional)", min_value=0.0, value=dados_obra.orcamento_previsto, step=100.0
            )
        status_obra = st.selectbox(
            "Status atual da obra",
            STATUS_OBRA,
            index=STATUS_OBRA.index(dados_obra.status_obra) if dados_obra.status_obra in STATUS_OBRA else 0,
        )
        observacoes_gerais = st.text_area(
            "Observações gerais sobre a obra (aparecem no relatório final)", value=dados_obra.observacoes_gerais
        )
        if st.form_submit_button("Salvar dados da obra"):
            dados_obra = DadosObra(
                nome_obra=nome_obra,
                proprietario=proprietario,
                endereco=endereco,
                data_inicio=data_inicio.isoformat(),
                previsao_termino=previsao_termino.isoformat(),
                orcamento_previsto=orcamento_previsto,
                status_obra=status_obra,
                observacoes_gerais=observacoes_gerais,
            )
            salvar_dados_obra(dados_obra)
            st.success("Dados da obra salvos.")
            st.rerun()

st.divider()

st.header("Lançar novo gasto")
with st.form("form_novo_gasto", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        data = st.date_input("Data do gasto", value=datetime.date.today())
        categoria = st.selectbox("Categoria", CATEGORIAS_GASTO)
        fase = st.selectbox("Fase da obra", FASES_OBRA)
    with col2:
        descricao = st.text_input("Descrição do gasto")
        fornecedor = st.text_input("Fornecedor/prestador (opcional)")
    with col3:
        valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
        forma_pagamento = st.selectbox("Forma de pagamento", FORMAS_PAGAMENTO)
        status_pagamento = st.selectbox("Status do pagamento", STATUS_PAGAMENTO)
    observacoes = st.text_area("Observações (opcional)")

    if st.form_submit_button("Adicionar gasto"):
        if not descricao or valor <= 0:
            st.error("Preencha ao menos a descrição e um valor maior que zero.")
        else:
            adicionar_gasto(
                GastoObra(
                    data=data.isoformat(),
                    categoria=categoria,
                    descricao=descricao,
                    valor=valor,
                    fornecedor=fornecedor,
                    forma_pagamento=forma_pagamento,
                    fase=fase,
                    status_pagamento=status_pagamento,
                    observacoes=observacoes,
                )
            )
            st.success("Gasto lançado com sucesso.")
            st.rerun()

st.divider()

st.header("Gastos lançados")
df_gastos = carregar_gastos()

if df_gastos.empty:
    st.info("Nenhum gasto lançado ainda.")
else:
    total = total_geral(df_gastos)
    pagamento = resumo_pagamento(df_gastos)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total gasto", fmt_moeda(total))
    col2.metric("Lançamentos", len(df_gastos))
    col3.metric("Já pago", fmt_moeda(pagamento["pago"]))
    col4.metric("Pendente", fmt_moeda(pagamento["pendente"]))

    if dados_obra.orcamento_previsto:
        pct = percentual_orcamento(total, dados_obra.orcamento_previsto)
        st.progress(
            min(pct, 1.0),
            text=escapar_markdown(f"{fmt_pct(pct)} do orçamento previsto ({fmt_moeda(dados_obra.orcamento_previsto)})"),
        )

    df_exibicao = df_gastos.copy()
    df_exibicao["data"] = df_exibicao["data"].apply(fmt_data_br)
    df_exibicao["valor"] = df_exibicao["valor"].apply(fmt_moeda)
    st.dataframe(
        df_exibicao[
            ["data", "categoria", "descricao", "fornecedor", "valor", "forma_pagamento", "fase", "status_pagamento"]
        ],
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Remover um lançamento"):
        opcoes = {
            f"#{row.id} — {fmt_data_br(row.data)} — {row.descricao} — {fmt_moeda(row.valor)}": row.id
            for row in df_gastos.itertuples()
        }
        escolha = st.selectbox("Selecione o lançamento", list(opcoes.keys()))
        if st.button("Remover lançamento selecionado"):
            remover_gasto(opcoes[escolha])
            st.success("Lançamento removido.")
            st.rerun()

st.divider()

st.header("Relatório final")
st.caption(
    "Gere o relatório em PDF com o resumo executivo, gráficos por categoria/fase, evolução no tempo, "
    "detalhamento de todos os lançamentos e considerações finais — pronto para apresentar ao proprietário."
)
if st.button("Gerar relatório em PDF"):
    if df_gastos.empty:
        st.warning("Lance ao menos um gasto antes de gerar o relatório.")
    else:
        pdf_bytes = gerar_pdf_obra(dados_obra, df_gastos)
        st.download_button(
            "Baixar relatório em PDF",
            data=pdf_bytes,
            file_name=f"relatorio_obra_{datetime.date.today().isoformat()}.pdf",
            mime="application/pdf",
        )
