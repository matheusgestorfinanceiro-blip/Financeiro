from src.models.schema import LinhaDespesaPrevista
from src.relatorio.graficos import grafico_despesas_por_categoria_pai


class _ResultadoFalso:
    def __init__(self, despesas_previstas):
        self.despesas_previstas = despesas_previstas


def test_grafico_despesas_por_categoria_pai_agrupa_por_categoria():
    despesas = [
        LinhaDespesaPrevista(
            categoria_pai="Com Pessoal", subcategoria="Folha", valor_historico=1000.0,
            percentual_reajuste_aplicado=0.0, valor_previsto=1000.0,
        ),
        LinhaDespesaPrevista(
            categoria_pai="Manutenção", subcategoria="Elevador", valor_historico=500.0,
            percentual_reajuste_aplicado=0.0, valor_previsto=500.0,
        ),
    ]
    fig = grafico_despesas_por_categoria_pai(_ResultadoFalso(despesas))
    assert fig is not None


def test_grafico_despesas_por_categoria_pai_nao_quebra_sem_despesas():
    fig = grafico_despesas_por_categoria_pai(_ResultadoFalso([]))
    assert fig is not None
