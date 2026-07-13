import io

import pandas as pd
import pdfplumber
import pytest

from src.calculo.previsao import gerar_previsao
from src.models.schema import ConfiguracaoArrecadacao, DadosFormulario, DadosInadimplencia
from src.parsers.demonstrativo_parser import parse_demonstrativo
from src.parsers.inadimplentes_parser import parse_inadimplentes
from src.relatorio.pdf_export import _calcular_balanco, gerar_pdf_previsao


def _formulario(**kwargs):
    base = dict(
        nome_condominio="Condomínio Teste",
        periodo="Janeiro/2026 a Dezembro/2026",
        numero_unidades=10,
        configuracao_rateio=ConfiguracaoArrecadacao(modo="igual", valor_unico=100.0),
        possui_fundo_reserva=True,
        configuracao_fundo_reserva=ConfiguracaoArrecadacao(modo="igual", valor_unico=5.0),
    )
    base.update(kwargs)
    return DadosFormulario(**base)


def test_gerar_pdf_com_grafico_de_inadimplencia(caminho_demonstrativo, caminho_inadimplentes):
    demonstrativo = parse_demonstrativo(caminho_demonstrativo)
    inadimplencia = parse_inadimplentes(caminho_inadimplentes)
    resultado = gerar_previsao(demonstrativo, inadimplencia, _formulario())
    assert not resultado.concentracao_inadimplencia.empty

    pdf_bytes = gerar_pdf_previsao(resultado)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


def test_gerar_pdf_sem_grafico_de_inadimplencia(caminho_demonstrativo):
    demonstrativo = parse_demonstrativo(caminho_demonstrativo)
    inadimplencia = DadosInadimplencia(
        condominio="Condomínio Teste",
        unidades=pd.DataFrame(
            columns=[
                "unidade", "vencimento", "competencia", "atraso_dias", "codigo",
                "principal", "juros", "multa", "honorarios", "total",
            ]
        ),
        qtd_unidades_inadimplentes=5,
        percentual_inadimplencia=0.125,
        total_principal=4000.0,
        total_geral=4500.0,
    )
    resultado = gerar_previsao(demonstrativo, inadimplencia, _formulario())
    assert resultado.concentracao_inadimplencia.empty

    pdf_bytes = gerar_pdf_previsao(resultado)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


def test_gerar_pdf_sem_dados_de_inadimplencia_nenhum(caminho_demonstrativo):
    demonstrativo = parse_demonstrativo(caminho_demonstrativo)
    resultado = gerar_previsao(demonstrativo, None, _formulario())

    pdf_bytes = gerar_pdf_previsao(resultado)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


def test_gerar_pdf_com_outras_arrecadacoes_continua_em_6_paginas(caminho_demonstrativo, caminho_inadimplentes):
    # Regressão: a linha extra de "valor médio previsto por unidade" (mostrada
    # abaixo dos cartões de arrecadação) podia empurrar o conteúdo da página 2
    # para uma página extra quando havia "outras arrecadações" configuradas
    # (cartões extras ocupam espaço) - o relatório deve continuar fixo em 6
    # páginas (capa, arrecadações, despesas, inadimplência, balanço, reajuste)
    # mesmo nesse cenário.
    demonstrativo = parse_demonstrativo(caminho_demonstrativo)
    inadimplencia = parse_inadimplentes(caminho_inadimplentes)
    formulario = _formulario(
        outras_arrecadacoes=[("Rateio de agua", ConfiguracaoArrecadacao(modo="igual", valor_unico=15.0))],
    )
    resultado = gerar_previsao(demonstrativo, inadimplencia, formulario)

    pdf_bytes = gerar_pdf_previsao(resultado)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        assert len(pdf.pages) == 6


def test_gerar_pdf_padrao_tem_6_paginas_na_ordem_certa(caminho_demonstrativo, caminho_inadimplentes):
    demonstrativo = parse_demonstrativo(caminho_demonstrativo)
    inadimplencia = parse_inadimplentes(caminho_inadimplentes)
    resultado = gerar_previsao(demonstrativo, inadimplencia, _formulario())

    pdf_bytes = gerar_pdf_previsao(resultado)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        assert len(pdf.pages) == 6
        titulos = [(pdf.pages[i].extract_text() or "").splitlines()[1] for i in range(1, 6)]
        assert titulos == [
            "2. Arrecadacoes",
            "3. Despesas",
            "4. Inadimplencia",
            "5. Balanco Orcamentario Consolidado",
            "6. Reajuste",
        ]


def test_calcular_balanco_reconhece_superavit_e_deficit():
    class _Resultado:
        def __init__(self, receita_mensal, fundo_mensal, outras_mensal, outras_receitas_anual,
                     despesas_anual, pct_inadimplencia, pct_reajuste):
            self.receita_rateio_necessaria = receita_mensal
            self.fundo_reserva_valor = fundo_mensal
            self.total_outras_arrecadacoes_previsto = outras_mensal
            self.total_outras_receitas_previsto = outras_receitas_anual
            self.total_despesas_previsto = despesas_anual
            self.percentual_inadimplencia = pct_inadimplencia
            self.percentual_reajuste_automatico = pct_reajuste

    # Receita anual (1000*12=12000) folgada frente a despesas (6000) mesmo com inadimplencia -> superavit.
    superavit = _calcular_balanco(
        _Resultado(1000.0, 0.0, 0.0, 0.0, despesas_anual=6000.0, pct_inadimplencia=0.1, pct_reajuste=0.0)
    )
    assert superavit["receita_total"] == pytest.approx(12000.0)
    assert superavit["saldo_final"] > 0

    # Receita anual (500*12=6000) apertada frente a despesas (6000) - a inadimplencia sozinha ja gera deficit.
    deficit = _calcular_balanco(
        _Resultado(500.0, 0.0, 0.0, 0.0, despesas_anual=6000.0, pct_inadimplencia=0.2, pct_reajuste=0.0)
    )
    assert deficit["saldo_final"] < 0
