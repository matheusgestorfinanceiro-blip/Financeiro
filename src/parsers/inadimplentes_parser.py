"""Lê o relatório 'Inadimplentes' (PDF) e extrai as unidades em atraso."""
import re

import pandas as pd
import pdfplumber

from src.models.schema import DadosInadimplencia

RODAPE_RE = re.compile(
    r"(\d+)\s+unidades\s+inadimplentes\s+\((\d+,\d+)%\)\s+"
    r"(-?\d{1,3}(?:\.\d{3})*,\d{2})\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})"
)
EMAIL_CABECALHO_RE = re.compile(r"^[\w.+-]+@[\w.-]+\.\w+")
# O codigo da unidade tanto pode vir como "AP 01"/"APTO 01"/"LOJA 01"/"SALA 01"
# quanto so um numero (ex: "05 - NOME"), dependendo do condominio. O nome pode
# vir seguido de uma tag de status (ex: "Juridico", "1a Notificacao").
UNIDADE_RE = re.compile(
    r"^(\d{1,4}|AP\s*\S+|APTO\s*\S+|LOJA\s*\S+|SALA\s*\S+)\s*-\s*(.+?)"
    r"(\s+(?:Jur[íi]dico|\d°\s*Notifica[çc][ãa]o))?$"
)
LANCAMENTO_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{2})\s+(\d{2}/\d{4})\s+(\d+)\s+(\d+)\s+"
    r"(-?\d{1,3}(?:\.\d{3})*,\d{2})\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})\s+"
    r"(-?\d{1,3}(?:\.\d{3})*,\d{2})\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})\s+"
    r"(-?\d{1,3}(?:\.\d{3})*,\d{2})$"
)


def _para_float(texto: str) -> float:
    return float(texto.replace(".", "").replace(",", "."))


def parse_inadimplentes(caminho_pdf: str) -> DadosInadimplencia:
    """Extrai a lista de unidades inadimplentes e o percentual geral do condomínio."""
    linhas: list[str] = []
    condominio = ""
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ""
            linhas.extend(texto.split("\n"))

    for linha in linhas:
        linha_stripped = linha.strip()
        if linha_stripped and not EMAIL_CABECALHO_RE.match(linha_stripped):
            condominio = linha_stripped
            break

    registros = []
    unidade_atual = None
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        m_lanc = LANCAMENTO_RE.match(linha)
        if m_lanc and unidade_atual:
            vencimento, competencia, atraso, codigo, principal, juros, multa, honorarios, total = m_lanc.groups()
            registros.append(
                {
                    "unidade": unidade_atual,
                    "vencimento": vencimento,
                    "competencia": competencia,
                    "atraso_dias": int(atraso),
                    "codigo": codigo,
                    "principal": _para_float(principal),
                    "juros": _para_float(juros),
                    "multa": _para_float(multa),
                    "honorarios": _para_float(honorarios),
                    "total": _para_float(total),
                }
            )
            continue
        m_unidade = UNIDADE_RE.match(linha)
        if m_unidade and "Vencimento" not in linha and not linha.lower().startswith("total"):
            unidade_atual = f"{m_unidade.group(1).strip()} - {m_unidade.group(2).strip()}"

    df = pd.DataFrame(
        registros,
        columns=[
            "unidade", "vencimento", "competencia", "atraso_dias", "codigo",
            "principal", "juros", "multa", "honorarios", "total",
        ],
    )

    percentual_inadimplencia = 0.0
    qtd_unidades_inadimplentes = 0
    total_geral = 0.0
    total_principal = 0.0
    texto_completo = "\n".join(linhas)
    m_rodape = RODAPE_RE.search(texto_completo)
    if m_rodape:
        qtd_unidades_inadimplentes = int(m_rodape.group(1))
        percentual_inadimplencia = _para_float(m_rodape.group(2)) / 100
        total_principal = _para_float(m_rodape.group(3))
        total_geral = _para_float(m_rodape.group(4))
    elif not df.empty:
        qtd_unidades_inadimplentes = df["unidade"].nunique()
        total_geral = df["total"].sum()
        total_principal = df["principal"].sum()

    return DadosInadimplencia(
        condominio=condominio,
        unidades=df,
        qtd_unidades_inadimplentes=qtd_unidades_inadimplentes,
        percentual_inadimplencia=percentual_inadimplencia,
        total_principal=total_principal,
        total_geral=total_geral,
    )
