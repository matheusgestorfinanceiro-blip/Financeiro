from datetime import date

from src.pessoal import repositorio
from src.pessoal.armazenamento import conectar
from src.pessoal.modelos import TIPO_DESPESA, Lancamento


def test_usa_sqlite_quando_planilha_nao_configurada():
    assert repositorio.usando_planilha() is False


def test_repositorio_delega_para_sqlite_por_padrao(tmp_path):
    conexao = conectar(str(tmp_path / "financeiro.db"))
    lancamento = Lancamento(
        descricao="Mercado",
        categoria="Alimentação",
        tipo=TIPO_DESPESA,
        valor=100.0,
        data=date(2026, 7, 3),
        usuario="Matheus",
    )
    repositorio.inserir(conexao, lancamento)
    todos = repositorio.listar_todos(conexao)
    assert len(todos) == 1
    assert todos[0].descricao == "Mercado"

    repositorio.excluir(conexao, todos[0].id)
    assert repositorio.listar_todos(conexao) == []
