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


def test_identificar_fornecedor_ignora_rotulo_generico_e_usa_nome_perto_do_cnpj():
    texto = (
        "NF-e\n"
        "DANFE\n"
        "MATERIAIS SILVA LTDA\n"
        "CNPJ: 11.222.333/0001-44\n"
        "DATA EMISSAO: 13/06/2026\n"
        "TOTAL R$ 64,90\n"
    )

    extraido = interpretar_comprovante(texto)

    assert extraido.fornecedor == "MATERIAIS SILVA LTDA"


def test_identifica_todos_os_itens_de_uma_nota_fiscal():
    texto = (
        "NF-e\n"
        "MATERIAIS SILVA LTDA\n"
        "CNPJ: 11.222.333/0001-44\n"
        "DATA EMISSAO: 13/06/2026\n"
        "DESCRICAO DO PRODUTO/SERVICO                 QTD   VL UNIT   VL TOTAL\n"
        "CIMENTO CP II 50KG                             2     32,50      65,00\n"
        "AREIA MEDIA LAVADA M3                          1     89,90      89,90\n"
        "TIJOLO CERAMICO 8 FUROS UN                   100      1,20     120,00\n"
        "SUBTOTAL R$ 274,90\n"
        "DESCONTO R$ 0,00\n"
        "TOTAL R$ 274,90\n"
        "FORMA DE PAGAMENTO: DINHEIRO\n"
    )

    extraido = interpretar_comprovante(texto)

    assert extraido.fornecedor == "MATERIAIS SILVA LTDA"
    assert len(extraido.itens) == 3
    descricoes = [item.descricao for item in extraido.itens]
    valores = [item.valor for item in extraido.itens]
    assert "CIMENTO CP II 50KG" in descricoes
    assert "AREIA MEDIA LAVADA M3" in descricoes
    assert "TIJOLO CERAMICO 8 FUROS UN" in descricoes
    assert valores == [65.00, 89.90, 120.00]
    # mesmo com categoria unica, cada item da nota vira um lancamento proprio
    assert "valor" not in extraido.campos_nao_encontrados


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
