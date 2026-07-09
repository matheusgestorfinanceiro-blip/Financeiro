from datetime import date

import pandas as pd

from src.pessoal.armazenamento_sheets import disponivel, lancamento_para_linha, linha_para_lancamento
from src.pessoal.modelos import REPETICAO_FIXA, REPETICAO_PARCELADA, TIPO_DESPESA, Lancamento


def test_disponivel_e_falso_sem_secrets():
    assert disponivel() is False


def test_ida_e_volta_lancamento_simples():
    original = Lancamento(
        descricao="Aluguel",
        categoria="Moradia",
        tipo=TIPO_DESPESA,
        valor=1800.0,
        data=date(2026, 7, 10),
        usuario="Matheus",
        repeticao=REPETICAO_FIXA,
    )
    original.id = "abc123"
    linha = pd.Series(lancamento_para_linha(original))
    de_volta = linha_para_lancamento(linha)

    assert de_volta.id == "abc123"
    assert de_volta.descricao == "Aluguel"
    assert de_volta.valor == 1800.0
    assert de_volta.data == date(2026, 7, 10)
    assert de_volta.repeticao == REPETICAO_FIXA
    assert de_volta.parcela_total is None
    assert de_volta.data_fim is None
    assert de_volta.observacao == ""


def test_ida_e_volta_lancamento_parcelado_com_observacao():
    original = Lancamento(
        descricao="Notebook",
        categoria="Outras despesas",
        tipo=TIPO_DESPESA,
        valor=300.0,
        data=date(2026, 6, 1),
        usuario="Walkiria",
        repeticao=REPETICAO_PARCELADA,
        parcela_total=10,
        observacao="Comprado na Black Friday",
    )
    original.id = "xyz999"
    linha = pd.Series(lancamento_para_linha(original))
    de_volta = linha_para_lancamento(linha)

    assert de_volta.parcela_total == 10
    assert de_volta.observacao == "Comprado na Black Friday"


def test_linha_vazia_em_campos_opcionais_vira_none():
    linha = pd.Series(
        {
            "id": "1",
            "descricao": "Mercado",
            "categoria": "Alimentação",
            "tipo": TIPO_DESPESA,
            "valor": 100.0,
            "data": "2026-07-03",
            "usuario": "Matheus",
            "repeticao": "unica",
            "parcela_total": "",
            "ativa": True,
            "data_fim": "",
            "observacao": "",
        }
    )
    lancamento = linha_para_lancamento(linha)
    assert lancamento.parcela_total is None
    assert lancamento.data_fim is None
    assert lancamento.observacao == ""
