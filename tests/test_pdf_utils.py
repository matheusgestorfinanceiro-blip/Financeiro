from src.parsers.pdf_utils import remover_cabecalho_inline


def test_remove_cabecalho_colado_no_meio_da_linha():
    # Regressão: em alguns PDFs reais o pdfplumber cola o cabeçalho repetido
    # ("usuario@dominio.com em DD/MM/AAAA HH:MM:SS") na mesma linha do último
    # item de conteúdo, corrompendo o rótulo da categoria/subcategoria.
    linha = "Placas de Sinalização e similiares adrielle@admazul.adm.br em 14/07/2026 11:15:33 225,00 18,75 0,39%"
    resultado = remover_cabecalho_inline(linha)
    assert "adrielle@admazul.adm.br" not in resultado
    assert resultado == "Placas de Sinalização e similiares  225,00 18,75 0,39%"


def test_remove_cabecalho_quando_linha_e_so_o_cabecalho():
    linha = "gestor@admazul.com.br em 03/07/2026 16:42:08"
    assert remover_cabecalho_inline(linha) == ""


def test_nao_altera_linha_sem_cabecalho():
    linha = "COELBA 11000 916,67 0,13"
    assert remover_cabecalho_inline(linha) == linha
