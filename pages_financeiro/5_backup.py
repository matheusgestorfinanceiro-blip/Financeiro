"""Backup: exporta e importa todos os lançamentos em CSV."""
from datetime import date

import pandas as pd
import streamlit as st

from src.pessoal import repositorio
from src.pessoal.modelos import Lancamento
from src.pessoal.repositorio import inserir, listar_todos
from src.pessoal.ui.estilo import aplicar_estilo
from src.pessoal.ui.sessao import obter_conexao, selecionar_usuario

aplicar_estilo()
conexao = obter_conexao()
selecionar_usuario()

st.title("💾 Backup")
if repositorio.usando_planilha():
    st.success(
        "Os lançamentos estão sendo salvos numa Planilha do Google — eles não são "
        "apagados quando o app dorme ou é atualizado. O CSV abaixo é só uma cópia extra."
    )
else:
    st.warning(
        "Os dados estão salvos apenas neste servidor. Se este app estiver publicado na "
        "Streamlit Community Cloud, eles são apagados quando o app dorme ou é atualizado. "
        "Exporte o CSV com frequência, ou configure a Planilha do Google (veja o README) "
        "para os dados nunca mais serem apagados."
    )

todos = listar_todos(conexao)

st.subheader("Exportar")
if todos:
    df = pd.DataFrame(
        [
            {
                "descricao": l.descricao,
                "categoria": l.categoria,
                "tipo": l.tipo,
                "valor": l.valor,
                "data": l.data.isoformat(),
                "usuario": l.usuario,
                "repeticao": l.repeticao,
                "parcela_total": l.parcela_total,
                "ativa": l.ativa,
                "data_fim": l.data_fim.isoformat() if l.data_fim else "",
                "observacao": l.observacao,
            }
            for l in todos
        ]
    )
    st.download_button(
        "Baixar todos os lançamentos (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"financas_pessoais_{date.today().isoformat()}.csv",
        mime="text/csv",
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.caption("Nenhum lançamento para exportar ainda.")

st.divider()
st.subheader("Importar")
st.caption("Envie um CSV exportado por este mesmo sistema. Os lançamentos serão adicionados aos já existentes.")
arquivo = st.file_uploader("Arquivo CSV", type="csv")
if arquivo is not None:
    df_importado = pd.read_csv(arquivo)
    if st.button("Confirmar importação", type="primary"):
        adicionados = 0
        for _, linha in df_importado.iterrows():
            inserir(
                conexao,
                Lancamento(
                    descricao=str(linha["descricao"]),
                    categoria=str(linha["categoria"]),
                    tipo=str(linha["tipo"]),
                    valor=float(linha["valor"]),
                    data=date.fromisoformat(str(linha["data"])),
                    usuario=str(linha["usuario"]),
                    repeticao=str(linha.get("repeticao", "unica")),
                    parcela_total=int(linha["parcela_total"]) if pd.notna(linha.get("parcela_total")) else None,
                    ativa=bool(linha.get("ativa", True)),
                    data_fim=date.fromisoformat(str(linha["data_fim"])) if linha.get("data_fim") and pd.notna(linha.get("data_fim")) and str(linha.get("data_fim")) else None,
                    observacao=str(linha.get("observacao", "")) if pd.notna(linha.get("observacao", "")) else "",
                ),
            )
            adicionados += 1
        st.success(f"{adicionados} lançamento(s) importado(s).")
        st.rerun()
