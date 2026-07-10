"""Leitor de arquivos de fração ideal/indexador (unidade, fração, proprietário),
a partir dos 2 formatos reais usados pela Azul Administradora: o relatório em
PDF "Contatos das unidades" (mesmo sistema de gestão condominial dos outros 2
PDFs) e uma planilha Excel de cálculo de rateio."""
import re
import unicodedata

import pandas as pd
import pdfplumber

COLUNAS_ESPERADAS = ["unidade", "fracao", "proprietario"]

_ALIAS_COLUNAS = {
    "unidade": ["unidade", "unidades", "apartamento", "apto", "ap", "unid"],
    "fracao": ["fracao", "fracao ideal", "indexador", "peso"],
    "proprietario": ["proprietario", "nome", "morador"],
}

_LINHA_FRACAO_RE = re.compile(
    r"^(?P<unidade>\S+\s+\S+)\s+(?P<nome>.+?)\s+Propriet[áa]rio\s+(?P<fracao>\d+,\d+)$"
)

_LINHA_HIFEN_RE = re.compile(r"^(?P<unidade>.+?)\s*-\s*(?P<proprietario>.+)$")


def _sem_acento(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in normalizado if not unicodedata.combining(c))


def _chave(texto: str) -> str:
    return _sem_acento(texto).strip().lower()


def _para_float_livre(texto: str) -> float:
    """Converte um número no formato brasileiro sem exigir 2 casas decimais
    fixas (frações vêm com 2 ou 3 casas, ex: '9,202' e '17,67'), diferente do
    parse_moeda_brl de pdf_utils.py (específico para valores monetários)."""
    return float(texto.strip().replace(".", "").replace(",", "."))


def _parse_fracoes_pdf(caminho: str) -> pd.DataFrame:
    registros = []
    with pdfplumber.open(caminho) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ""
            for linha in texto.split("\n"):
                m = _LINHA_FRACAO_RE.match(linha.strip())
                if not m:
                    continue
                registros.append(
                    {
                        "unidade": m.group("unidade").strip(),
                        "fracao": _para_float_livre(m.group("fracao")),
                        "proprietario": m.group("nome").strip(),
                    }
                )

    if not registros:
        raise ValueError(
            "Não encontrei nenhuma linha de unidade/fração reconhecível neste PDF."
        )
    return pd.DataFrame(registros, columns=COLUNAS_ESPERADAS)


def _localizar_linha_cabecalho(bruto: pd.DataFrame) -> tuple[int, dict[int, str]] | None:
    """Procura, nas primeiras linhas da planilha, a linha de cabeçalho da
    tabela (coluna de unidade + coluna de fração), sem assumir que está na
    primeira linha - na planilha real, o cabeçalho está na linha 4."""
    limite = min(15, len(bruto))
    for indice_linha in range(limite):
        colunas_encontradas: dict[str, int] = {}
        for indice_coluna, valor in enumerate(bruto.iloc[indice_linha]):
            if pd.isna(valor):
                continue
            chave = _chave(valor)
            for nome_final, alias in _ALIAS_COLUNAS.items():
                if chave in alias and nome_final not in colunas_encontradas:
                    colunas_encontradas[nome_final] = indice_coluna
        if "unidade" in colunas_encontradas and "fracao" in colunas_encontradas:
            mapa = {indice: nome for nome, indice in colunas_encontradas.items()}
            return indice_linha, mapa
    return None


def _parse_fracoes_excel(caminho: str) -> pd.DataFrame:
    bruto = pd.read_excel(caminho, header=None)
    encontrado = _localizar_linha_cabecalho(bruto)
    if encontrado is None:
        raise ValueError(
            "Não encontrei uma coluna de unidade e uma coluna de fração nesta planilha."
        )
    linha_cabecalho, mapa_colunas = encontrado

    registros = []
    for _, linha in bruto.iloc[linha_cabecalho + 1 :].iterrows():
        celula_unidade = linha[[i for i, n in mapa_colunas.items() if n == "unidade"][0]]
        celula_fracao = linha[[i for i, n in mapa_colunas.items() if n == "fracao"][0]]

        if pd.isna(celula_unidade) or pd.isna(celula_fracao):
            continue
        if _chave(celula_unidade) == "total":
            break

        proprietario = ""
        indices_proprietario = [i for i, n in mapa_colunas.items() if n == "proprietario"]
        if indices_proprietario:
            valor_proprietario = linha[indices_proprietario[0]]
            proprietario = "" if pd.isna(valor_proprietario) else str(valor_proprietario).strip()
            unidade = str(celula_unidade).strip()
        else:
            m = _LINHA_HIFEN_RE.match(str(celula_unidade).strip())
            if m:
                unidade = m.group("unidade").strip()
                proprietario = m.group("proprietario").strip()
            else:
                unidade = str(celula_unidade).strip()

        registros.append(
            {
                "unidade": unidade,
                "fracao": float(celula_fracao),
                "proprietario": proprietario,
            }
        )

    if not registros:
        raise ValueError("Não encontrei nenhuma linha de dados abaixo do cabeçalho desta planilha.")
    return pd.DataFrame(registros, columns=COLUNAS_ESPERADAS)


def parse_fracoes(caminho: str) -> pd.DataFrame:
    """Lê um arquivo Excel ou PDF com unidade/fração/proprietário.

    `caminho` é o caminho local do arquivo (mesmo padrão de
    `parse_demonstrativo`/`parse_inadimplentes` - o chamador salva o arquivo
    enviado num arquivo temporário antes de chamar este parser).
    """
    caminho_lower = caminho.lower()

    if caminho_lower.endswith((".xlsx", ".xls")):
        return _parse_fracoes_excel(caminho)

    if caminho_lower.endswith(".pdf"):
        return _parse_fracoes_pdf(caminho)

    raise ValueError("Formato de arquivo não suportado. Envie um PDF ou uma planilha Excel (.xlsx).")
