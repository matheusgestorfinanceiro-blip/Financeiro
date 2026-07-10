"""Persistência numa Google Sheets — os dados sobrevivem a reinícios do
servidor gratuito da Streamlit Cloud (diferente do SQLite local, que é
apagado sempre que o app "dorme" ou é atualizado)."""
import uuid
from datetime import date

import pandas as pd
import streamlit as st

from src.pessoal.modelos import Lancamento

NOME_ABA = "lancamentos"
COLUNAS = [
    "id", "descricao", "categoria", "tipo", "valor", "data", "usuario",
    "repeticao", "parcela_total", "ativa", "data_fim", "observacao",
]


def disponivel() -> bool:
    """True se a planilha estiver configurada nos secrets do Streamlit."""
    try:
        return "gsheets" in st.secrets.get("connections", {})
    except Exception:
        return False


def conectar():
    from streamlit_gsheets import GSheetsConnection

    return st.connection("gsheets", type=GSheetsConnection)


def _df_vazio() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUNAS)


def _ler(conexao) -> pd.DataFrame:
    from gspread.exceptions import WorksheetNotFound

    try:
        df = conexao.read(worksheet=NOME_ABA, ttl=0)
    except WorksheetNotFound:
        # Primeira vez usando a planilha: cria a aba "lancamentos" com o
        # cabeçalho certo, já que ela não existe ainda.
        conexao.create(worksheet=NOME_ABA, data=_df_vazio())
        return _df_vazio()
    df = df.dropna(how="all")
    if df.empty:
        return _df_vazio()
    return df.reset_index(drop=True)


def _escrever(conexao, df: pd.DataFrame) -> None:
    conexao.update(worksheet=NOME_ABA, data=df[COLUNAS])


def _vazio_para_none(valor):
    if valor is None:
        return None
    if isinstance(valor, float) and pd.isna(valor):
        return None
    texto = str(valor).strip()
    return texto if texto and texto.lower() != "nan" else None


def linha_para_lancamento(linha) -> Lancamento:
    parcela_total = _vazio_para_none(linha.get("parcela_total"))
    data_fim = _vazio_para_none(linha.get("data_fim"))
    ativa = linha.get("ativa")
    return Lancamento(
        id=str(linha["id"]),
        descricao=str(linha["descricao"]),
        categoria=str(linha["categoria"]),
        tipo=str(linha["tipo"]),
        valor=float(linha["valor"]),
        data=date.fromisoformat(str(linha["data"])),
        usuario=str(linha["usuario"]),
        repeticao=str(linha["repeticao"]),
        parcela_total=int(float(parcela_total)) if parcela_total else None,
        ativa=bool(ativa) if not isinstance(ativa, str) else ativa.strip().upper() != "FALSE",
        data_fim=date.fromisoformat(data_fim) if data_fim else None,
        observacao=_vazio_para_none(linha.get("observacao")) or "",
    )


def lancamento_para_linha(lancamento: Lancamento) -> dict:
    return {
        "id": lancamento.id,
        "descricao": lancamento.descricao,
        "categoria": lancamento.categoria,
        "tipo": lancamento.tipo,
        "valor": lancamento.valor,
        "data": lancamento.data.isoformat(),
        "usuario": lancamento.usuario,
        "repeticao": lancamento.repeticao,
        "parcela_total": lancamento.parcela_total if lancamento.parcela_total else "",
        "ativa": lancamento.ativa,
        "data_fim": lancamento.data_fim.isoformat() if lancamento.data_fim else "",
        "observacao": lancamento.observacao,
    }


def listar_todos(conexao) -> list[Lancamento]:
    df = _ler(conexao)
    lancamentos = [linha_para_lancamento(linha) for _, linha in df.iterrows()]
    return sorted(lancamentos, key=lambda l: (l.data, str(l.id)), reverse=True)


def inserir(conexao, lancamento: Lancamento) -> str:
    df = _ler(conexao)
    lancamento.id = str(uuid.uuid4())[:8]
    nova_linha = pd.DataFrame([lancamento_para_linha(lancamento)])
    df = pd.concat([df, nova_linha], ignore_index=True)
    _escrever(conexao, df)
    return lancamento.id


def excluir(conexao, id_lancamento) -> None:
    df = _ler(conexao)
    df = df[df["id"].astype(str) != str(id_lancamento)]
    _escrever(conexao, df)


def encerrar_fixa(conexao, id_lancamento, data_fim: date) -> None:
    df = _ler(conexao)
    df.loc[df["id"].astype(str) == str(id_lancamento), "data_fim"] = data_fim.isoformat()
    _escrever(conexao, df)
