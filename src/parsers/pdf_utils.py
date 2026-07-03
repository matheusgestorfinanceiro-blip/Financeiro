"""Funções auxiliares compartilhadas pelos parsers de PDF."""
import re

NUMERO_BRL_RE = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2}")


def parse_moeda_brl(texto: str) -> float:
    """Converte um número no formato brasileiro ('1.234,56') para float."""
    texto = texto.strip().replace(".", "").replace(",", ".")
    return float(texto)


def extrair_numeros(linha: str) -> list[str]:
    """Retorna todos os tokens que parecem valores monetários numa linha."""
    return NUMERO_BRL_RE.findall(linha)


def rotulo_da_linha(linha: str, numeros: list[str]) -> str:
    """Retorna a parte da linha antes do primeiro número (o rótulo/categoria)."""
    if not numeros:
        return linha.strip()
    primeiro = numeros[0]
    idx = linha.find(primeiro)
    return linha[:idx].strip()
