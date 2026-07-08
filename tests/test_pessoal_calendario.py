from src.pessoal.calendario import mes_anterior, mes_seguinte, semanas_do_mes


def test_mes_anterior_cruza_ano():
    assert mes_anterior(2026, 1) == (2025, 12)
    assert mes_anterior(2026, 7) == (2026, 6)


def test_mes_seguinte_cruza_ano():
    assert mes_seguinte(2026, 12) == (2027, 1)
    assert mes_seguinte(2026, 7) == (2026, 8)


def test_semanas_do_mes_cobre_todos_os_dias():
    semanas = semanas_do_mes(2026, 7)
    dias = [dia for semana in semanas for dia in semana if dia != 0]
    assert dias == list(range(1, 32))
    assert all(len(semana) == 7 for semana in semanas)
