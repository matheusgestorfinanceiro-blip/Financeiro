from datetime import date

from src.pessoal.armazenamento import conectar, encerrar_fixa, excluir, inserir, listar_todos
from src.pessoal.modelos import REPETICAO_FIXA, TIPO_DESPESA, Lancamento


def test_inserir_e_listar(tmp_path):
    conexao = conectar(str(tmp_path / "financeiro.db"))
    lanc = Lancamento(
        descricao="Internet",
        categoria="Contas (água/luz/internet)",
        tipo=TIPO_DESPESA,
        valor=120.0,
        data=date(2026, 1, 15),
        usuario="Matheus",
        repeticao=REPETICAO_FIXA,
    )
    id_criado = inserir(conexao, lanc)
    todos = listar_todos(conexao)
    assert len(todos) == 1
    assert todos[0].id == id_criado
    assert todos[0].descricao == "Internet"
    assert todos[0].data == date(2026, 1, 15)


def test_encerrar_fixa_define_data_fim(tmp_path):
    conexao = conectar(str(tmp_path / "financeiro.db"))
    lanc = Lancamento(
        descricao="Academia",
        categoria="Saúde",
        tipo=TIPO_DESPESA,
        valor=100.0,
        data=date(2026, 1, 1),
        usuario="Matheus",
        repeticao=REPETICAO_FIXA,
    )
    id_criado = inserir(conexao, lanc)
    encerrar_fixa(conexao, id_criado, date(2026, 5, 1))
    todos = listar_todos(conexao)
    assert todos[0].data_fim == date(2026, 5, 1)


def test_excluir_remove_lancamento(tmp_path):
    conexao = conectar(str(tmp_path / "financeiro.db"))
    lanc = Lancamento(
        descricao="Cinema",
        categoria="Lazer",
        tipo=TIPO_DESPESA,
        valor=40.0,
        data=date(2026, 1, 1),
        usuario="Matheus",
    )
    id_criado = inserir(conexao, lanc)
    excluir(conexao, id_criado)
    assert listar_todos(conexao) == []
