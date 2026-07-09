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
_PADRAO_LINHA_ITEM = re.compile(r"^(.*?)[\s:]*R?\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2})\s*$")

# Rótulos genéricos de documento/rodapé que não são o nome do fornecedor,
# mesmo aparecendo como a "primeira linha com letras" do texto extraído.
_ROTULOS_GENERICOS_FORNECEDOR = {
    "nf-e",
    "nfe",
    "nota fiscal eletronica",
    "nota fiscal eletrônica",
    "nota fiscal",
    "cupom fiscal",
    "cupom fiscal eletronico",
    "cupom fiscal eletrônico",
    "danfe",
    "documento auxiliar",
    "documento auxiliar da nota fiscal eletronica",
    "documento auxiliar da nota fiscal eletrônica",
    "via do consumidor",
    "consumidor",
    "recibo",
    "comprovante",
    "comprovante de pagamento",
}

# Linhas que contêm alguma dessas palavras não são itens comprados, mesmo que
# terminem em um valor monetário (são totais, tributos, dados do documento etc).
_PALAVRAS_LINHA_NAO_ITEM = {
    "total",
    "subtotal",
    "desconto",
    "troco",
    "acrescimo",
    "acréscimo",
    "valor pago",
    "valor recebido",
    "forma de pagamento",
    "forma pagamento",
    "dinheiro",
    "cartao",
    "cartão",
    "pix",
    "cnpj",
    "cpf",
    "ie:",
    "inscricao estadual",
    "inscrição estadual",
    "endereco",
    "endereço",
    "chave de acesso",
    "protocolo",
    "autorizacao",
    "autorização",
    "tributos",
    "icms",
    "issqn",
    "cofins",
    "pis",
    "caixa",
    "operador",
    "atendente",
    "item",
    "qtd",
    "unit",
    "cod.",
    "codigo",
    "código",
}


class TextoNaoReconhecido(Exception):
    """Levantada quando não foi possível ler nenhum texto do arquivo (ex: OCR indisponível)."""


@dataclass
class ItemComprovante:
    """Um item (produto ou serviço) identificado na nota/comprovante."""

    descricao: str
    valor: float


@dataclass
class ComprovanteExtraido:
    texto_bruto: str
    data: str | None = None  # "AAAA-MM-DD"
    valor: float | None = None
    fornecedor: str | None = None
    descricao_sugerida: str = ""
    itens: list[ItemComprovante] = field(default_factory=list)
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


def _e_candidata_a_fornecedor(linha: str) -> bool:
    linha_limpa = linha.strip()
    if not linha_limpa or len(linha_limpa) > 60:
        return False
    letras = sum(1 for c in linha_limpa if c.isalpha())
    if letras < 3:
        return False
    linha_lower = linha_limpa.lower().strip(" -:")
    return linha_lower not in _ROTULOS_GENERICOS_FORNECEDOR


def _identificar_fornecedor(texto: str) -> str | None:
    linhas = [l.strip() for l in texto.splitlines()]

    # Em notas fiscais e cupons, o nome do emitente costuma aparecer logo
    # acima do CNPJ - preferimos essa pista quando disponível.
    for i, linha in enumerate(linhas):
        if "cnpj" in linha.lower():
            for anterior in reversed(linhas[:i]):
                if _e_candidata_a_fornecedor(anterior):
                    return anterior[:60]
            break

    for linha in linhas:
        if _e_candidata_a_fornecedor(linha):
            return linha[:60]
    return None


def _identificar_itens(texto: str) -> list[ItemComprovante]:
    """Identifica linhas de item (descrição + valor) na nota, ignorando
    totais, tributos e dados do documento/estabelecimento."""
    itens = []
    for linha in texto.splitlines():
        linha_limpa = linha.strip()
        if not linha_limpa:
            continue

        linha_lower = linha_limpa.lower()
        if any(palavra in linha_lower for palavra in _PALAVRAS_LINHA_NAO_ITEM):
            continue

        correspondencia = _PADRAO_LINHA_ITEM.match(linha_limpa)
        if not correspondencia:
            continue

        descricao = correspondencia.group(1).strip(" -:\t")
        descricao = re.sub(r"^\d+[\s.xX*]+", "", descricao).strip()  # remove código/quantidade no início
        # remove quantidade/valor unitario que sobraram entre a descricao e o
        # valor total da linha (ex: "CIMENTO 50KG   2   32,50" -> "CIMENTO 50KG")
        descricao = re.sub(r"(\s+[\d.,]+)+$", "", descricao).strip()
        descricao = re.sub(r"\s{2,}", " ", descricao)
        letras = sum(1 for c in descricao if c.isalpha())
        if letras < 3:
            continue

        valor = float(correspondencia.group(2).replace(".", "").replace(",", "."))
        if valor <= 0:
            continue

        itens.append(ItemComprovante(descricao=descricao[:80], valor=valor))
    return itens


def interpretar_comprovante(texto: str) -> ComprovanteExtraido:
    data = _identificar_data(texto)
    valor = _identificar_valor(texto)
    fornecedor = _identificar_fornecedor(texto)
    itens = _identificar_itens(texto)

    campos_nao_encontrados = []
    if not data:
        campos_nao_encontrados.append("data")
    if not valor and not itens:
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
        itens=itens,
        campos_nao_encontrados=campos_nao_encontrados,
    )
