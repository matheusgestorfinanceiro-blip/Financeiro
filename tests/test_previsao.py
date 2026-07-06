import pandas as pd
import pytest

from src.calculo.previsao import gerar_previsao
from src.models.schema import AjusteManual, DadosDemonstrativo, DadosFormulario, DadosInadimplencia


def _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0, outras_receitas=0.0, fundo_reserva=0.0):
    meses = [f"Mes{i}" for i in range(1, 13)]
    df_despesas = pd.DataFrame(
        [
            {"categoria_pai": "Categoria A", "subcategoria": "Item 1", **{m: total_despesa / 12 for m in meses}, "total": total_despesa},
        ]
    )
    receitas = [
        {"categoria": "Rateio Mensal - Taxa de Condomínio", **{m: total_rateio / 12 for m in meses}, "total": total_rateio},
    ]
    if outras_receitas:
        receitas.append({"categoria": "Juros", **{m: outras_receitas / 12 for m in meses}, "total": outras_receitas})
    if fundo_reserva:
        receitas.append({"categoria": "Fundo de Reserva", **{m: fundo_reserva / 12 for m in meses}, "total": fundo_reserva})
    df_receitas = pd.DataFrame(receitas)
    return DadosDemonstrativo(
        condominio="Condomínio Teste",
        meses=meses,
        df_receitas=df_receitas,
        df_despesas=df_despesas,
        total_receitas=total_rateio + outras_receitas + fundo_reserva,
        total_despesas=total_despesa,
    )


def _formulario(**kwargs):
    base = dict(
        nome_condominio="Condomínio Teste",
        periodo_inicio="2026-01",
        periodo_fim="2026-12",
        numero_unidades=10,
        rateio_tipo="igualitario",
    )
    base.update(kwargs)
    return DadosFormulario(**base)


def test_sem_reajuste_quando_receita_cobre_a_despesa():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario()
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.percentual_reajuste_automatico == pytest.approx(0.0)
    assert resultado.receita_rateio_necessaria == pytest.approx(1000.0)
    assert resultado.valor_por_unidade_sem_ajuste == pytest.approx(100.0)


def test_reajuste_automatico_quando_despesa_maior_que_receita():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=800.0)
    formulario = _formulario()
    resultado = gerar_previsao(demonstrativo, None, formulario)
    # (1000 - 800) / 800 = 0.25
    assert resultado.percentual_reajuste_automatico == pytest.approx(0.25)
    assert resultado.total_despesas_previsto == pytest.approx(1250.0)
    assert resultado.receita_rateio_necessaria == pytest.approx(1250.0)


def test_fundo_de_reserva_automatico_quando_linha_existe():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0, fundo_reserva=100.0)
    formulario = _formulario()
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.fundo_reserva_linha_encontrada is True
    # 100 / 1000 = 0.10
    assert resultado.fundo_reserva_percentual_automatico == pytest.approx(0.10)
    # R = despesas + 0.10 * R  =>  0.90 * R = 1000  =>  R = 1111.11...
    assert resultado.receita_rateio_necessaria == pytest.approx(1000 / 0.9)
    assert resultado.fundo_reserva_valor == pytest.approx(resultado.receita_rateio_necessaria * 0.10)


def test_fundo_de_reserva_zero_quando_linha_nao_existe():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario()
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.fundo_reserva_linha_encontrada is False
    assert resultado.fundo_reserva_percentual_automatico == pytest.approx(0.0)
    assert resultado.fundo_reserva_valor == pytest.approx(0.0)


def test_outras_receitas_abatem_a_receita_de_rateio_necessaria():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0, outras_receitas=200.0)
    formulario = _formulario()
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.total_outras_receitas_previsto == pytest.approx(200.0)
    assert resultado.receita_rateio_necessaria == pytest.approx(800.0)


def test_ajuste_por_inadimplencia_infla_o_valor_por_unidade():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(numero_unidades=10)
    inadimplencia = DadosInadimplencia(
        condominio="Condomínio Teste",
        unidades=pd.DataFrame(),
        qtd_unidades_inadimplentes=2,
        percentual_inadimplencia=0.20,
        total_principal=0.0,
        total_geral=0.0,
    )
    resultado = gerar_previsao(demonstrativo, inadimplencia, formulario)
    assert resultado.valor_por_unidade_sem_ajuste == pytest.approx(100.0)
    # 100 / (1 - 0.20) = 125
    assert resultado.valor_por_unidade_com_inadimplencia == pytest.approx(125.0)


def test_rateio_igualitario_divide_entre_as_unidades():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(numero_unidades=4)
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert len(resultado.rateio_por_unidade) == 4
    assert resultado.rateio_por_unidade["valor"].sum() == pytest.approx(resultado.receita_rateio_necessaria)


def test_rateio_por_fracao_ideal():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    fracoes = pd.DataFrame({"unidade": ["AP 01", "AP 02"], "fracao": [0.6, 0.4]})
    formulario = _formulario(numero_unidades=2, rateio_tipo="fracao_ideal", fracoes_ideais=fracoes)
    resultado = gerar_previsao(demonstrativo, None, formulario)
    valores = dict(zip(resultado.rateio_por_unidade["unidade"], resultado.rateio_por_unidade["valor"]))
    assert valores["AP 01"] == pytest.approx(600.0)
    assert valores["AP 02"] == pytest.approx(400.0)


def test_ajuste_manual_sobrescreve_reajuste_automatico():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=800.0)
    formulario = _formulario(
        ajustes_manuais=[AjusteManual(subcategoria="Item 1", percentual_reajuste=0.50)],
    )
    resultado = gerar_previsao(demonstrativo, None, formulario)
    linha = resultado.despesas_previstas[0]
    assert linha.ajuste_manual is True
    assert linha.valor_previsto == pytest.approx(1500.0)


def test_valor_unico_por_unidade_substitui_calculo_automatico():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(numero_unidades=10, valor_unico_por_unidade=150.0)
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.valor_por_unidade_sem_ajuste == pytest.approx(150.0)
    assert resultado.receita_rateio_necessaria == pytest.approx(1500.0)
    # o sistema calcularia 100 (despesa=receita, sem reajuste/fundo) - mostrado como referência
    assert resultado.valor_por_unidade_sugerido_pelo_sistema == pytest.approx(100.0)


def test_sem_valor_unico_nao_ha_sugestao_de_referencia():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(numero_unidades=10)
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.valor_por_unidade_sugerido_pelo_sistema is None
