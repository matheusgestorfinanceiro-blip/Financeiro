import io

import pandas as pd
import pdfplumber

from src.calculo.previsao import gerar_previsao
from src.models.schema import ConfiguracaoArrecadacao, DadosFormulario, DadosInadimplencia
from src.parsers.demonstrativo_parser import parse_demonstrativo
from src.parsers.inadimplentes_parser import parse_inadimplentes
from src.relatorio.pdf_export import gerar_pdf_previsao


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


def test_gerar_pdf_com_outras_arrecadacoes_continua_em_5_paginas(caminho_demonstrativo, caminho_inadimplentes):
    # Regressão: a linha extra de "valor médio previsto por unidade" (mostrada
    # abaixo dos cartões de arrecadação) podia empurrar o conteúdo da página 2
    # para uma 6a página quando havia "outras arrecadações" configuradas
    # (cartões extras ocupam espaço) - o relatório deve continuar fixo em 5
    # páginas mesmo nesse cenário.
    demonstrativo = parse_demonstrativo(caminho_demonstrativo)
    inadimplencia = parse_inadimplentes(caminho_inadimplentes)
    formulario = _formulario(
        outras_arrecadacoes=[("Rateio de agua", ConfiguracaoArrecadacao(modo="igual", valor_unico=15.0))],
    )
    resultado = gerar_previsao(demonstrativo, inadimplencia, formulario)

    pdf_bytes = gerar_pdf_previsao(resultado)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        assert len(pdf.pages) == 5
