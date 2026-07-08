"""Leitura automática de comprovantes (PDF ou foto/imagem) para pré-preencher
um lançamento de gasto: extrai o texto do arquivo e tenta identificar data,
valor e fornecedor. Campos que não forem encontrados ficam em branco para o
usuário conferir e preencher antes de confirmar o lançamento."""
import io
import re
from dataclasses import dataclass, field

import fitz  # PyMuPDF
from PIL import Image

TAMANHO_MINIMO_TEXTO_PDF = 20  # abaixo disso, tratamos o PDF como digitalizado (sem camada de texto) e usamos OCR

EXTENSOES_IMAGEM = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

_PADRAO_DATA = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b")
_PADRAO_VALOR = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2})")


class TextoNaoReconhecido(Exception):
    """Levantada quando não foi possível ler nenhum texto do arquivo (ex: OCR indisponível)."""


@dataclass
class ComprovanteExtraido:
    texto_bruto: str
    data: str | None = None  # "AAAA-MM-DD"
    valor: float | None = None
    fornecedor: str | None = None
    descricao_sugerida: str = ""
    campos_nao_encontrados: list[str] = field(default_factory=list)


def _ocr_imagem(imagem: Image.Image) -> str:
    import pytesseract

    return pytesseract.image_to_string(imagem, lang="por+eng")


def extrair_texto(nome_arquivo: str, conteudo: bytes) -> str:
    """Extrai o texto de um PDF (camada de texto ou, se não houver, via OCR das
    páginas) ou de uma foto/imagem (via OCR). Levanta TextoNaoReconhecido se
    não for possível ler nada (ex: tesseract não instalado no servidor)."""
    nome_lower = nome_arquivo.lower()

    if nome_lower.endswith(".pdf"):
        with fitz.open(stream=conteudo, filetype="pdf") as documento:
            texto = "\n".join(pagina.get_text() for pagina in documento)
            if len(texto.strip()) >= TAMANHO_MINIMO_TEXTO_PDF:
                return texto

            partes_ocr = []
            try:
                for pagina in documento:
                    pixmap = pagina.get_pixmap(dpi=200)
                    imagem = Image.open(io.BytesIO(pixmap.tobytes("png")))
                    partes_ocr.append(_ocr_imagem(imagem))
            except Exception as exc:
                raise TextoNaoReconhecido(str(exc)) from exc
            return "\n".join(partes_ocr)

    if nome_lower.endswith(EXTENSOES_IMAGEM):
        try:
            imagem = Image.open(io.BytesIO(conteudo))
            return _ocr_imagem(imagem)
        except Exception as exc:
            raise TextoNaoReconhecido(str(exc)) from exc

    raise TextoNaoReconhecido(f"Formato de arquivo não suportado: {nome_arquivo}")


def _identificar_data(texto: str) -> str | None:
    for dia, mes, ano in _PADRAO_DATA.findall(texto):
        dia, mes = int(dia), int(mes)
        ano = int(ano)
        if ano < 100:
            ano += 2000
        if not (1 <= dia <= 31 and 1 <= mes <= 12 and 2000 <= ano <= 2100):
            continue
        try:
            import datetime

            return datetime.date(ano, mes, dia).isoformat()
        except ValueError:
            continue
    return None


def _identificar_valor(texto: str) -> float | None:
    linhas = texto.splitlines()
    candidatos_total = []
    for linha in linhas:
        if "total" in linha.lower() and "subtotal" not in linha.lower():
            candidatos_total.extend(_PADRAO_VALOR.findall(linha))

    def _para_float(valor_str: str) -> float:
        return float(valor_str.replace(".", "").replace(",", "."))

    if candidatos_total:
        return max(_para_float(v) for v in candidatos_total)

    todos = _PADRAO_VALOR.findall(texto)
    if todos:
        return max(_para_float(v) for v in todos)
    return None


def _identificar_fornecedor(texto: str) -> str | None:
    for linha in texto.splitlines():
        linha_limpa = linha.strip()
        letras = sum(1 for c in linha_limpa if c.isalpha())
        if letras >= 3 and len(linha_limpa) <= 60:
            return linha_limpa[:60]
    return None


def interpretar_comprovante(texto: str) -> ComprovanteExtraido:
    data = _identificar_data(texto)
    valor = _identificar_valor(texto)
    fornecedor = _identificar_fornecedor(texto)

    campos_nao_encontrados = []
    if not data:
        campos_nao_encontrados.append("data")
    if not valor:
        campos_nao_encontrados.append("valor")
    if not fornecedor:
        campos_nao_encontrados.append("fornecedor")

    descricao_sugerida = f"Compra em {fornecedor}" if fornecedor else ""

    return ComprovanteExtraido(
        texto_bruto=texto,
        data=data,
        valor=valor,
        fornecedor=fornecedor,
        descricao_sugerida=descricao_sugerida,
        campos_nao_encontrados=campos_nao_encontrados,
    )
