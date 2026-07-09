"""Escolhe automaticamente onde os lançamentos são salvos.

Se a planilha do Google estiver configurada nos secrets do Streamlit
(`[connections.gsheets]`), os dados são salvos lá — o que sobrevive a
reinícios do servidor gratuito da Streamlit Cloud. Sem essa configuração
(por exemplo, rodando localmente), usa um arquivo SQLite como antes.
"""
from datetime import date

from src.pessoal import armazenamento as _sqlite
from src.pessoal.modelos import Lancamento


def usando_planilha() -> bool:
    from src.pessoal import armazenamento_sheets as _sheets

    return _sheets.disponivel()


def _backend():
    if usando_planilha():
        from src.pessoal import armazenamento_sheets as _sheets

        return _sheets
    return _sqlite


def obter_conexao():
    return _backend().conectar()


def inserir(conexao, lancamento: Lancamento):
    return _backend().inserir(conexao, lancamento)


def listar_todos(conexao) -> list[Lancamento]:
    return _backend().listar_todos(conexao)


def excluir(conexao, id_lancamento) -> None:
    _backend().excluir(conexao, id_lancamento)


def encerrar_fixa(conexao, id_lancamento, data_fim: date) -> None:
    _backend().encerrar_fixa(conexao, id_lancamento, data_fim)
