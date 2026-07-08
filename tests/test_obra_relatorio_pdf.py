import io

import pandas as pd
import pytest
from PIL import Image

from src.obra.armazenamento import adicionar_foto
from src.obra.relatorio_pdf import gerar_pdf_obra
from src.obra.schema import DadosObra


def _bytes_imagem_teste() -> bytes:
    imagem = Image.new("RGB", (400, 300), color="blue")
    buffer = io.BytesIO()
    imagem.save(buffer, format="JPEG")
    return buffer.getvalue()


def _df_gastos():
    return pd.DataFrame(
        [
            {
                "id": 1,
                "data": "2026-01-10",
                "categoria": "Material",
                "descricao": "Cimento e areia",
                "fornecedor": "Casa do Construtor",
                "valor": 1200.0,
                "pago": True,
                "observacoes": "",
            },
            {
                "id": 2,
                "data": "2026-02-14",
                "categoria": "Mão de obra",
                "descricao": "Pedreiro - 2 semanas",
                "fornecedor": "João Pedreiro",
                "valor": 3000.0,
                "pago": False,
                "observacoes": "",
            },
        ]
    )


def test_gerar_pdf_obra_com_orcamento():
    dados_obra = DadosObra(
        nome_obra="Reforma da cozinha",
        proprietario="Maria Silva",
        endereco="Rua das Flores, 123",
        data_inicio="2026-01-01",
        previsao_termino="2026-06-01",
        orcamento_previsto=10000.0,
        status_obra="Em andamento",
        observacoes_gerais="Obra dentro do previsto ate o momento.",
    )

    pdf_bytes = gerar_pdf_obra(dados_obra, _df_gastos())

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_gerar_pdf_obra_sem_orcamento_nem_observacoes():
    dados_obra = DadosObra(nome_obra="Reforma do banheiro", status_obra="Concluída")

    pdf_bytes = gerar_pdf_obra(dados_obra, _df_gastos())

    assert pdf_bytes.startswith(b"%PDF")


def test_relatorio_final_sem_fotos_levanta_erro():
    dados_obra = DadosObra(nome_obra="Reforma da cozinha")

    with pytest.raises(ValueError):
        gerar_pdf_obra(dados_obra, _df_gastos(), tipo_relatorio="final")


def test_relatorio_final_com_fotos_inclui_pagina_de_fotos(tmp_path):
    dados_obra = DadosObra(nome_obra="Reforma da cozinha")
    caminho_csv = tmp_path / "fotos.csv"
    dir_fotos = tmp_path / "fotos"
    adicionar_foto(_bytes_imagem_teste(), "inicio.jpg", "2026-01-05", "Início da obra", caminho_csv, dir_fotos)
    adicionar_foto(_bytes_imagem_teste(), "fim.jpg", "2026-02-20", "Obra finalizada", caminho_csv, dir_fotos)

    from src.obra.armazenamento import carregar_fotos

    df_fotos = carregar_fotos(caminho_csv)

    pdf_com_fotos = gerar_pdf_obra(dados_obra, _df_gastos(), df_fotos, dir_fotos, tipo_relatorio="final")
    pdf_sem_fotos = gerar_pdf_obra(dados_obra, _df_gastos(), tipo_relatorio="parcial")

    assert pdf_com_fotos.startswith(b"%PDF")
    # o relatorio com a pagina extra de fotos deve ser maior que o sem fotos
    assert len(pdf_com_fotos) > len(pdf_sem_fotos)


def test_relatorio_parcial_gerado_sem_fotos():
    dados_obra = DadosObra(nome_obra="Reforma da cozinha")

    pdf_bytes = gerar_pdf_obra(dados_obra, _df_gastos(), tipo_relatorio="parcial")

    assert pdf_bytes.startswith(b"%PDF")
