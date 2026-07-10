from datetime import date

import pandas as pd
from gspread.exceptions import WorksheetNotFound

from src.pessoal.armazenamento_sheets import (
    COLUNAS,
    disponivel,
    inserir,
    lancamento_para_linha,
    linha_para_lancamento,
    listar_todos,
)
from src.pessoal.modelos import REPETICAO_FIXA, REPETICAO_PARCELADA, TIPO_DESPESA, TIPO_RECEITA, Lancamento


class ConexaoFalsa:
    """Simula uma GSheetsConnection: guarda os dados em memória, sem rede."""

    def __init__(self, aba_existe=True):
        self.aba_existe = aba_existe
        self.dados = pd.DataFrame(columns=COLUNAS)
        self.chamadas_create = 0

    def read(self, worksheet, ttl=0, **kwargs):
        if not self.aba_existe:
            raise WorksheetNotFound(worksheet)
        return self.dados.copy()

    def update(self, worksheet, data):
        self.dados = data.copy()

    def create(self, worksheet, data):
        self.chamadas_create += 1
        self.aba_existe = True
        self.dados = data.copy()


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


def test_cria_aba_automaticamente_quando_nao_existe():
    conexao = ConexaoFalsa(aba_existe=False)
    assert listar_todos(conexao) == []
    assert conexao.chamadas_create == 1
    assert conexao.aba_existe is True


def test_inserir_e_listar_com_aba_ja_existente():
    conexao = ConexaoFalsa(aba_existe=True)
    lancamento = Lancamento(
        descricao="Mercado",
        categoria="Alimentação",
        tipo=TIPO_DESPESA,
        valor=250.0,
        data=date(2026, 7, 9),
        usuario="Matheus",
    )
    novo_id = inserir(conexao, lancamento)
    todos = listar_todos(conexao)
    assert len(todos) == 1
    assert todos[0].id == novo_id
    assert todos[0].descricao == "Mercado"
    assert todos[0].valor == 250.0


def test_inserir_cria_aba_se_planilha_estiver_totalmente_vazia():
    conexao = ConexaoFalsa(aba_existe=False)
    lancamento = Lancamento(
        descricao="Salário",
        categoria="Salário",
        tipo=TIPO_RECEITA,
        valor=11000.0,
        data=date(2026, 7, 5),
        usuario="Matheus",
        repeticao=REPETICAO_FIXA,
    )
    inserir(conexao, lancamento)
    assert conexao.chamadas_create == 1
    todos = listar_todos(conexao)
    assert len(todos) == 1
    assert todos[0].descricao == "Salário"
