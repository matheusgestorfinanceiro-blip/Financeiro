import pandas as pd
import pytest

from src.calculo.previsao import gerar_previsao
from src.models.schema import AjusteManual, DadosDemonstrativo, DadosFormulario, DadosInadimplencia


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
        # Concentrada em só 2 dos 12 meses (não uniforme), para ser classificada
        # como "extraordinaria" pelo coeficiente de variação (veja src/calculo/analise.py) -
        # imita o comportamento real de juros/multas, que não ocorrem todo mês.
        valores_juros = {m: 0.0 for m in meses}
        valores_juros[meses[0]] = outras_receitas * 0.6
        valores_juros[meses[1]] = outras_receitas * 0.4
        receitas.append({"categoria": "Juros", **valores_juros, "total": outras_receitas})
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
        periodo="Janeiro/2026 a Dezembro/2026",
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


def test_reajuste_correto_mesmo_sem_a_palavra_rateio_na_receita():
    # A receita ordinária deve ser identificada pela regularidade mensal
    # (valor uniforme nos 12 meses), não por conter a palavra "rateio" no nome.
    meses = [f"Mes{i}" for i in range(1, 13)]
    df_despesas = pd.DataFrame(
        [
            {"categoria_pai": "Categoria A", "subcategoria": "Item 1", **{m: 1000.0 / 12 for m in meses}, "total": 1000.0},
        ]
    )
    df_receitas = pd.DataFrame(
        [
            {"categoria": "Taxa Condominial", **{m: 800.0 / 12 for m in meses}, "total": 800.0},
        ]
    )
    demonstrativo = DadosDemonstrativo(
        condominio="Condomínio Teste",
        meses=meses,
        df_receitas=df_receitas,
        df_despesas=df_despesas,
        total_receitas=800.0,
        total_despesas=1000.0,
    )
    formulario = _formulario()
    resultado = gerar_previsao(demonstrativo, None, formulario)
    # (1000 - 800) / 800 = 0.25 - não pode explodir só porque o nome não contém "rateio"
    assert resultado.percentual_reajuste_automatico == pytest.approx(0.25)
    assert resultado.valor_por_unidade_sugerido_pelo_sistema is None or resultado.valor_por_unidade_sugerido_pelo_sistema >= 0


def test_despesa_ordinaria_do_reajuste_ignora_despesas_extraordinarias():
    # Uma despesa extraordinária (concentrada em poucos meses) não deve inflar
    # a base de despesa usada no cálculo automático do reajuste.
    meses = [f"Mes{i}" for i in range(1, 13)]
    valores_extraordinaria = {m: 0.0 for m in meses}
    valores_extraordinaria[meses[0]] = 5000.0
    df_despesas = pd.DataFrame(
        [
            {"categoria_pai": "Categoria A", "subcategoria": "Item Ordinario", **{m: 1000.0 / 12 for m in meses}, "total": 1000.0},
            {"categoria_pai": "Categoria B", "subcategoria": "Obra Emergencial", **valores_extraordinaria, "total": 5000.0},
        ]
    )
    df_receitas = pd.DataFrame(
        [
            {"categoria": "Rateio Mensal - Taxa de Condomínio", **{m: 1000.0 / 12 for m in meses}, "total": 1000.0},
        ]
    )
    demonstrativo = DadosDemonstrativo(
        condominio="Condomínio Teste",
        meses=meses,
        df_receitas=df_receitas,
        df_despesas=df_despesas,
        total_receitas=1000.0,
        total_despesas=6000.0,
    )
    formulario = _formulario()
    resultado = gerar_previsao(demonstrativo, None, formulario)
    # Despesa ordinária = 1000 (só "Item Ordinario"), igual à receita ordinária -> sem reajuste.
    assert resultado.percentual_reajuste_automatico == pytest.approx(0.0)


def test_sem_fundo_de_reserva():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(possui_fundo_reserva=False)
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.fundo_reserva_valor == pytest.approx(0.0)
    assert resultado.fundo_reserva_percentual == pytest.approx(0.0)
    assert resultado.receita_rateio_necessaria == pytest.approx(1000.0)


def test_fundo_de_reserva_percentual_resolve_equacao():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(
        possui_fundo_reserva=True, fundo_reserva_modo="percentual", fundo_reserva_valor_input=0.10
    )
    resultado = gerar_previsao(demonstrativo, None, formulario)
    # R = despesas + 0.10 * R  =>  0.90 * R = 1000  =>  R = 1111.11...
    assert resultado.receita_rateio_necessaria == pytest.approx(1000 / 0.9)
    assert resultado.fundo_reserva_valor == pytest.approx(resultado.receita_rateio_necessaria * 0.10)


def test_fundo_de_reserva_percentual_e_limitado_a_teto_defensivo():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(
        possui_fundo_reserva=True, fundo_reserva_modo="percentual", fundo_reserva_valor_input=1.5
    )
    # não deve levantar exceção, mesmo com um percentual absurdo digitado
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.fundo_reserva_percentual < 1.0
    assert resultado.receita_rateio_necessaria > 0


def test_fundo_de_reserva_valor_fixo_por_unidade():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(
        numero_unidades=10, possui_fundo_reserva=True, fundo_reserva_modo="valor_fixo", fundo_reserva_valor_input=20.0
    )
    resultado = gerar_previsao(demonstrativo, None, formulario)
    # 20 por unidade x 10 unidades = 200, somado direto (sem equação)
    assert resultado.fundo_reserva_valor == pytest.approx(200.0)
    assert resultado.receita_rateio_necessaria == pytest.approx(1200.0)


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


def test_gerar_previsao_preenche_campos_do_relatorio_final():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario()
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.receitas_classificadas is not None
    assert "classificacao" in resultado.receitas_classificadas.columns
    assert resultado.despesas_classificadas is not None
    assert "classificacao" in resultado.despesas_classificadas.columns
    assert resultado.concentracao_inadimplencia is not None
    assert resultado.concentracao_inadimplencia.empty
    assert resultado.mes_pico_inadimplencia is None
    assert resultado.data_geracao != ""


def test_gerar_previsao_identifica_pico_de_inadimplencia():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario()
    unidades = pd.DataFrame(
        [
            {"unidade": "AP 01", "competencia": "01/2026", "total": 100.0},
            {"unidade": "AP 02", "competencia": "02/2026", "total": 900.0},
        ]
    )
    inadimplencia = DadosInadimplencia(
        condominio="Condomínio Teste",
        unidades=unidades,
        qtd_unidades_inadimplentes=2,
        percentual_inadimplencia=0.2,
        total_principal=0.0,
        total_geral=1000.0,
    )
    resultado = gerar_previsao(demonstrativo, inadimplencia, formulario)
    assert resultado.mes_pico_inadimplencia == "02/2026"
