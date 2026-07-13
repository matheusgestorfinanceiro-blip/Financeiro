"""Registro de Obra — controle simples dos gastos de uma reforma residencial
e geração do relatório final para o proprietário do imóvel.

Para rodar: streamlit run app_obra.py
"""
import datetime

import streamlit as st

from src.obra import repositorio
from src.obra.backup import gerar_backup_zip
from src.obra.calculo import fmt_data_br, percentual_orcamento, total_geral
from src.obra.relatorio_pdf import gerar_pdf_obra
from src.obra.schema import CATEGORIAS_GASTO, STATUS_OBRA, DadosObra, GastoObra
from src.ui.estilo import aplicar_estilo_azul
from src.ui.formatacao import escapar_markdown, fmt_moeda, fmt_pct

FORMATO_DATA = "DD/MM/YYYY"

st.set_page_config(page_title="Registro de Obra", layout="wide", page_icon="🏗️")
aplicar_estilo_azul()

st.title("🏗️ Registro de Obra")
st.caption("Anote os gastos da reforma no dia a dia e gere, quando quiser, um relatório para o proprietário.")

conexao = repositorio.obter_conexao()
if repositorio.usando_planilha():
    st.caption("💾 Dados salvos na Planilha do Google — permanentes, mesmo se o app reiniciar.")
if repositorio.usando_drive():
    st.caption("📎 Fotos e comprovantes salvos permanentemente no Google Drive.")

dados_obra = repositorio.carregar_dados_obra(conexao) or DadosObra()

with st.expander("Dados da obra (preencha uma vez)", expanded=not dados_obra.nome_obra):
    with st.form("form_dados_obra"):
        col1, col2 = st.columns(2)
        with col1:
            nome_obra = st.text_input("Nome da obra/reforma", value=dados_obra.nome_obra)
            proprietario = st.text_input("Proprietário do imóvel", value=dados_obra.proprietario)
            endereco = st.text_input("Endereço (opcional)", value=dados_obra.endereco)
        with col2:
            data_inicio = st.date_input(
                "Início",
                value=datetime.date.fromisoformat(dados_obra.data_inicio) if dados_obra.data_inicio else datetime.date.today(),
                format=FORMATO_DATA,
            )
            orcamento_previsto = st.number_input(
                "Orçamento previsto (R$, opcional)", min_value=0.0, value=dados_obra.orcamento_previsto, step=100.0
            )
            status_obra = st.selectbox(
                "Status atual",
                STATUS_OBRA,
                index=STATUS_OBRA.index(dados_obra.status_obra) if dados_obra.status_obra in STATUS_OBRA else 0,
            )
        observacoes_gerais = st.text_input("Observação geral (opcional, aparece no relatório)", value=dados_obra.observacoes_gerais)
        if st.form_submit_button("Salvar"):
            dados_obra = DadosObra(
                nome_obra=nome_obra,
                proprietario=proprietario,
                endereco=endereco,
                data_inicio=data_inicio.isoformat(),
                previsao_termino=dados_obra.previsao_termino,
                orcamento_previsto=orcamento_previsto,
                status_obra=status_obra,
                observacoes_gerais=observacoes_gerais,
            )
            repositorio.salvar_dados_obra(conexao, dados_obra)
            st.success("Dados salvos.")
            st.rerun()

st.divider()

st.header("Lançar gasto")
st.caption("Preencha os dados do gasto abaixo.")

with st.form("form_novo_gasto_manual", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        descricao_m = st.text_input("O que foi gasto?", placeholder="Ex: Cimento, Pedreiro, Torneira...", key="m_descricao")
    with col2:
        valor_m = st.number_input("Valor (R$)", min_value=0.0, step=10.0, key="m_valor")
    with col3:
        data_m = st.date_input("Data", value=datetime.date.today(), format=FORMATO_DATA, key="m_data")

    categoria_m = st.selectbox("Categoria", CATEGORIAS_GASTO, key="m_categoria")
    fornecedor_m = st.text_input("Fornecedor/prestador (opcional)", key="m_fornecedor")
    observacoes_m = st.text_input("Observação (opcional)", key="m_observacoes")

    if st.form_submit_button("Adicionar", type="primary"):
        if not descricao_m or valor_m <= 0:
            st.error("Preencha ao menos o que foi gasto e um valor maior que zero.")
        else:
            repositorio.adicionar_gasto(
                conexao,
                GastoObra(
                    data=data_m.isoformat(),
                    categoria=categoria_m,
                    descricao=descricao_m,
                    valor=valor_m,
                    fornecedor=fornecedor_m,
                    pago=True,
                    observacoes=observacoes_m,
                )
            )
            st.success("Gasto lançado!")
            st.rerun()

st.divider()

st.header("Gastos lançados")
df_gastos = repositorio.carregar_gastos(conexao)

if df_gastos.empty:
    st.info("Nenhum gasto lançado ainda.")
else:
    total = total_geral(df_gastos)

    col1, col2 = st.columns(2)
    col1.metric("Total gasto", fmt_moeda(total))
    col2.metric("Lançamentos", len(df_gastos))

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
        df_exibicao[["data", "descricao", "categoria", "valor", "fornecedor"]],
        use_container_width=True,
        hide_index=True,
    )

    opcoes_lancamentos = {
        f"{fmt_data_br(row.data)} — {row.descricao} — {fmt_moeda(row.valor)}": row.id
        for row in df_gastos.itertuples()
    }

    with st.expander("Editar um lançamento"):
        escolha_editar = st.selectbox("Selecione o lançamento", list(opcoes_lancamentos.keys()), key="escolha_editar")
        id_editar = opcoes_lancamentos[escolha_editar]
        gasto_atual = df_gastos[df_gastos["id"] == id_editar].iloc[0]

        with st.form("form_editar_gasto"):
            col1, col2, col3 = st.columns(3)
            with col1:
                descricao_e = st.text_input("O que foi gasto?", value=gasto_atual["descricao"], key="editar_descricao")
            with col2:
                valor_e = st.number_input(
                    "Valor (R$)", min_value=0.0, step=10.0, value=float(gasto_atual["valor"]), key="editar_valor"
                )
            with col3:
                data_e = st.date_input(
                    "Data", value=datetime.date.fromisoformat(gasto_atual["data"]), format=FORMATO_DATA, key="editar_data"
                )

            col4, col5 = st.columns(2)
            with col4:
                categoria_e = st.selectbox(
                    "Categoria",
                    CATEGORIAS_GASTO,
                    index=CATEGORIAS_GASTO.index(gasto_atual["categoria"]) if gasto_atual["categoria"] in CATEGORIAS_GASTO else 0,
                    key="editar_categoria",
                )
            with col5:
                fornecedor_e = st.text_input(
                    "Fornecedor/prestador", value=gasto_atual["fornecedor"], key="editar_fornecedor"
                )

            observacoes_e = st.text_input("Observação (opcional)", value=gasto_atual["observacoes"], key="editar_observacoes")

            if st.form_submit_button("Salvar alterações", type="primary"):
                if not descricao_e or valor_e <= 0:
                    st.error("Preencha ao menos o que foi gasto e um valor maior que zero.")
                else:
                    repositorio.atualizar_gasto(
                        conexao,
                        GastoObra(
                            id=id_editar,
                            data=data_e.isoformat(),
                            categoria=categoria_e,
                            descricao=descricao_e,
                            valor=valor_e,
                            fornecedor=fornecedor_e,
                            pago=True,
                            observacoes=observacoes_e,
                            anexo=gasto_atual["anexo"],
                        ),
                    )
                    st.success("Lançamento atualizado.")
                    st.rerun()

    with st.expander("Remover um lançamento"):
        escolha_remover = st.selectbox("Selecione o lançamento", list(opcoes_lancamentos.keys()), key="escolha_remover")
        if st.button("Remover"):
            repositorio.remover_gasto(conexao, opcoes_lancamentos[escolha_remover])
            st.success("Lançamento removido.")
            st.rerun()

st.divider()

st.header("Fotos da evolução da obra")
st.caption("Envie fotos ao longo da obra, com a data de quando foram tiradas — elas entram no relatório organizadas na ordem de execução.")

with st.form("form_nova_foto", clear_on_submit=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        foto_enviada = st.file_uploader("Foto", type=["png", "jpg", "jpeg", "webp"], key="upload_foto")
    with col2:
        data_foto = st.date_input("Data da foto", value=datetime.date.today(), format=FORMATO_DATA)
    legenda_foto = st.text_input("Legenda (opcional)", placeholder="Ex: Demolição do banheiro concluída")

    if st.form_submit_button("Adicionar foto", type="primary"):
        if foto_enviada is None:
            st.error("Selecione uma foto antes de adicionar.")
        else:
            repositorio.adicionar_foto(conexao, foto_enviada.getvalue(), foto_enviada.name, data_foto.isoformat(), legenda_foto)
            st.success("Foto adicionada!")
            st.rerun()

df_fotos = repositorio.carregar_fotos(conexao)
if not df_fotos.empty:
    st.caption(f"{len(df_fotos)} foto(s) cadastrada(s), em ordem cronológica:")
    colunas_galeria = st.columns(4)
    for i, foto in enumerate(df_fotos.itertuples()):
        with colunas_galeria[i % 4]:
            try:
                st.image(repositorio.obter_bytes_foto(foto.nome_arquivo), use_container_width=True)
            except Exception:
                st.caption("(não foi possível carregar a foto)")
            legenda = fmt_data_br(foto.data) + (f" — {foto.legenda}" if foto.legenda else "")
            st.caption(legenda)
            if st.button("Remover", key=f"remover_foto_{foto.id}"):
                repositorio.remover_foto(conexao, foto.id)
                st.rerun()

st.divider()

st.header("Notas fiscais e comprovantes")
st.caption("Envie as notas fiscais e comprovantes da obra (PDF ou foto) — elas entram no relatório em uma página própria, sem precisar estar ligadas a um lançamento específico.")

with st.form("form_nova_nota_fiscal", clear_on_submit=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        nota_enviada = st.file_uploader(
            "Nota fiscal ou comprovante", type=["pdf", "png", "jpg", "jpeg", "webp"], key="upload_nota_fiscal"
        )
    with col2:
        data_nota = st.date_input("Data", value=datetime.date.today(), format=FORMATO_DATA, key="data_nota_fiscal")
    legenda_nota = st.text_input("Legenda (opcional)", placeholder="Ex: Compra de cimento e areia", key="legenda_nota_fiscal")

    if st.form_submit_button("Adicionar nota fiscal", type="primary"):
        if nota_enviada is None:
            st.error("Selecione um arquivo antes de adicionar.")
        else:
            repositorio.adicionar_nota_fiscal(
                conexao, nota_enviada.getvalue(), nota_enviada.name, data_nota.isoformat(), legenda_nota
            )
            st.success("Nota fiscal adicionada!")
            st.rerun()

df_notas_fiscais = repositorio.carregar_notas_fiscais(conexao)
if not df_notas_fiscais.empty:
    st.caption(f"{len(df_notas_fiscais)} nota(s) fiscal(is)/comprovante(s) cadastrado(s):")
    colunas_notas = st.columns(4)
    for i, nota in enumerate(df_notas_fiscais.itertuples()):
        with colunas_notas[i % 4]:
            try:
                st.image(repositorio.obter_bytes_nota_fiscal(nota.nome_arquivo), use_container_width=True)
            except Exception:
                st.caption("(pré-visualização não disponível, ex: PDF)")
            legenda = fmt_data_br(nota.data) + (f" — {nota.legenda}" if nota.legenda else "")
            st.caption(legenda)
            if st.button("Remover", key=f"remover_nota_fiscal_{nota.id}"):
                repositorio.remover_nota_fiscal(conexao, nota.id)
                st.rerun()

st.divider()

if not repositorio.usando_drive():
    st.header("Backup de fotos e notas fiscais")
    st.caption(
        "As fotos e as notas fiscais ficam salvas neste servidor e podem ser apagadas quando "
        "o app reinicia. Baixe este backup de vez em quando para garantir uma cópia própria."
    )
    if df_fotos.empty and df_notas_fiscais.empty:
        st.caption("Nenhuma foto ou nota fiscal cadastrada ainda.")
    elif st.button("Gerar backup em ZIP"):
        zip_bytes = gerar_backup_zip(df_fotos, df_notas_fiscais)
        st.download_button(
            "Baixar backup (ZIP)",
            data=zip_bytes,
            file_name=f"backup_obra_fotos_notas_fiscais_{datetime.date.today().isoformat()}.zip",
            mime="application/zip",
        )

    st.divider()

st.header("Relatório final")
st.caption("Gera um PDF com o resumo, gráficos, todos os lançamentos, as fotos da evolução e as notas fiscais/comprovantes — pronto para mostrar ao proprietário.")

tipo_relatorio_label = st.radio(
    "Tipo de relatório",
    ["Parcial (andamento da obra)", "Final (obra concluída)"],
    horizontal=True,
)
tipo_relatorio = "final" if tipo_relatorio_label.startswith("Final") else "parcial"

if tipo_relatorio == "final" and df_fotos.empty:
    st.warning("O relatório final exige ao menos uma foto de evolução da obra. Adicione fotos acima ou gere um relatório parcial.")

if st.button("Gerar relatório em PDF", type="primary"):
    if df_gastos.empty:
        st.warning("Lance ao menos um gasto antes de gerar o relatório.")
    elif tipo_relatorio == "final" and df_fotos.empty:
        st.error("Não é possível gerar o relatório final sem fotos de evolução da obra.")
    else:
        pdf_bytes = gerar_pdf_obra(
            dados_obra,
            df_gastos,
            df_fotos,
            repositorio.obter_bytes_foto,
            tipo_relatorio,
            df_notas_fiscais,
            repositorio.obter_bytes_nota_fiscal,
        )
        st.download_button(
            "Baixar relatório em PDF",
            data=pdf_bytes,
            file_name=f"relatorio_obra_{datetime.date.today().isoformat()}.pdf",
            mime="application/pdf",
        )
