"""Persistência dos gastos, dos dados da obra e dos metadados das
fotos/anexos numa Google Sheets — os dados sobrevivem a reinícios do
servidor gratuito da Streamlit Cloud (diferente dos arquivos locais, que
são apagados sempre que o app "dorme" ou é atualizado).

Os arquivos binários (fotos e comprovantes) não cabem numa planilha - essa
parte é sempre feita pelo Drive (`armazenamento_drive.py`) ou, se o Drive
não estiver configurado, localmente. Só os metadados (data, legenda etc.)
ficam aqui."""
from dataclasses import asdict

import pandas as pd
import streamlit as st

from src.obra.schema import DadosObra, FotoObra, GastoObra, NotaFiscalObra

NOME_ABA_GASTOS = "gastos_obra"
NOME_ABA_DADOS_OBRA = "dados_obra"
NOME_ABA_FOTOS = "fotos_obra"
NOME_ABA_NOTAS_FISCAIS = "notas_fiscais_obra"

COLUNAS_GASTOS = [
    "id", "data", "categoria", "descricao", "fornecedor", "valor", "pago", "observacoes", "anexo",
]
COLUNAS_FOTOS = ["id", "data", "nome_arquivo", "legenda"]
COLUNAS_NOTAS_FISCAIS = ["id", "data", "nome_arquivo", "legenda"]
CAMPOS_DADOS_OBRA = [
    "nome_obra",
    "proprietario",
    "endereco",
    "data_inicio",
    "previsao_termino",
    "orcamento_previsto",
    "status_obra",
    "observacoes_gerais",
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


def _gastos_vazio() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUNAS_GASTOS)


def _ler_gastos(conexao) -> pd.DataFrame:
    try:
        df = conexao.read(worksheet=NOME_ABA_GASTOS, ttl=0)
    except Exception:
        # aba ainda nao existe na planilha - cria vazia na primeira vez que for usada
        vazio = _gastos_vazio()
        try:
            conexao.create(worksheet=NOME_ABA_GASTOS, data=vazio)
        except Exception:
            pass
        return vazio

    df = df.dropna(how="all")
    if df.empty:
        return _gastos_vazio()

    df["data"] = pd.to_datetime(df["data"]).dt.date.astype(str)
    df["pago"] = df["pago"].astype(str).str.strip().str.lower().isin(["true", "1"])
    df["id"] = df["id"].astype(float).astype(int)
    df["valor"] = df["valor"].astype(float)
    if "anexo" not in df.columns:
        df["anexo"] = ""
    for coluna in ("fornecedor", "observacoes", "anexo"):
        df[coluna] = df[coluna].fillna("")
    return df.sort_values("data").reset_index(drop=True)


def _escrever_gastos(conexao, df: pd.DataFrame) -> None:
    conexao.update(worksheet=NOME_ABA_GASTOS, data=df[COLUNAS_GASTOS])


def carregar_gastos(conexao) -> pd.DataFrame:
    return _ler_gastos(conexao)


def adicionar_gasto(conexao, gasto: GastoObra) -> GastoObra:
    df = _ler_gastos(conexao)
    gasto.id = int(df["id"].max()) + 1 if not df.empty else 1
    nova_linha = pd.DataFrame([asdict(gasto)])
    df = pd.concat([df, nova_linha], ignore_index=True)
    _escrever_gastos(conexao, df)
    return gasto


def remover_gasto(conexao, id_gasto: int) -> None:
    df = _ler_gastos(conexao)
    df = df[df["id"] != int(id_gasto)]
    _escrever_gastos(conexao, df)


def atualizar_gasto(conexao, gasto: GastoObra) -> None:
    """Substitui um lançamento existente (identificado por `gasto.id`) pelos
    novos valores."""
    df = _ler_gastos(conexao)
    df = df[df["id"] != int(gasto.id)]
    nova_linha = pd.DataFrame([asdict(gasto)])
    df = pd.concat([df, nova_linha], ignore_index=True)
    _escrever_gastos(conexao, df)


def carregar_dados_obra(conexao) -> DadosObra | None:
    try:
        df = conexao.read(worksheet=NOME_ABA_DADOS_OBRA, ttl=0)
    except Exception:
        try:
            conexao.create(worksheet=NOME_ABA_DADOS_OBRA, data=pd.DataFrame(columns=["campo", "valor"]))
        except Exception:
            pass
        return None

    df = df.dropna(how="all")
    if df.empty:
        return None

    valores = dict(zip(df["campo"].astype(str), df["valor"]))
    if not any(str(v).strip() for v in valores.values()):
        return None

    def _texto(campo: str) -> str:
        valor = valores.get(campo)
        return "" if valor is None or (isinstance(valor, float) and pd.isna(valor)) else str(valor)

    orcamento = _texto("orcamento_previsto")
    return DadosObra(
        nome_obra=_texto("nome_obra"),
        proprietario=_texto("proprietario"),
        endereco=_texto("endereco"),
        data_inicio=_texto("data_inicio"),
        previsao_termino=_texto("previsao_termino"),
        orcamento_previsto=float(orcamento) if orcamento else 0.0,
        status_obra=_texto("status_obra") or "Em andamento",
        observacoes_gerais=_texto("observacoes_gerais"),
    )


def salvar_dados_obra(conexao, dados: DadosObra) -> None:
    dados_dict = asdict(dados)
    df = pd.DataFrame([{"campo": campo, "valor": dados_dict[campo]} for campo in CAMPOS_DADOS_OBRA])
    conexao.update(worksheet=NOME_ABA_DADOS_OBRA, data=df)


def _fotos_vazio() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUNAS_FOTOS)


def _ler_fotos(conexao) -> pd.DataFrame:
    try:
        df = conexao.read(worksheet=NOME_ABA_FOTOS, ttl=0)
    except Exception:
        vazio = _fotos_vazio()
        try:
            conexao.create(worksheet=NOME_ABA_FOTOS, data=vazio)
        except Exception:
            pass
        return vazio

    df = df.dropna(how="all")
    if df.empty:
        return _fotos_vazio()

    df["data"] = pd.to_datetime(df["data"]).dt.date.astype(str)
    df["id"] = df["id"].astype(float).astype(int)
    df["legenda"] = df["legenda"].fillna("")
    return df.sort_values(["data", "id"]).reset_index(drop=True)


def _escrever_fotos(conexao, df: pd.DataFrame) -> None:
    conexao.update(worksheet=NOME_ABA_FOTOS, data=df[COLUNAS_FOTOS])


def carregar_fotos(conexao) -> pd.DataFrame:
    return _ler_fotos(conexao)


def adicionar_foto_registro(conexao, foto: FotoObra) -> FotoObra:
    """Registra os metadados de uma foto cujo arquivo já foi salvo em algum
    lugar permanente (Drive) - veja `src/obra/repositorio.py`."""
    df = _ler_fotos(conexao)
    foto.id = int(df["id"].max()) + 1 if not df.empty else 1
    nova_linha = pd.DataFrame([asdict(foto)])
    df = pd.concat([df, nova_linha], ignore_index=True)
    _escrever_fotos(conexao, df)
    return foto


def remover_foto_registro(conexao, id_foto: int) -> None:
    df = _ler_fotos(conexao)
    df = df[df["id"] != int(id_foto)]
    _escrever_fotos(conexao, df)


def _notas_fiscais_vazio() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUNAS_NOTAS_FISCAIS)


def _ler_notas_fiscais(conexao) -> pd.DataFrame:
    try:
        df = conexao.read(worksheet=NOME_ABA_NOTAS_FISCAIS, ttl=0)
    except Exception:
        vazio = _notas_fiscais_vazio()
        try:
            conexao.create(worksheet=NOME_ABA_NOTAS_FISCAIS, data=vazio)
        except Exception:
            pass
        return vazio

    df = df.dropna(how="all")
    if df.empty:
        return _notas_fiscais_vazio()

    df["data"] = pd.to_datetime(df["data"]).dt.date.astype(str)
    df["id"] = df["id"].astype(float).astype(int)
    df["legenda"] = df["legenda"].fillna("")
    return df.sort_values(["data", "id"]).reset_index(drop=True)


def _escrever_notas_fiscais(conexao, df: pd.DataFrame) -> None:
    conexao.update(worksheet=NOME_ABA_NOTAS_FISCAIS, data=df[COLUNAS_NOTAS_FISCAIS])


def carregar_notas_fiscais(conexao) -> pd.DataFrame:
    return _ler_notas_fiscais(conexao)


def adicionar_nota_fiscal_registro(conexao, nota: NotaFiscalObra) -> NotaFiscalObra:
    """Registra os metadados de uma nota fiscal cujo arquivo já foi salvo em
    algum lugar permanente (Drive) - veja `src/obra/repositorio.py`."""
    df = _ler_notas_fiscais(conexao)
    nota.id = int(df["id"].max()) + 1 if not df.empty else 1
    nova_linha = pd.DataFrame([asdict(nota)])
    df = pd.concat([df, nova_linha], ignore_index=True)
    _escrever_notas_fiscais(conexao, df)
    return nota


def remover_nota_fiscal_registro(conexao, id_nota: int) -> None:
    df = _ler_notas_fiscais(conexao)
    df = df[df["id"] != int(id_nota)]
    _escrever_notas_fiscais(conexao, df)
