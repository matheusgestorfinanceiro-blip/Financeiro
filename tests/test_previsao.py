import pandas as pd
import pytest

from src.calculo.previsao import calcular_taxas_reajustadas, gerar_previsao
from src.models.schema import (
    RESPONSAVEL_TECNICO_NOME,
    RESPONSAVEL_TECNICO_REGISTROS,
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


def test_assinatura_usa_dados_do_responsavel_tecnico_por_padrao():
    demonstrativo = _demonstrativo_simples()
    resultado = gerar_previsao(demonstrativo, None, _formulario())
    assert resultado.assinatura_nome == RESPONSAVEL_TECNICO_NOME
    assert resultado.assinatura_registro == RESPONSAVEL_TECNICO_REGISTROS
    assert resultado.assinatura_credito == ""


def test_assinatura_usa_nome_do_emissor_quando_nao_e_o_responsavel_tecnico():
    demonstrativo = _demonstrativo_simples()
    formulario = _formulario(emitido_pelo_responsavel_tecnico=False, nome_emissor="Sindico Fulano")
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.assinatura_nome == "Sindico Fulano"
    assert resultado.assinatura_registro == ""
    assert RESPONSAVEL_TECNICO_NOME in resultado.assinatura_credito
    assert RESPONSAVEL_TECNICO_REGISTROS in resultado.assinatura_credito


def test_gerar_previsao_nao_aplica_reajuste_por_padrao():
    # Sem passar pela tela de confirmacao (calcular_taxas_reajustadas), o
    # resultado nao deve ter nenhum reajuste "aplicado" - rateio_reajustado
    # e fundo_reserva_reajustado ficam iguais aos valores sem reajuste, e
    # percentual_reajuste_aplicado fica em 0, mesmo quando ha um reajuste
    # AUTOMATICO sugerido (deficit) - a pagina de taxas reajustadas so deve
    # aparecer depois de uma escolha explicita do usuario.
    demonstrativo = _demonstrativo_simples(total_despesa=1500.0, total_rateio=800.0)
    formulario = _formulario(configuracao_rateio=_config_igual(10.0))
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.percentual_reajuste_automatico > 0
    assert resultado.percentual_reajuste_aplicado == pytest.approx(0.0)
    assert resultado.rateio_reajustado == pytest.approx(resultado.receita_rateio_necessaria)
    assert resultado.fundo_reserva_reajustado == pytest.approx(resultado.fundo_reserva_valor)


def test_calcular_taxas_reajustadas_aplica_so_ao_rateio_por_padrao():
    demonstrativo = _demonstrativo_simples(total_despesa=1500.0, total_rateio=800.0)
    formulario = _formulario(configuracao_rateio=_config_igual(10.0))
    resultado = gerar_previsao(demonstrativo, None, formulario)

    ajustado = calcular_taxas_reajustadas(resultado, percentual_reajuste=0.25, aplicar_ao_fundo_reserva=False)
    assert ajustado.percentual_reajuste_aplicado == pytest.approx(0.25)
    assert ajustado.rateio_reajustado == pytest.approx(resultado.receita_rateio_necessaria * 1.25)
    assert ajustado.fundo_reserva_reajustado == pytest.approx(resultado.fundo_reserva_valor)
    assert ajustado.reajuste_aplicado_ao_fundo_reserva is False


def test_calcular_taxas_reajustadas_preenche_tabela_por_unidade():
    # Regressao: a pagina "Taxas Reajustadas" do PDF precisa de uma linha por
    # unidade com a fracao (peso da unidade no rateio) e o valor da taxa ja
    # reajustada - nao so os totais agregados.
    demonstrativo = _demonstrativo_simples(total_despesa=1500.0, total_rateio=800.0)
    formulario = _formulario(configuracao_rateio=_config_igual(10.0))  # 10 unidades, R$10 cada = R$100/mes
    resultado = gerar_previsao(demonstrativo, None, formulario)

    ajustado = calcular_taxas_reajustadas(resultado, percentual_reajuste=0.25, aplicar_ao_fundo_reserva=False)
    tabela = ajustado.taxas_reajustadas_por_unidade
    assert tabela is not None
    assert len(tabela) == 10
    # Rateio igualitario -> cada unidade tem a mesma fracao (1/10) e a mesma
    # taxa reajustada (R$10 x 1.25 = R$12.50).
    assert tabela["fracao"].round(4).unique().tolist() == [0.1]
    assert tabela["valor_taxa"].round(2).unique().tolist() == [12.5]


def test_calcular_taxas_reajustadas_aplica_tambem_ao_fundo_de_reserva():
    demonstrativo = _demonstrativo_simples(total_despesa=1500.0, total_rateio=800.0)
    formulario = _formulario(
        configuracao_rateio=_config_igual(10.0),
        possui_fundo_reserva=True,
        configuracao_fundo_reserva=_config_igual(2.0),
    )
    resultado = gerar_previsao(demonstrativo, None, formulario)

    ajustado = calcular_taxas_reajustadas(resultado, percentual_reajuste=0.1, aplicar_ao_fundo_reserva=True)
    assert ajustado.fundo_reserva_reajustado == pytest.approx(resultado.fundo_reserva_valor * 1.1)
    assert ajustado.reajuste_aplicado_ao_fundo_reserva is True
    # Outras arrecadacoes nunca recebem reajuste.
    assert ajustado.total_outras_arrecadacoes_previsto == pytest.approx(resultado.total_outras_arrecadacoes_previsto)


def test_reajuste_automatico_quando_despesa_maior_que_receita():
    # Reajuste agora compara a receita TOTAL configurada no formulário
    # (rateio + fundo de reserva + outras arrecadações, anualizados, mais as
    # receitas extraordinárias do histórico) com as despesas TOTAIS apuradas
    # no período - mesma conta usada no Balanço Orçamentário Consolidado.
    demonstrativo = _demonstrativo_simples(total_despesa=1500.0, total_rateio=800.0)
    formulario = _formulario(configuracao_rateio=_config_igual(10.0))
    resultado = gerar_previsao(demonstrativo, None, formulario)
    # Receita total anual = 10 x 10 unidades x 12 = 1200. Despesas totais = 1500.
    # (1500 - 1200) / 1200 = 0.25
    assert resultado.percentual_reajuste_automatico == pytest.approx(0.25)
    assert resultado.total_despesas_previsto == pytest.approx(1875.0)


def test_reajuste_automatico_ignora_despesas_extraordinarias():
    # A despesa extraordinária (concentrada em poucos meses) não deve entrar
    # na base de despesa usada no cálculo automático do reajuste, mesmo que
    # seja muito maior que a despesa ordinária.
    meses = [f"Mes{i}" for i in range(1, 13)]
    valores_extraordinaria = {m: 0.0 for m in meses}
    valores_extraordinaria[meses[0]] = 50000.0
    df_despesas = pd.DataFrame(
        [
            {"categoria_pai": "Categoria A", "subcategoria": "Item Ordinario", **{m: 2000.0 / 12 for m in meses}, "total": 2000.0},
            {"categoria_pai": "Categoria B", "subcategoria": "Obra Emergencial", **valores_extraordinaria, "total": 50000.0},
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
        total_despesas=52000.0,
    )
    # Receita total anual = 25 x 10 unidades x 12 = 3000, cobre a despesa
    # ordinaria de 2000 - se a despesa extraordinaria (50000) entrasse na
    # conta, o resultado seria um deficit gigante em vez de 0%.
    formulario = _formulario(
        configuracao_rateio=_config_igual(25.0), despesas_extraordinarias=["Obra Emergencial"],
    )
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.percentual_reajuste_automatico == pytest.approx(0.0)

    # Com a receita configurada abaixo da despesa ordinaria, o deficit e
    # calculado só com base nela (2000), não com a despesa total (52000).
    formulario_rateio_baixo = _formulario(
        configuracao_rateio=_config_igual(10.0), despesas_extraordinarias=["Obra Emergencial"],
    )
    resultado_com_deficit = gerar_previsao(demonstrativo, None, formulario_rateio_baixo)
    # Receita total anual = 10 x 10 x 12 = 1200. Despesa ordinaria = 2000.
    # (2000 - 1200) / 1200 = 0.6666...
    assert resultado_com_deficit.percentual_reajuste_automatico == pytest.approx((2000.0 - 1200.0) / 1200.0)


def test_reajuste_automatico_inclui_fundo_de_reserva_mas_ignora_outras_receitas():
    # A receita total usada no reajuste inclui rateio + fundo de reserva
    # (configurados), mas NAO as receitas extraordinarias/taxas extras do
    # historico - essas ficam de fora dessa conta, mesmo que apareçam no
    # demonstrativo.
    demonstrativo = _demonstrativo_simples(total_despesa=3000.0, total_rateio=800.0, outras_receitas=600.0)
    formulario = _formulario(
        configuracao_rateio=_config_igual(10.0),
        possui_fundo_reserva=True,
        configuracao_fundo_reserva=_config_igual(5.0),
    )
    resultado = gerar_previsao(demonstrativo, None, formulario)
    # Receita total anual = (10 + 5) x 10 unidades x 12 = 1800 (sem as 600 de outras receitas historico).
    assert resultado.receita_total_anual_base_reajuste == pytest.approx(1800.0)
    # Despesas totais = 3000. (3000 - 1800) / 1800 = 0.6666...
    assert resultado.percentual_reajuste_automatico == pytest.approx((3000.0 - 1800.0) / 1800.0)


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
    formulario = _formulario(receitas_extraordinarias=["Juros"])
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.total_outras_receitas_previsto == pytest.approx(200.0)
    # a receita de rateio agora vem diretamente da configuração do usuário (100 x 10 unidades)
    assert resultado.receita_rateio_necessaria == pytest.approx(1000.0)


def test_total_por_unidade_e_soma_direta_sem_ajuste_de_inadimplencia():
    # O Total por unidade e exatamente rateio + fundo de reserva + outras
    # arrecadacoes, sem nenhum ajuste (ex: inflar pela inadimplencia esperada).
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
    assert resultado.valores_por_unidade["total"].iloc[0] == pytest.approx(100.0)


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


def test_fundo_de_reserva_soma_na_arrecadacao_prevista_mensal():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(
        numero_unidades=10, configuracao_rateio=_config_igual(100.0),
        possui_fundo_reserva=True, configuracao_fundo_reserva=_config_igual(10.0),
    )
    resultado = gerar_previsao(demonstrativo, None, formulario)
    # (100 x 10) + (10 x 10) = 1100
    assert resultado.arrecadacao_prevista_mensal == pytest.approx(1100.0)


def test_outras_receitas_extraordinarias_somam_na_arrecadacao_prevista_mensal():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0, outras_receitas=500.0)
    formulario = _formulario(
        numero_unidades=10, configuracao_rateio=_config_igual(100.0),
        receitas_extraordinarias=["Juros"],
    )
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.percentual_reajuste_automatico == pytest.approx(0.0)
    assert resultado.total_outras_receitas_previsto == pytest.approx(500.0)
    # (100 x 10) + 500 (outras receitas extraordinarias do historico) = 1500
    assert resultado.arrecadacao_prevista_mensal == pytest.approx(1500.0)


def test_arrecadacao_prevista_mensal_usa_valor_total_mensal_no_rateio_por_fracao_ideal():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    fracoes = pd.DataFrame({"unidade": ["AP01", "AP02"], "fracao": [0.6, 0.4]})
    config_rateio = ConfiguracaoArrecadacao(modo="fracao_ideal", valor_total_mensal=1000.0, fracoes=fracoes)
    formulario = _formulario(numero_unidades=2, configuracao_rateio=config_rateio)
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.arrecadacao_prevista_mensal == pytest.approx(1000.0)


def test_desconto_pontualidade_valor_fixo_reduz_arrecadacao_prevista():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(
        numero_unidades=40,
        configuracao_rateio=_config_igual(180.0),
        possui_desconto_pontualidade=True,
        desconto_pontualidade_modo="valor_fixo",
        desconto_pontualidade_valor=20.0,
    )
    resultado = gerar_previsao(demonstrativo, None, formulario)
    # (180 - 20) x 40 = 6400
    assert resultado.arrecadacao_prevista_mensal == pytest.approx(6400.0)
    assert resultado.desconto_pontualidade_total_mensal == pytest.approx(800.0)


def test_desconto_pontualidade_percentual_reduz_arrecadacao_prevista():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(
        numero_unidades=40,
        configuracao_rateio=_config_igual(180.0),
        possui_desconto_pontualidade=True,
        desconto_pontualidade_modo="percentual",
        desconto_pontualidade_valor=0.05,
    )
    resultado = gerar_previsao(demonstrativo, None, formulario)
    # 180 x 40 x 0.95 = 6840
    assert resultado.arrecadacao_prevista_mensal == pytest.approx(6840.0)
    assert resultado.desconto_pontualidade_total_mensal == pytest.approx(360.0)


def test_desconto_pontualidade_nao_deixa_rateio_negativo():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(
        numero_unidades=5,
        configuracao_rateio=_config_igual(50.0),
        possui_desconto_pontualidade=True,
        desconto_pontualidade_modo="valor_fixo",
        desconto_pontualidade_valor=100.0,
    )
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.arrecadacao_prevista_mensal == pytest.approx(0.0)
    assert (resultado.valores_por_unidade["rateio"] >= 0).all()


def test_sem_desconto_pontualidade_nao_altera_arrecadacao():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(numero_unidades=10, configuracao_rateio=_config_igual(150.0))
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.possui_desconto_pontualidade is False
    assert resultado.desconto_pontualidade_total_mensal == pytest.approx(0.0)
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
    # inadimplencia_valor_total deve usar o valor PRINCIPAL (sem juros/multa/
    # honorarios), nao o total_geral - por isso os dois valores sao diferentes
    # neste teste, confirmando que o campo certo esta sendo usado.
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
        total_principal=130.0,
        total_geral=150.0,
    )
    resultado = gerar_previsao(demonstrativo, inadimplencia, formulario)
    assert resultado.inadimplencia_valor_total == pytest.approx(130.0)
    assert resultado.inadimplencia_unidades == ["AP 01", "AP 02"]


def test_inadimplencia_valor_total_e_unidades_vazios_sem_dados_de_inadimplencia():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario()
    resultado = gerar_previsao(demonstrativo, None, formulario)
    assert resultado.inadimplencia_valor_total == pytest.approx(0.0)
    assert resultado.inadimplencia_unidades == []


def test_unidade_isenta_100_por_cento_nao_paga_rateio():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(
        numero_unidades=4, configuracao_rateio=_config_igual(200.0),
        unidades_isentas=[("Unidade 1", 1.0)],
    )
    resultado = gerar_previsao(demonstrativo, None, formulario)
    valores = dict(zip(resultado.valores_por_unidade["unidade"], resultado.valores_por_unidade["rateio"]))
    assert valores["Unidade 1"] == pytest.approx(0.0)
    assert valores["Unidade 2"] == pytest.approx(200.0)
    # 3 unidades pagando integralmente (600) + 1 isenta (0) = 600.
    assert resultado.receita_rateio_necessaria == pytest.approx(600.0)
    assert resultado.isencao_total_mensal == pytest.approx(200.0)


def test_unidade_isenta_parcialmente_reduz_proporcionalmente():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    formulario = _formulario(
        numero_unidades=2, configuracao_rateio=_config_igual(200.0),
        unidades_isentas=[("Unidade 1", 0.5)],
    )
    resultado = gerar_previsao(demonstrativo, None, formulario)
    valores = dict(zip(resultado.valores_por_unidade["unidade"], resultado.valores_por_unidade["rateio"]))
    assert valores["Unidade 1"] == pytest.approx(100.0)
    assert valores["Unidade 2"] == pytest.approx(200.0)
    assert resultado.isencao_total_mensal == pytest.approx(100.0)


def test_isencao_se_propaga_para_arrecadacao_prevista_e_base_do_reajuste():
    demonstrativo = _demonstrativo_simples(total_despesa=1000.0, total_rateio=1000.0)
    sem_isencao = _formulario(numero_unidades=2, configuracao_rateio=_config_igual(200.0))
    com_isencao = _formulario(
        numero_unidades=2, configuracao_rateio=_config_igual(200.0),
        unidades_isentas=[("Unidade 1", 1.0)],
    )
    resultado_sem = gerar_previsao(demonstrativo, None, sem_isencao)
    resultado_com = gerar_previsao(demonstrativo, None, com_isencao)
    assert resultado_sem.arrecadacao_prevista_mensal == pytest.approx(400.0)
    assert resultado_com.arrecadacao_prevista_mensal == pytest.approx(200.0)
    assert resultado_com.receita_total_anual_base_reajuste == pytest.approx(resultado_sem.receita_total_anual_base_reajuste - 200.0 * 12)


def test_desconto_em_linha_de_receita_negativa_reduz_arrecadacao_prevista():
    meses = [f"Mes{i}" for i in range(1, 13)]
    df_despesas = pd.DataFrame(
        [{"categoria_pai": "Categoria A", "subcategoria": "Item 1", **{m: 1000.0 / 12 for m in meses}, "total": 1000.0}]
    )
    df_receitas = pd.DataFrame(
        [
            {"categoria": "Rateio Mensal - Taxa de Condomínio", **{m: 1000.0 / 12 for m in meses}, "total": 1000.0},
            {"categoria": "Isenção do Síndico", **{m: -100.0 / 12 for m in meses}, "total": -100.0},
        ]
    )
    demonstrativo = DadosDemonstrativo(
        condominio="Condomínio Teste", meses=meses, df_receitas=df_receitas, df_despesas=df_despesas,
        total_receitas=900.0, total_despesas=1000.0,
    )
    formulario = _formulario(numero_unidades=10, configuracao_rateio=_config_igual(100.0))
    resultado = gerar_previsao(demonstrativo, None, formulario)
    # Receita rateio = 1000/mes; desconto historico = 100/ano = 8.33/mes.
    assert resultado.desconto_receita_historico_anual == pytest.approx(100.0)
    assert resultado.arrecadacao_prevista_mensal == pytest.approx(1000.0 - 100.0 / 12)
    # A linha negativa nao deve ser contada em total_outras_receitas_previsto (evita dupla contagem).
    assert resultado.total_outras_receitas_previsto == pytest.approx(0.0)
