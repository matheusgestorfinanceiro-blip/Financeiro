import pandas as pd

from src.obra.relatorio_pdf import gerar_pdf_obra
from src.obra.schema import DadosObra


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
