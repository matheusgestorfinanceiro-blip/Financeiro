"""Leitor de arquivos de fração ideal/indexador (unidade, fração, proprietário).

Suporta Excel hoje (colunas identificadas por nome, sem diferenciar
maiúsculas/minúsculas). Leitura de PDF ainda não está implementada - depende
de um arquivo de exemplo real para definir o formato exato usado pela Azul
Administradora; até lá, a tabela pode ser preenchida manualmente na tela.
"""
import pandas as pd

COLUNAS_ESPERADAS = ["unidade", "fracao", "proprietario"]

_ALIAS_COLUNAS = {
    "unidade": ["unidade", "apartamento", "apto", "ap", "unid"],
    "fracao": ["fracao", "fração", "fracao ideal", "fração ideal", "indexador", "peso"],
    "proprietario": ["proprietario", "proprietário", "nome", "morador"],
}


def _renomear_colunas(df: pd.DataFrame) -> pd.DataFrame:
    mapa = {}
    for coluna in df.columns:
        chave = str(coluna).strip().lower()
        for nome_final, alias in _ALIAS_COLUNAS.items():
            if chave in alias:
                mapa[coluna] = nome_final
                break
    return df.rename(columns=mapa)


def parse_fracoes(arquivo) -> pd.DataFrame:
    """Lê um arquivo Excel ou PDF com unidade/fração/proprietário.

    `arquivo` é o objeto retornado por `st.file_uploader` (tem `.name`).
    """
    nome = getattr(arquivo, "name", "") or ""
    nome_lower = nome.lower()

    if nome_lower.endswith((".xlsx", ".xls")):
        df = pd.read_excel(arquivo)
        df = _renomear_colunas(df)
        faltando = [c for c in COLUNAS_ESPERADAS if c not in df.columns]
        if faltando:
            raise ValueError(f"Colunas não encontradas na planilha: {', '.join(faltando)}")
        df["unidade"] = df["unidade"].astype(str)
        df["fracao"] = pd.to_numeric(df["fracao"], errors="coerce").fillna(0.0)
        return df[COLUNAS_ESPERADAS]

    raise ValueError(
        "Leitura automática de PDF ainda não configurada. Preencha ou ajuste a tabela manualmente abaixo."
    )
