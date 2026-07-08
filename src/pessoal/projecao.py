"""Projeta, para qualquer mês (passado, atual ou futuro), quais lançamentos ocorrem.

Um lançamento único só aparece no seu próprio mês. Um lançamento fixo aparece
todo mês (enquanto ativo). Um lançamento parcelado aparece por N meses
seguidos a partir da primeira parcela.
"""
import calendar
from dataclasses import dataclass
from datetime import date

from src.pessoal.modelos import REPETICAO_FIXA, REPETICAO_PARCELADA, REPETICAO_UNICA, Lancamento


@dataclass
class Ocorrencia:
    """Uma ocorrência concreta de um lançamento em um mês específico."""

    lancamento_id: int
    descricao: str
    categoria: str
    tipo: str
    valor: float
    data: date
    usuario: str
    repeticao: str
    parcela_atual: int | None = None
    parcela_total: int | None = None
    observacao: str = ""

    @property
    def descricao_completa(self) -> str:
        if self.repeticao == REPETICAO_PARCELADA and self.parcela_total:
            return f"{self.descricao} ({self.parcela_atual}/{self.parcela_total})"
        return self.descricao


def _dia_no_mes(dia: int, ano: int, mes: int) -> int:
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return min(dia, ultimo_dia)


def _meses_entre(inicio: date, ano: int, mes: int) -> int:
    """Quantidade de meses de diferença entre a data inicial e (ano, mes)."""
    return (ano - inicio.year) * 12 + (mes - inicio.month)


def ocorrencia_no_mes(lancamento: Lancamento, ano: int, mes: int) -> Ocorrencia | None:
    """Retorna a ocorrência do lançamento no mês pedido, ou None se não ocorrer."""
    if lancamento.repeticao == REPETICAO_UNICA:
        if lancamento.data.year == ano and lancamento.data.month == mes:
            return _para_ocorrencia(lancamento, lancamento.data)
        return None

    if lancamento.repeticao == REPETICAO_FIXA:
        if not lancamento.ativa:
            return None
        if _meses_entre(lancamento.data, ano, mes) < 0:
            return None
        if lancamento.data_fim is not None and _meses_entre(lancamento.data_fim, ano, mes) > 0:
            return None
        dia = _dia_no_mes(lancamento.data.day, ano, mes)
        return _para_ocorrencia(lancamento, date(ano, mes, dia))

    if lancamento.repeticao == REPETICAO_PARCELADA:
        total = lancamento.parcela_total or 1
        indice = _meses_entre(lancamento.data, ano, mes)
        if 0 <= indice < total:
            dia = _dia_no_mes(lancamento.data.day, ano, mes)
            return _para_ocorrencia(lancamento, date(ano, mes, dia), parcela_atual=indice + 1)
        return None

    return None


def _para_ocorrencia(lancamento: Lancamento, data: date, parcela_atual: int | None = None) -> Ocorrencia:
    return Ocorrencia(
        lancamento_id=lancamento.id,
        descricao=lancamento.descricao,
        categoria=lancamento.categoria,
        tipo=lancamento.tipo,
        valor=lancamento.valor,
        data=data,
        usuario=lancamento.usuario,
        repeticao=lancamento.repeticao,
        parcela_atual=parcela_atual,
        parcela_total=lancamento.parcela_total,
        observacao=lancamento.observacao,
    )


def lancamentos_do_mes(todos: list[Lancamento], ano: int, mes: int) -> list[Ocorrencia]:
    """Todas as ocorrências (reais + projetadas) de um mês, ordenadas por data."""
    ocorrencias = []
    for lancamento in todos:
        ocorrencia = ocorrencia_no_mes(lancamento, ano, mes)
        if ocorrencia is not None:
            ocorrencias.append(ocorrencia)
    return sorted(ocorrencias, key=lambda o: (o.data, o.descricao))


def proximos_meses(ano: int, mes: int, quantidade: int) -> list[tuple[int, int]]:
    """Lista de (ano, mes) começando em (ano, mes), com `quantidade` elementos."""
    resultado = []
    for i in range(quantidade):
        total = (mes - 1) + i
        resultado.append((ano + total // 12, total % 12 + 1))
    return resultado
