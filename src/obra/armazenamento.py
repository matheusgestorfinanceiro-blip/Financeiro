"""Persistência dos gastos, fotos, anexos e dados gerais da obra em arquivos
locais (CSV/JSON). Usado sempre para as fotos/anexos no modo local, e também
para tudo quando nem a Planilha nem o Drive estão configurados - veja
`src/obra/repositorio.py`."""
import json
import uuid
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from src.obra.schema import DadosObra, FotoObra, GastoObra

DIR_OBRA = Path(__file__).resolve().parents[2] / "data" / "obra"
CAMINHO_GASTOS = DIR_OBRA / "gastos.csv"
CAMINHO_DADOS_OBRA = DIR_OBRA / "dados_obra.json"
CAMINHO_FOTOS = DIR_OBRA / "fotos.csv"
DIR_FOTOS = DIR_OBRA / "fotos"
DIR_ANEXOS = DIR_OBRA / "anexos"

COLUNAS_FOTOS = ["id", "data", "nome_arquivo", "legenda"]

COLUNAS_GASTOS = [
    "id",
    "data",
    "categoria",
    "descricao",
    "fornecedor",
    "valor",
    "pago",
    "observacoes",
    "anexo",
]


def carregar_gastos(caminho: Path = CAMINHO_GASTOS) -> pd.DataFrame:
    caminho = Path(caminho)
    if not caminho.exists():
        return pd.DataFrame(columns=COLUNAS_GASTOS)
    df = pd.read_csv(caminho, dtype={"observacoes": str, "fornecedor": str})
    df["data"] = pd.to_datetime(df["data"]).dt.date.astype(str)
    df["pago"] = df["pago"].astype(str).str.strip().str.lower().isin(["true", "1"])
    if "anexo" not in df.columns:
        df["anexo"] = ""  # compatibilidade com gastos.csv salvos antes desse campo existir
    for coluna in ("fornecedor", "observacoes", "anexo"):
        df[coluna] = df[coluna].fillna("")
    return df.sort_values("data").reset_index(drop=True)


def salvar_gastos(df: pd.DataFrame, caminho: Path = CAMINHO_GASTOS) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False, columns=COLUNAS_GASTOS)


def adicionar_gasto(gasto: GastoObra, caminho: Path = CAMINHO_GASTOS) -> GastoObra:
    df = carregar_gastos(caminho)
    gasto.id = int(df["id"].max()) + 1 if not df.empty else 1
    nova_linha = pd.DataFrame([asdict(gasto)])
    df = pd.concat([df, nova_linha], ignore_index=True)
    salvar_gastos(df, caminho)
    return gasto


def remover_gasto(id_gasto: int, caminho: Path = CAMINHO_GASTOS) -> None:
    df = carregar_gastos(caminho)
    df = df[df["id"] != id_gasto]
    salvar_gastos(df, caminho)


def atualizar_gasto(gasto: GastoObra, caminho: Path = CAMINHO_GASTOS) -> None:
    """Substitui um lançamento existente (identificado por `gasto.id`) pelos
    novos valores."""
    df = carregar_gastos(caminho)
    df = df[df["id"] != gasto.id]
    nova_linha = pd.DataFrame([asdict(gasto)])
    df = pd.concat([df, nova_linha], ignore_index=True)
    salvar_gastos(df, caminho)


def carregar_dados_obra(caminho: Path = CAMINHO_DADOS_OBRA) -> DadosObra | None:
    caminho = Path(caminho)
    if not caminho.exists():
        return None
    with open(caminho, encoding="utf-8") as f:
        return DadosObra(**json.load(f))


def salvar_dados_obra(dados: DadosObra, caminho: Path = CAMINHO_DADOS_OBRA) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(asdict(dados), f, ensure_ascii=False, indent=2)


def carregar_fotos(caminho: Path = CAMINHO_FOTOS) -> pd.DataFrame:
    """Retorna as fotos cadastradas, ordenadas por data (ordem de execução da obra)."""
    caminho = Path(caminho)
    if not caminho.exists():
        return pd.DataFrame(columns=COLUNAS_FOTOS)
    df = pd.read_csv(caminho, dtype={"legenda": str, "nome_arquivo": str})
    df["data"] = pd.to_datetime(df["data"]).dt.date.astype(str)
    df["legenda"] = df["legenda"].fillna("")
    return df.sort_values(["data", "id"]).reset_index(drop=True)


def salvar_fotos(df: pd.DataFrame, caminho: Path = CAMINHO_FOTOS) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False, columns=COLUNAS_FOTOS)


def salvar_arquivo_local(conteudo: bytes, nome_original: str, diretorio: Path) -> str:
    """Salva um arquivo binário (foto ou anexo) num diretório local com um
    nome único, e retorna esse nome (usado depois para ler/remover)."""
    diretorio = Path(diretorio)
    diretorio.mkdir(parents=True, exist_ok=True)
    extensao = Path(nome_original).suffix or ""
    nome_arquivo = f"{uuid.uuid4().hex}{extensao}"
    (diretorio / nome_arquivo).write_bytes(conteudo)
    return nome_arquivo


def ler_arquivo_local(nome_arquivo: str, diretorio: Path) -> bytes:
    return (Path(diretorio) / nome_arquivo).read_bytes()


def remover_arquivo_local(nome_arquivo: str, diretorio: Path) -> None:
    caminho_arquivo = Path(diretorio) / nome_arquivo
    if caminho_arquivo.exists():
        caminho_arquivo.unlink()


def registrar_foto(foto: FotoObra, caminho_csv: Path = CAMINHO_FOTOS) -> FotoObra:
    """Grava os metadados de uma foto cujo arquivo já foi salvo em algum
    lugar (local ou Drive) - não mexe em nenhum arquivo."""
    df = carregar_fotos(caminho_csv)
    foto.id = int(df["id"].max()) + 1 if not df.empty else 1
    nova_linha = pd.DataFrame([asdict(foto)])
    df = pd.concat([df, nova_linha], ignore_index=True)
    salvar_fotos(df, caminho_csv)
    return foto


def desregistrar_foto(id_foto: int, caminho_csv: Path = CAMINHO_FOTOS) -> None:
    """Remove os metadados de uma foto - não mexe em nenhum arquivo."""
    df = carregar_fotos(caminho_csv)
    df = df[df["id"] != id_foto]
    salvar_fotos(df, caminho_csv)


def adicionar_foto(
    conteudo: bytes,
    nome_original: str,
    data: str,
    legenda: str = "",
    caminho_csv: Path = CAMINHO_FOTOS,
    dir_fotos: Path = DIR_FOTOS,
) -> FotoObra:
    """Salva o arquivo da foto em disco e registra seus metadados."""
    nome_arquivo = salvar_arquivo_local(conteudo, nome_original, dir_fotos)
    return registrar_foto(FotoObra(data=data, nome_arquivo=nome_arquivo, legenda=legenda), caminho_csv)


def remover_foto(id_foto: int, caminho_csv: Path = CAMINHO_FOTOS, dir_fotos: Path = DIR_FOTOS) -> None:
    df = carregar_fotos(caminho_csv)
    linha = df[df["id"] == id_foto]
    if not linha.empty:
        remover_arquivo_local(linha.iloc[0]["nome_arquivo"], dir_fotos)
    desregistrar_foto(id_foto, caminho_csv)
