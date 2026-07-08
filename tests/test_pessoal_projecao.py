from datetime import date

from src.pessoal.modelos import (
    REPETICAO_FIXA,
    REPETICAO_PARCELADA,
    REPETICAO_UNICA,
    TIPO_DESPESA,
    TIPO_RECEITA,
    Lancamento,
)
from src.pessoal.projecao import lancamentos_do_mes, ocorrencia_no_mes, proximos_meses


def _l(id_, **kwargs):
    base = dict(
        descricao="teste",
        categoria="Outras despesas",
        tipo=TIPO_DESPESA,
        valor=100.0,
        data=date(2026, 1, 10),
        usuario="Matheus",
        repeticao=REPETICAO_UNICA,
    )
    base.update(kwargs)
    lanc = Lancamento(**base)
    lanc.id = id_
    return lanc


def test_unica_so_aparece_no_proprio_mes():
    lanc = _l(1, data=date(2026, 3, 5))
    assert ocorrencia_no_mes(lanc, 2026, 3) is not None
    assert ocorrencia_no_mes(lanc, 2026, 4) is None
    assert ocorrencia_no_mes(lanc, 2026, 2) is None


def test_fixa_repete_todo_mes_a_partir_do_inicio():
    lanc = _l(1, repeticao=REPETICAO_FIXA, data=date(2026, 1, 5))
    assert ocorrencia_no_mes(lanc, 2025, 12) is None
    assert ocorrencia_no_mes(lanc, 2026, 1) is not None
    assert ocorrencia_no_mes(lanc, 2026, 6) is not None
    assert ocorrencia_no_mes(lanc, 2030, 1) is not None


def test_fixa_inativa_nao_aparece():
    lanc = _l(1, repeticao=REPETICAO_FIXA, data=date(2026, 1, 5), ativa=False)
    assert ocorrencia_no_mes(lanc, 2026, 2) is None


def test_fixa_respeita_data_fim():
    lanc = _l(1, repeticao=REPETICAO_FIXA, data=date(2026, 1, 5), data_fim=date(2026, 3, 1))
    assert ocorrencia_no_mes(lanc, 2026, 3) is not None
    assert ocorrencia_no_mes(lanc, 2026, 4) is None


def test_parcelada_aparece_apenas_durante_as_parcelas():
    lanc = _l(1, repeticao=REPETICAO_PARCELADA, data=date(2026, 1, 10), parcela_total=3)
    assert ocorrencia_no_mes(lanc, 2025, 12) is None
    oc_jan = ocorrencia_no_mes(lanc, 2026, 1)
    oc_fev = ocorrencia_no_mes(lanc, 2026, 2)
    oc_mar = ocorrencia_no_mes(lanc, 2026, 3)
    assert oc_jan.parcela_atual == 1
    assert oc_fev.parcela_atual == 2
    assert oc_mar.parcela_atual == 3
    assert ocorrencia_no_mes(lanc, 2026, 4) is None


def test_dia_clampado_em_mes_curto():
    lanc = _l(1, repeticao=REPETICAO_FIXA, data=date(2026, 1, 31))
    oc_fev = ocorrencia_no_mes(lanc, 2026, 2)
    assert oc_fev.data == date(2026, 2, 28)


def test_lancamentos_do_mes_combina_tipos():
    fixa = _l(1, repeticao=REPETICAO_FIXA, data=date(2026, 1, 1), tipo=TIPO_RECEITA, valor=11000)
    unica = _l(2, data=date(2026, 3, 15), valor=50)
    parcelada = _l(3, repeticao=REPETICAO_PARCELADA, data=date(2026, 2, 1), parcela_total=2, valor=200)
    resultado = lancamentos_do_mes([fixa, unica, parcelada], 2026, 3)
    descricoes_valores = {(o.lancamento_id, o.valor) for o in resultado}
    assert (1, 11000) in descricoes_valores
    assert (2, 50) in descricoes_valores
    assert (3, 200) in descricoes_valores  # 2ª e última parcela cai em março
    resultado_abril = lancamentos_do_mes([fixa, unica, parcelada], 2026, 4)
    assert 3 not in {o.lancamento_id for o in resultado_abril}


def test_proximos_meses_cruza_ano():
    assert proximos_meses(2026, 11, 4) == [(2026, 11), (2026, 12), (2027, 1), (2027, 2)]
