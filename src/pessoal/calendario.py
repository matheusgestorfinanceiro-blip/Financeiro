"""Monta a grade de um calendário mensal (domingo a sábado)."""
import calendar as _calendar

NOMES_MESES = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
DIAS_SEMANA = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]


def semanas_do_mes(ano: int, mes: int) -> list[list[int]]:
    """Semanas do mês (domingo a sábado); 0 marca dias fora do mês."""
    calendario = _calendar.Calendar(firstweekday=6)
    return calendario.monthdayscalendar(ano, mes)


def mes_anterior(ano: int, mes: int) -> tuple[int, int]:
    return (ano - 1, 12) if mes == 1 else (ano, mes - 1)


def mes_seguinte(ano: int, mes: int) -> tuple[int, int]:
    return (ano + 1, 1) if mes == 12 else (ano, mes + 1)
