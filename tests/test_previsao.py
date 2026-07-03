import pandas as pd
import pytest

from src.calculo.previsao import gerar_previsao
from src.models.schema import DadosDemonstrativo, DadosFormulario, DadosInadimplencia


def _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0, outras_receitas=0.0):
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
    df_receitas = pd.DataFrame(receitas)
    return DadosDemonstrativo(
        condominio="Condomínio Teste",
        meses=meses,
        df_receitas=df_receitas,
        df_despesas=df_despesas,
        total_receitas=total_rateio + outras_receitas,
        total_despesas=total_despesa,
    )


def _formulario(**kwargs):
    base = dict(
        nome_condominio="Condomínio Teste",
        periodo_inicio="2026-01",
        periodo_fim="2026-12",
        percentual_reajuste=0.0,
        numero_unidades=10,
        fundo_reserva_percentual=0.0,
        fundo_reserva_base="despesas",
        taxa_administracao_modo="valor_fixo",
        taxa_administracao_valor=0.0,
        rateio_tipo="igualitario",
    )
    base.update(kwargs)
    return DadosFormulario(**base)


def test_sem_reajuste_fundo_ou_taxa_rateio_igual_as_despesas():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0)
    formulario = _formulario()
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.receita_rateio_necessaria == pytest.approx(1000.0)
    assert resultado.valor_por_unidade_sem_ajuste == pytest.approx(100.0)


def test_reajuste_e_aplicado_as_despesas():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0)
    formulario = _formulario(percentual_reajuste=0.10)
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.total_despesas_previsto == pytest.approx(1100.0)
    assert resultado.receita_rateio_necessaria == pytest.approx(1100.0)


def test_taxa_administracao_valor_fixo_por_unidade():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0)
    formulario = _formulario(taxa_administracao_modo="valor_fixo", taxa_administracao_valor=20.0, numero_unidades=10)
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.taxa_administracao_valor == pytest.approx(200.0)
    assert resultado.receita_rateio_necessaria == pytest.approx(1200.0)


def test_fundo_de_reserva_sobre_despesas():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0)
    formulario = _formulario(fundo_reserva_base="despesas", fundo_reserva_percentual=0.05)
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.fundo_reserva_valor == pytest.approx(50.0)
    assert resultado.receita_rateio_necessaria == pytest.approx(1050.0)


def test_fundo_de_reserva_sobre_rateio_resolve_equacao():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0)
    formulario = _formulario(fundo_reserva_base="rateio", fundo_reserva_percentual=0.10)
    resultado = gerar_previsao(demonstrativo, None, formulario)
    # R = despesas + 0.10 * R  =>  0.90 * R = 1000  =>  R = 1111.11...
    assert resultado.receita_rateio_necessaria == pytest.approx(1000 / 0.9)
    assert resultado.fundo_reserva_valor == pytest.approx(resultado.receita_rateio_necessaria * 0.10)


def test_outras_receitas_abatem_a_receita_de_rateio_necessaria():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, outras_receitas=200.0)
    formulario = _formulario()
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.total_outras_receitas_previsto == pytest.approx(200.0)
    assert resultado.receita_rateio_necessaria == pytest.approx(800.0)


def test_ajuste_por_inadimplencia_infla_o_valor_por_unidade():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0)
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
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0)
    formulario = _formulario(numero_unidades=4)
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert len(resultado.rateio_por_unidade) == 4
    assert resultado.rateio_por_unidade["valor"].sum() == pytest.approx(resultado.receita_rateio_necessaria)


def test_rateio_por_fracao_ideal():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0)
    fracoes = pd.DataFrame({"unidade": ["AP 01", "AP 02"], "fracao": [0.6, 0.4]})
    formulario = _formulario(numero_unidades=2, rateio_tipo="fracao_ideal", fracoes_ideais=fracoes)
    resultado = gerar_previsao(demonstrativo, None, formulario)
    valores = dict(zip(resultado.rateio_por_unidade["unidade"], resultado.rateio_por_unidade["valor"]))
    assert valores["AP 01"] == pytest.approx(600.0)
    assert valores["AP 02"] == pytest.approx(400.0)


def test_ajuste_manual_sobrescreve_reajuste_padrao():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0)
    from src.models.schema import AjusteManual

    formulario = _formulario(
        percentual_reajuste=0.05,
        ajustes_manuais=[AjusteManual(subcategoria="Item 1", percentual_reajuste=0.50)],
    )
    resultado = gerar_previsao(demonstrativo, None, formulario)
    linha = resultado.despesas_previstas[0]
    assert linha.ajuste_manual is True
    assert linha.valor_previsto == pytest.approx(1500.0)
