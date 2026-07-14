"""Funções auxiliares compartilhadas pelos parsers de PDF."""
import re

NUMERO_BRL_RE = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2}")

# O sistema de gestao condominial repete um cabecalho ("usuario@dominio.com em
# DD/MM/AAAA HH:MM:SS") no topo de cada pagina. Normalmente ele sai como uma
# linha propria no texto extraido, mas em alguns PDFs reais o pdfplumber cola
# esse cabecalho na MESMA linha do ultimo item de conteudo (quando o item cai
# bem na quebra de pagina) - isso corrompia o rotulo da categoria/subcategoria
# com o texto do cabecalho embutido no meio. Remover essa substring de
# qualquer lugar da linha, nao so quando ela esta sozinha.
CABECALHO_INLINE_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+\s+em\s+\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}")


def remover_cabecalho_inline(linha: str) -> str:
    """Remove um cabeçalho de página ('email em data hora') colado no meio de
    uma linha de conteúdo, onde quer que ele apareça."""
    return CABECALHO_INLINE_RE.sub("", linha).strip()


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
