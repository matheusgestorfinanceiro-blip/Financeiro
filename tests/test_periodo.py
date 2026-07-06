from src.calculo.periodo import limpar_nome_condominio, sugerir_periodo


def test_limpar_nome_condominio_remove_codigo_e_sufixo():
    assert limpar_nome_condominio("W015A CONDOMINIO PRAIA DE ITACIMIRIM (42)") == "CONDOMINIO PRAIA DE ITACIMIRIM"


def test_limpar_nome_condominio_sem_sufixo():
    assert limpar_nome_condominio("W003A CONDOMINIO EXEMPLO") == "CONDOMINIO EXEMPLO"


def test_limpar_nome_condominio_sem_a_palavra_condominio():
    assert limpar_nome_condominio("W020A RESIDENCIAL JARDIM DAS FLORES (10)") == "RESIDENCIAL JARDIM DAS FLORES"


def test_sugerir_periodo_calcula_proximo_ano():
    meses = ["Mai/2025", "Jun/2025", "Jul/2025", "Ago/2025", "Set/2025", "Out/2025",
              "Nov/2025", "Dez/2025", "Jan/2026", "Fev/2026", "Mar/2026", "Abr/2026"]
    assert sugerir_periodo(meses) == "Maio/2026 a Abril/2027"


def test_sugerir_periodo_lista_vazia():
    assert sugerir_periodo([]) == ""


def test_sugerir_periodo_atravessa_virada_de_ano_no_meio():
    meses = ["Out/2025", "Nov/2025", "Dez/2025", "Jan/2026", "Fev/2026", "Mar/2026",
              "Abr/2026", "Mai/2026", "Jun/2026", "Jul/2026", "Ago/2026", "Set/2026"]
    assert sugerir_periodo(meses) == "Outubro/2026 a Setembro/2027"
