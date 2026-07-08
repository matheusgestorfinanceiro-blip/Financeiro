"""Persistência dos lançamentos em SQLite (arquivo compartilhado por quem roda o app)."""
import os
import sqlite3
from datetime import date

from src.pessoal.modelos import REPETICAO_UNICA, Lancamento

CAMINHO_BANCO_PADRAO = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "pessoal", "financeiro.db"
)

_CRIAR_TABELA = """
CREATE TABLE IF NOT EXISTS lancamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT NOT NULL,
    categoria TEXT NOT NULL,
    tipo TEXT NOT NULL,
    valor REAL NOT NULL,
    data TEXT NOT NULL,
    usuario TEXT NOT NULL,
    repeticao TEXT NOT NULL DEFAULT 'unica',
    parcela_total INTEGER,
    ativa INTEGER NOT NULL DEFAULT 1,
    data_fim TEXT,
    observacao TEXT DEFAULT ''
)
"""


def conectar(caminho_banco: str = CAMINHO_BANCO_PADRAO) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(caminho_banco), exist_ok=True)
    conexao = sqlite3.connect(caminho_banco, check_same_thread=False)
    conexao.row_factory = sqlite3.Row
    conexao.execute(_CRIAR_TABELA)
    conexao.commit()
    return conexao


def _linha_para_lancamento(linha: sqlite3.Row) -> Lancamento:
    return Lancamento(
        id=linha["id"],
        descricao=linha["descricao"],
        categoria=linha["categoria"],
        tipo=linha["tipo"],
        valor=linha["valor"],
        data=date.fromisoformat(linha["data"]),
        usuario=linha["usuario"],
        repeticao=linha["repeticao"],
        parcela_total=linha["parcela_total"],
        ativa=bool(linha["ativa"]),
        data_fim=date.fromisoformat(linha["data_fim"]) if linha["data_fim"] else None,
        observacao=linha["observacao"] or "",
    )


def inserir(conexao: sqlite3.Connection, lancamento: Lancamento) -> int:
    cursor = conexao.execute(
        """INSERT INTO lancamentos
           (descricao, categoria, tipo, valor, data, usuario, repeticao,
            parcela_total, ativa, data_fim, observacao)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            lancamento.descricao,
            lancamento.categoria,
            lancamento.tipo,
            lancamento.valor,
            lancamento.data.isoformat(),
            lancamento.usuario,
            lancamento.repeticao,
            lancamento.parcela_total,
            int(lancamento.ativa),
            lancamento.data_fim.isoformat() if lancamento.data_fim else None,
            lancamento.observacao,
        ),
    )
    conexao.commit()
    return cursor.lastrowid


def listar_todos(conexao: sqlite3.Connection) -> list[Lancamento]:
    linhas = conexao.execute("SELECT * FROM lancamentos ORDER BY data DESC, id DESC").fetchall()
    return [_linha_para_lancamento(linha) for linha in linhas]


def excluir(conexao: sqlite3.Connection, id_lancamento: int) -> None:
    conexao.execute("DELETE FROM lancamentos WHERE id = ?", (id_lancamento,))
    conexao.commit()


def atualizar_ativa(conexao: sqlite3.Connection, id_lancamento: int, ativa: bool) -> None:
    conexao.execute(
        "UPDATE lancamentos SET ativa = ? WHERE id = ?", (int(ativa), id_lancamento)
    )
    conexao.commit()


def encerrar_fixa(conexao: sqlite3.Connection, id_lancamento: int, data_fim: date) -> None:
    """Marca a data em que um lançamento fixo deixa de se repetir (sem apagar o histórico)."""
    conexao.execute(
        "UPDATE lancamentos SET data_fim = ? WHERE id = ? AND repeticao != ?",
        (data_fim.isoformat(), id_lancamento, REPETICAO_UNICA),
    )
    conexao.commit()
