import pytest

from src.parsers.fracoes_parser import parse_fracoes


def test_parse_fracoes_pdf_extrai_unidades_fracoes_e_proprietarios(caminho_fracoes_pdf):
    df = parse_fracoes(caminho_fracoes_pdf)
    assert len(df) == 11
    assert set(df["unidade"]) == {
        "APTO 01", "APTO 02", "APTO 03", "APTO 04", "APTO 05",
        "APTO 06", "APTO 07", "APTO 08", "LOJA 01", "LOJA 02", "SALA 01",
    }
    assert df["fracao"].sum() == pytest.approx(100.0, abs=0.01)
    linha_loja = df[df["unidade"] == "LOJA 01"].iloc[0]
    assert linha_loja["proprietario"] == "PROPRIETARIO 09"
    assert linha_loja["fracao"] == pytest.approx(4.867)


def test_parse_fracoes_excel_separa_unidade_e_proprietario(caminho_fracoes_excel):
    df = parse_fracoes(caminho_fracoes_excel)
    assert len(df) == 11
    linha_apto1 = df[df["unidade"] == "APTO 01"].iloc[0]
    assert linha_apto1["proprietario"] == "PROPRIETARIO 01"
    assert linha_apto1["fracao"] == pytest.approx(0.09202)
    assert df["fracao"].sum() == pytest.approx(1.0, abs=0.001)


def test_parse_fracoes_formato_nao_suportado_gera_erro_amigavel():
    with pytest.raises(ValueError):
        parse_fracoes("arquivo.docx")
