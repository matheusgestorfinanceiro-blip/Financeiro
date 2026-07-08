import shutil

import pytest
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

from src.obra.extracao import TextoNaoReconhecido, extrair_texto, interpretar_comprovante

TESSERACT_DISPONIVEL = shutil.which("tesseract") is not None


def test_interpretar_comprovante_identifica_data_valor_fornecedor():
    texto = (
        "Loja ABC Materiais de Construcao\n"
        "CNPJ: 12.345.678/0001-99\n"
        "Data: 05/03/2026\n"
        "Item: Cimento 50kg\n"
        "SUBTOTAL R$ 100,00\n"
        "TOTAL R$ 1.234,56\n"
    )

    extraido = interpretar_comprovante(texto)

    assert extraido.data == "2026-03-05"
    assert extraido.valor == 1234.56
    assert extraido.fornecedor == "Loja ABC Materiais de Construcao"
    assert extraido.campos_nao_encontrados == []
    assert "Loja ABC Materiais de Construcao" in extraido.descricao_sugerida


def test_interpretar_comprovante_campos_faltando():
    extraido = interpretar_comprovante("   \n   \n")

    assert extraido.data is None
    assert extraido.valor is None
    assert extraido.fornecedor is None
    assert set(extraido.campos_nao_encontrados) == {"data", "valor", "fornecedor"}


def test_interpretar_comprovante_usa_maior_valor_sem_total():
    texto = "Recibo\nItem 1: 50,00\nItem 2: 199,90\n"

    extraido = interpretar_comprovante(texto)

    assert extraido.valor == 199.90


def test_extrair_texto_pdf_com_camada_de_texto():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Loja Teste - Data: 10/01/2026 - TOTAL R$ 100,00")
    conteudo = bytes(pdf.output())

    texto = extrair_texto("nota_fiscal.pdf", conteudo)

    assert "TOTAL" in texto
    assert "100,00" in texto


def test_extrair_texto_formato_nao_suportado():
    with pytest.raises(TextoNaoReconhecido):
        extrair_texto("arquivo.txt", b"conteudo qualquer")


@pytest.mark.skipif(not TESSERACT_DISPONIVEL, reason="tesseract não instalado neste ambiente")
def test_extrair_texto_imagem_via_ocr():
    imagem = Image.new("RGB", (600, 150), color="white")
    desenho = ImageDraw.Draw(imagem)
    try:
        fonte = ImageFont.load_default(size=32)
    except TypeError:
        fonte = ImageFont.load_default()
    desenho.text((10, 50), "TOTAL 100,00", fill="black", font=fonte)

    import io

    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")

    texto = extrair_texto("foto_recibo.png", buffer.getvalue())

    assert "100" in texto
