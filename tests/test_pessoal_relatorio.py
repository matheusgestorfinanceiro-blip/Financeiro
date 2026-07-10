from datetime import date

from src.pessoal.modelos import (
    REPETICAO_FIXA,
    REPETICAO_PARCELADA,
    REPETICAO_UNICA,
    TIPO_DESPESA,
    TIPO_RECEITA,
    Lancamento,
)
from src.pessoal.relatorio import evolucao_mensal, ocorrencias_no_periodo, resumir_periodo


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
    salario_walkiria = Lancamento(
        descricao="Salário Walkiria",
        categoria="Salário",
        tipo=TIPO_RECEITA,
        valor=1600.0,
        data=date(2026, 1, 5),
        usuario="Walkiria",
        repeticao=REPETICAO_FIXA,
    )
    salario_walkiria.id = 2
    aluguel = Lancamento(
        descricao="Aluguel",
        categoria="Moradia",
        tipo=TIPO_DESPESA,
        valor=1800.0,
        data=date(2026, 1, 10),
        usuario="Matheus",
        repeticao=REPETICAO_FIXA,
    )
    aluguel.id = 3
    mercado_maio = Lancamento(
        descricao="Mercado",
        categoria="Alimentação",
        tipo=TIPO_DESPESA,
        valor=500.0,
        data=date(2026, 5, 3),
        usuario="Walkiria",
        repeticao=REPETICAO_UNICA,
    )
    mercado_maio.id = 4
    notebook = Lancamento(
        descricao="Notebook",
        categoria="Outras despesas",
        tipo=TIPO_DESPESA,
        valor=300.0,
        data=date(2026, 3, 1),
        usuario="Matheus",
        repeticao=REPETICAO_PARCELADA,
        parcela_total=3,
    )
    notebook.id = 5
    return [salario, salario_walkiria, aluguel, mercado_maio, notebook]


def test_ocorrencias_no_periodo_respeita_datas():
    todos = _lancamentos_exemplo()
    ocorrencias = ocorrencias_no_periodo(todos, date(2026, 1, 1), date(2026, 1, 31))
    ids = {oc.lancamento_id for oc in ocorrencias}
    assert ids == {1, 2, 3}


def test_ocorrencias_no_periodo_inclui_parcelas_em_andamento():
    todos = _lancamentos_exemplo()
    ocorrencias = ocorrencias_no_periodo(todos, date(2026, 3, 1), date(2026, 5, 31))
    parcelas = [oc for oc in ocorrencias if oc.lancamento_id == 5]
    assert len(parcelas) == 3
    assert [oc.parcela_atual for oc in parcelas] == [1, 2, 3]


def test_filtro_por_usuario():
    todos = _lancamentos_exemplo()
    ocorrencias = ocorrencias_no_periodo(
        todos, date(2026, 1, 1), date(2026, 12, 31), usuarios={"Walkiria"}
    )
    assert all(oc.usuario == "Walkiria" for oc in ocorrencias)
    assert {oc.lancamento_id for oc in ocorrencias} == {2, 4}


def test_filtro_por_categoria_e_tipo():
    todos = _lancamentos_exemplo()
    ocorrencias = ocorrencias_no_periodo(
        todos,
        date(2026, 1, 1),
        date(2026, 12, 31),
        categorias={"Moradia", "Alimentação"},
        tipos={TIPO_DESPESA},
    )
    assert {oc.lancamento_id for oc in ocorrencias} == {3, 4}


def test_resumir_periodo_calcula_totais():
    todos = _lancamentos_exemplo()
    ocorrencias = ocorrencias_no_periodo(todos, date(2026, 1, 1), date(2026, 1, 31))
    resumo = resumir_periodo(ocorrencias, date(2026, 1, 1), date(2026, 1, 31))
    assert resumo.total_receitas == 12600.0
    assert resumo.total_despesas == 1800.0
    assert resumo.saldo == 10800.0
    assert resumo.por_usuario["Matheus"][TIPO_RECEITA] == 11000.0
    assert resumo.por_categoria_despesa["Moradia"] == 1800.0


def test_evolucao_mensal_agrupa_por_mes_em_ordem():
    todos = _lancamentos_exemplo()
    ocorrencias = ocorrencias_no_periodo(todos, date(2026, 1, 1), date(2026, 5, 31))
    resumos = evolucao_mensal(ocorrencias)
    assert [(r.ano, r.mes) for r in resumos] == [(2026, 1), (2026, 2), (2026, 3), (2026, 4), (2026, 5)]
    janeiro = resumos[0]
    assert janeiro.total_receitas == 12600.0
    assert janeiro.total_despesas == 1800.0
    maio = resumos[4]
    # aluguel (fixo, 1800) + notebook parcela 3/3 (300) + mercado (500)
    assert maio.total_despesas == 2600.0
