"""Persistência dos gastos e dos dados gerais da obra em arquivos locais (CSV/JSON)."""
import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from src.obra.schema import DadosObra, GastoObra

DIR_OBRA = Path(__file__).resolve().parents[2] / "data" / "obra"
CAMINHO_GASTOS = DIR_OBRA / "gastos.csv"
CAMINHO_DADOS_OBRA = DIR_OBRA / "dados_obra.json"

COLUNAS_GASTOS = [
    "id",
    "data",
    "categoria",
    "descricao",
    "fornecedor",
    "valor",
    "pago",
    "observacoes",
]


def carregar_gastos(caminho: Path = CAMINHO_GASTOS) -> pd.DataFrame:
    caminho = Path(caminho)
    if not caminho.exists():
        return pd.DataFrame(columns=COLUNAS_GASTOS)
    df = pd.read_csv(caminho, dtype={"observacoes": str, "fornecedor": str})
    df["data"] = pd.to_datetime(df["data"]).dt.date.astype(str)
    df["pago"] = df["pago"].astype(str).str.strip().str.lower().isin(["true", "1"])
    for coluna in ("fornecedor", "observacoes"):
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
