import pandas as pd
import pytest

from src.calculo.previsao import gerar_previsao
from src.models.schema import (
    AjusteManual,
    ConfiguracaoArrecadacao,
    DadosDemonstrativo,
    DadosFormulario,
    DadosInadimplencia,
    TipoUnidade,
)


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


def _config_igual(valor_unico):
    return ConfiguracaoArrecadacao(modo="igual", valor_unico=valor_unico)


def _formulario(**kwargs):
    base = dict(
        nome_condominio="Condomínio Teste",
        periodo="Janeiro/2026 a Dezembro/2026",
        numero_unidades=10,
        configuracao_rateio=_config_igual(100.0),
    )
    base.update(kwargs)
    return DadosFormulario(**base)


def test_sem_reajuste_quando_receita_cobre_a_despesa():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario()
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.percentual_reajuste_automatico == pytest.approx(0.0)
    assert resultado.receita_rateio_necessaria == pytest.approx(1000.0)


def test_reajuste_automatico_quando_despesa_maior_que_receita():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=800.0)
    formulario = _formulario()
    resultado = gerar_previsao(demonstrativo, None, formulario)
    # (1000 - 800) / 800 = 0.25
    assert resultado.percentual_reajuste_automatico == pytest.approx(0.25)
    assert resultado.total_despesas_previsto == pytest.approx(1250.0)


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
    assert resultado.receita_rateio_necessaria == pytest.approx(1000.0)


def test_fundo_de_reserva_modo_igual():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(
        numero_unidades=10,
        possui_fundo_reserva=True,
        configuracao_fundo_reserva=_config_igual(20.0),
    )
    resultado = gerar_previsao(demonstrativo, None, formulario)
    # 20 por unidade x 10 unidades = 200
    assert resultado.fundo_reserva_valor == pytest.approx(200.0)


def test_outras_receitas_nao_afetam_a_receita_de_rateio_configurada():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0, outras_receitas=200.0)
    formulario = _formulario()
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.total_outras_receitas_previsto == pytest.approx(200.0)
    # a receita de rateio agora vem diretamente da configuração do usuário (100 x 10 unidades)
    assert resultado.receita_rateio_necessaria == pytest.approx(1000.0)


def test_ajuste_por_inadimplencia_infla_o_total_por_unidade():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(numero_unidades=10, configuracao_rateio=_config_igual(100.0))
    inadimplencia = DadosInadimplencia(
        condominio="Condomínio Teste",
        unidades=pd.DataFrame(),
        qtd_unidades_inadimplentes=2,
        percentual_inadimplencia=0.20,
        total_principal=0.0,
        total_geral=0.0,
    )
    resultado = gerar_previsao(demonstrativo, inadimplencia, formulario)
    # 100 / (1 - 0.20) = 125
    assert resultado.valores_por_unidade["total"].iloc[0] == pytest.approx(125.0)


def test_rateio_igualitario_divide_entre_as_unidades():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(numero_unidades=4, configuracao_rateio=_config_igual(250.0))
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert len(resultado.valores_por_unidade) == 4
    assert resultado.valores_por_unidade["rateio"].sum() == pytest.approx(resultado.receita_rateio_necessaria)


def test_rateio_por_fracao_ideal():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    fracoes = pd.DataFrame({"unidade": ["AP 01", "AP 02"], "fracao": [0.6, 0.4]})
    config = ConfiguracaoArrecadacao(modo="fracao_ideal", valor_total_mensal=1000.0, fracoes=fracoes)
    formulario = _formulario(numero_unidades=2, configuracao_rateio=config)
    resultado = gerar_previsao(demonstrativo, None, formulario)
    valores = dict(zip(resultado.valores_por_unidade["unidade"], resultado.valores_por_unidade["rateio"]))
    assert valores["AP 01"] == pytest.approx(600.0)
    assert valores["AP 02"] == pytest.approx(400.0)


def test_rateio_por_tipos_de_unidade():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    tipos = [
        TipoUnidade(nome="Apartamento", quantidade=8, valor=100.0),
        TipoUnidade(nome="Cobertura", quantidade=2, valor=180.0),
    ]
    config = ConfiguracaoArrecadacao(modo="tipos", tipos=tipos)
    formulario = _formulario(numero_unidades=10, configuracao_rateio=config)
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert len(resultado.valores_por_unidade) == 10
    # 8 x 100 + 2 x 180 = 1160
    assert resultado.receita_rateio_necessaria == pytest.approx(1160.0)


def test_ajuste_manual_sobrescreve_reajuste_automatico():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=800.0)
    formulario = _formulario(
        ajustes_manuais=[AjusteManual(subcategoria="Item 1", percentual_reajuste=0.50)],
    )
    resultado = gerar_previsao(demonstrativo, None, formulario)
    linha = resultado.despesas_previstas[0]
    assert linha.ajuste_manual is True
    assert linha.valor_previsto == pytest.approx(1500.0)


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


def test_arrecadacao_prevista_mensal_e_a_soma_do_rateio_configurado():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(numero_unidades=10, configuracao_rateio=_config_igual(150.0))
    resultado = gerar_previsao(demonstrativo, None, formulario)
    # Todo modo de ConfiguracaoArrecadacao já representa um valor mensal: 150 x 10 = 1500/mês.
    assert resultado.arrecadacao_prevista_mensal == pytest.approx(1500.0)


def test_outras_arrecadacoes_somam_no_total_por_unidade():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    config_agua = ConfiguracaoArrecadacao(modo="igual", valor_unico=10.0)
    formulario = _formulario(
        numero_unidades=10,
        configuracao_rateio=_config_igual(100.0),
        outras_arrecadacoes=[("Rateio de agua", config_agua)],
    )
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.total_outras_arrecadacoes_previsto == pytest.approx(100.0)
    assert resultado.outras_arrecadacoes_detalhe == [("Rateio de agua", pytest.approx(100.0))]
    assert resultado.valores_por_unidade["Rateio de agua"].sum() == pytest.approx(100.0)
    # total por unidade = rateio (100) + fundo (0) + agua (10)
    assert resultado.valores_por_unidade["total"].iloc[0] == pytest.approx(110.0)


def test_fundo_de_reserva_igual_reaproveita_nomes_de_unidade_do_rateio_por_fracao():
    # Quando o rateio principal é por fração ideal (nomes de unidade vindos do
    # arquivo do usuário, ex: "AP01"), o fundo de reserva no modo "igual" deve
    # reaproveitar esses mesmos nomes, e não gerar "Unidade 1"/"Unidade 2"
    # genéricos - senão o merge por unidade duplica linhas em vez de somar.
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    fracoes = pd.DataFrame({"unidade": ["AP01", "AP02"], "fracao": [0.6, 0.4]})
    config_rateio = ConfiguracaoArrecadacao(modo="fracao_ideal", valor_total_mensal=1000.0, fracoes=fracoes)
    formulario = _formulario(
        numero_unidades=2,
        configuracao_rateio=config_rateio,
        possui_fundo_reserva=True,
        configuracao_fundo_reserva=_config_igual(10.0),
    )
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert len(resultado.valores_por_unidade) == 2
    assert set(resultado.valores_por_unidade["unidade"]) == {"AP01", "AP02"}
    assert resultado.fundo_reserva_valor == pytest.approx(20.0)


def test_inadimplencia_valor_total_e_unidades_preenchidos_a_partir_dos_dados():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario()
    unidades = pd.DataFrame(
        [
            {"unidade": "AP 02", "competencia": "01/2026", "total": 100.0},
            {"unidade": "AP 01", "competencia": "01/2026", "total": 50.0},
        ]
    )
    inadimplencia = DadosInadimplencia(
        condominio="Condomínio Teste",
        unidades=unidades,
        qtd_unidades_inadimplentes=2,
        percentual_inadimplencia=0.2,
        total_principal=0.0,
        total_geral=150.0,
    )
    resultado = gerar_previsao(demonstrativo, inadimplencia, formulario)
    assert resultado.inadimplencia_valor_total == pytest.approx(150.0)
    assert resultado.inadimplencia_unidades == ["AP 01", "AP 02"]


def test_inadimplencia_valor_total_e_unidades_vazios_sem_dados_de_inadimplencia():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario()
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.inadimplencia_valor_total == pytest.approx(0.0)
    assert resultado.inadimplencia_unidades == []
