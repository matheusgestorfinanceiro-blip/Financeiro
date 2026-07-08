from datetime import date

from src.pessoal.analise import historico_mensal, previsao_futura, resumir_mes
from src.pessoal.modelos import REPETICAO_FIXA, REPETICAO_UNICA, TIPO_DESPESA, TIPO_RECEITA, Lancamento


def _lancamentos_exemplo():
    salario = Lancamento(
        descricao="Salário",
        categoria="Salário",
        tipo=TIPO_RECEITA,
        valor=11000.0,
        data=date(2026, 1, 5),
        usuario="Matheus",
        repeticao=REPETICAO_FIXA,
    )
    salario.id = 1
    salario_esposa = Lancamento(
        descricao="Salário esposa",
        categoria="Salário",
        tipo=TIPO_RECEITA,
        valor=1600.0,
        data=date(2026, 1, 5),
        usuario="Esposa",
        repeticao=REPETICAO_FIXA,
    )
    salario_esposa.id = 2
    aluguel = Lancamento(
        descricao="Aluguel",
        categoria="Moradia",
        tipo=TIPO_DESPESA,
        valor=2000.0,
        data=date(2026, 1, 10),
        usuario="Matheus",
        repeticao=REPETICAO_FIXA,
    )
    aluguel.id = 3
    mercado = Lancamento(
        descricao="Mercado",
        categoria="Alimentação",
        tipo=TIPO_DESPESA,
        valor=500.0,
        data=date(2026, 7, 3),
        usuario="Esposa",
        repeticao=REPETICAO_UNICA,
    )
    mercado.id = 4
    return [salario, salario_esposa, aluguel, mercado]


def test_resumir_mes_calcula_totais_e_saldo():
    todos = _lancamentos_exemplo()
    resumo = resumir_mes(todos, 2026, 7)
    assert resumo.total_receitas == 12600.0
    assert resumo.total_despesas == 2500.0
    assert resumo.saldo == 10100.0
    assert resumo.por_categoria_despesa["Alimentação"] == 500.0
    assert resumo.por_usuario["Matheus"][TIPO_RECEITA] == 11000.0
    assert resumo.por_usuario["Esposa"][TIPO_DESPESA] == 500.0


def test_resumir_mes_sem_variavel_nao_conta_no_outro_mes():
    todos = _lancamentos_exemplo()
    resumo = resumir_mes(todos, 2026, 6)
    assert resumo.total_despesas == 2000.0


def test_historico_mensal_retorna_quantidade_certa_em_ordem():
    todos = _lancamentos_exemplo()
    historico = historico_mensal(todos, 2026, 7, quantidade_meses_passados=3)
    assert [(r.ano, r.mes) for r in historico] == [(2026, 5), (2026, 6), (2026, 7)]


def test_previsao_futura_inclui_fixos():
    todos = _lancamentos_exemplo()
    previsao = previsao_futura(todos, 2026, 8, quantidade_meses=3)
    assert [(r.ano, r.mes) for r in previsao] == [(2026, 8), (2026, 9), (2026, 10)]
    for r in previsao:
        assert r.total_receitas == 12600.0
        assert r.total_despesas == 2000.0
