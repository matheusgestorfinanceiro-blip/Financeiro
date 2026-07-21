import io
import re

import pandas as pd
import pdfplumber
import pytest

from src.calculo.previsao import calcular_taxas_reajustadas, gerar_previsao
from src.models.schema import ConfiguracaoArrecadacao, DadosFormulario, DadosInadimplencia, LinhaDespesaPrevista
from src.parsers.demonstrativo_parser import parse_demonstrativo
from src.parsers.inadimplentes_parser import parse_inadimplentes
from src.relatorio.pdf_export import RelatorioPDF, _bloco_assinatura, _calcular_balanco, gerar_pdf_previsao


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


def test_gerar_pdf_inadimplencia_formato_horizontal_lista_unidades(caminho_demonstrativo, caminho_inadimplentes_horizontal):
    # Regressão: um PDF real de inadimplentes com códigos de unidade
    # numéricos (sem "AP") e várias unidades/meses em atraso não podia gerar
    # uma página de inadimplência contraditória (percentual > 0 mas "não há
    # unidades inadimplentes"). Confere que a tabela por unidade aparece no
    # texto do PDF.
    demonstrativo = parse_demonstrativo(caminho_demonstrativo)
    inadimplencia = parse_inadimplentes(caminho_inadimplentes_horizontal)
    resultado = gerar_previsao(demonstrativo, inadimplencia, _formulario())
    assert len(resultado.inadimplencia_unidades) == 6
    assert not resultado.inadimplencia_valor_por_unidade.empty

    pdf_bytes = gerar_pdf_previsao(resultado)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        # A pagina de inadimplencia é localizada pelo título, não por índice
        # fixo - a assinatura em todas as páginas (a partir da 2) pode empurrar
        # uma página cheia de conteúdo para uma página extra, deslocando a
        # numeração física.
        texto_pagina_4 = next(
            (p.extract_text() or "") for p in pdf.pages if "4. Inadimplencia" in (p.extract_text() or "")
        )
    assert "nao ha unidades inadimplentes" not in texto_pagina_4.lower()
    assert "16" in texto_pagina_4
    assert "Meses em atraso" in texto_pagina_4
    # O relatorio gerado nunca deve conter o nome do proprietario, so o codigo da unidade.
    assert "PROPRIETARIO EXEMPLO" not in texto_pagina_4


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


def test_gerar_pdf_com_outras_arrecadacoes_nao_gera_paginas_em_branco(caminho_demonstrativo, caminho_inadimplentes):
    # Regressão: um bug de posicionamento em _linha_ledger (página de balanço)
    # podia disparar quebras de página em cascata sempre que uma linha da
    # "planilha" caía perto do fim da página, gerando dezenas/centenas de
    # páginas em branco. O relatório completo (capa + 4 páginas fixas +
    # balanço variável + reajuste) deve ficar bem abaixo desse patamar mesmo
    # com "outras arrecadações" configuradas (mais uma linha na seção Receita).
    demonstrativo = parse_demonstrativo(caminho_demonstrativo)
    inadimplencia = parse_inadimplentes(caminho_inadimplentes)
    formulario = _formulario(
        outras_arrecadacoes=[("Rateio de agua", ConfiguracaoArrecadacao(modo="igual", valor_unico=15.0))],
    )
    resultado = gerar_previsao(demonstrativo, inadimplencia, formulario)

    pdf_bytes = gerar_pdf_previsao(resultado)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        assert 6 <= len(pdf.pages) <= 15


def test_gerar_pdf_padrao_tem_as_paginas_fixas_na_ordem_certa(caminho_demonstrativo, caminho_inadimplentes):
    demonstrativo = parse_demonstrativo(caminho_demonstrativo)
    inadimplencia = parse_inadimplentes(caminho_inadimplentes)
    resultado = gerar_previsao(demonstrativo, inadimplencia, _formulario())

    pdf_bytes = gerar_pdf_previsao(resultado)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        # A página de balanço agora é um "livro-razão" de tamanho variável
        # (uma linha por subcategoria de despesa do demonstrativo enviado),
        # então o total de páginas não é mais fixo - mas a ordem dos títulos
        # das páginas fixas continua sendo sempre a mesma.
        # A posicao da linha de titulo varia conforme a logo (imagem real
        # nao gera texto extraivel, o wordmark de texto gera) - por isso os
        # titulos sao localizados por padrao ("N. Nome da secao") em
        # qualquer linha da pagina, nao por indice fixo.
        titulos = [
            linha
            for pagina in pdf.pages
            for linha in (pagina.extract_text() or "").splitlines()
            if re.match(r"^\d+\. ", linha)
        ]
        assert "2. Arrecadacoes" in titulos
        assert "3. Despesas" in titulos
        assert "4. Inadimplencia" in titulos
        assert "5. Balanco Orcamentario Consolidado" in titulos
        assert titulos[-1] == "6. Reajuste"
        assert titulos.index("2. Arrecadacoes") < titulos.index("3. Despesas") < titulos.index("4. Inadimplencia")
        assert titulos.index("4. Inadimplencia") < titulos.index("5. Balanco Orcamentario Consolidado") < titulos.index("6. Reajuste")


def test_bloco_assinatura_nunca_pula_pagina_em_conteudo_cheio(caminho_demonstrativo, caminho_inadimplentes):
    # Regressao: com varias deducoes configuradas (desconto de pontualidade,
    # isencao, outra arrecadacao), a caixa de considerações da pagina
    # "2. Arrecadacoes" fica mais alta, e a assinatura compacta (nao-final)
    # acabava sendo empurrada para uma pagina nova em vez de ficar na mesma
    # pagina do conteudo - o usuario espera ve-la sempre junto.
    demonstrativo = parse_demonstrativo(caminho_demonstrativo)
    inadimplencia = parse_inadimplentes(caminho_inadimplentes)
    formulario = _formulario(
        possui_desconto_pontualidade=True, desconto_pontualidade_modo="percentual", desconto_pontualidade_valor=0.05,
        unidades_isentas=[("Unidade 1", 0.5)],
        outras_arrecadacoes=[("Rateio de agua", ConfiguracaoArrecadacao(modo="igual", valor_unico=15.0))],
    )
    resultado = gerar_previsao(demonstrativo, inadimplencia, formulario)

    pdf_bytes = gerar_pdf_previsao(resultado)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        texto_pagina_2 = pdf.pages[1].extract_text() or ""
    assert "2. Arrecadacoes" in texto_pagina_2
    assert "Responsavel pela emissao deste relatorio" in texto_pagina_2


def test_bloco_assinatura_preserva_b_margin_entre_chamadas():
    # Regressao: pdf.set_auto_page_break(False) do fpdf2 zera pdf.b_margin
    # como efeito colateral (o parametro margin tem default 0), a menos que
    # o valor atual seja passado de volta explicitamente. Sem isso, a partir
    # da segunda chamada de _bloco_assinatura (uma por pagina, a partir da
    # pagina 2) o calculo do limite inferior da pagina passaria a usar
    # b_margin=0 - quebrando tambem as checagens de espaco de
    # _caixa_consideracoes/_linha_ledger em todas as paginas seguintes, que
    # leem o mesmo pdf.b_margin.
    demonstrativo = parse_demonstrativo("data/fixtures/exemplo_demonstrativo.pdf")
    inadimplencia = parse_inadimplentes("data/fixtures/exemplo_inadimplentes.pdf")
    resultado = gerar_previsao(demonstrativo, inadimplencia, _formulario())

    pdf = RelatorioPDF()
    pdf.arquivos_temp = []
    pdf.add_page()
    b_margin_original = pdf.b_margin
    assert b_margin_original > 0

    for _ in range(3):
        _bloco_assinatura(pdf, resultado)
        assert pdf.b_margin == b_margin_original
        pdf.add_page()


def test_bloco_assinatura_final_nunca_cria_pagina_nova(caminho_demonstrativo, caminho_inadimplentes):
    # Regressao: quando a pagina de Reajuste ficava cheia (ex: as 2 caixas
    # lado a lado ocupando quase todo o espaco), a assinatura final
    # ("final=True") criava uma pagina nova so para ela - as vezes quase em
    # branco. O relatorio deve sempre terminar na mesma pagina do ultimo
    # conteudo, mesmo quando nao sobra espaco para o bloco grande.
    demonstrativo = parse_demonstrativo(caminho_demonstrativo)
    inadimplencia = parse_inadimplentes(caminho_inadimplentes)
    resultado = gerar_previsao(demonstrativo, inadimplencia, _formulario())

    pdf = RelatorioPDF()
    pdf.arquivos_temp = []
    pdf.add_page()
    # Simula o conteudo tendo preenchido quase toda a pagina, sem sobrar
    # espaco para o bloco grande (34mm + 10mm de respiro) antes do rodape.
    pdf.set_y(pdf.h - pdf.b_margin - 5)
    pagina_antes = pdf.page_no()

    _bloco_assinatura(pdf, resultado, final=True)

    assert pdf.page_no() == pagina_antes


def test_gerar_pdf_inadimplencia_com_grafico_cabe_numa_unica_pagina(caminho_demonstrativo, caminho_inadimplentes):
    # Regressao: o grafico de evolucao da inadimplencia (largura cheia da
    # pagina) deixava pouco espaco vertical para a caixa de considerações e
    # a tabela por unidade, empurrando parte da tabela para uma pagina extra
    # sem titulo, logo antes do "5. Balanco..." - a pagina de inadimplencia
    # (com grafico) precisa caber inteira numa unica pagina no cenario comum.
    demonstrativo = parse_demonstrativo(caminho_demonstrativo)
    inadimplencia = parse_inadimplentes(caminho_inadimplentes)
    resultado = gerar_previsao(demonstrativo, inadimplencia, _formulario())
    assert not resultado.concentracao_inadimplencia.empty

    pdf_bytes = gerar_pdf_previsao(resultado)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        paginas_texto = [pagina.extract_text() or "" for pagina in pdf.pages]
        idx_inadimplencia = next(i for i, t in enumerate(paginas_texto) if "4. Inadimplencia" in t)
        idx_balanco = next(i for i, t in enumerate(paginas_texto) if "5. Balanco Orcamentario Consolidado" in t)
    assert idx_balanco == idx_inadimplencia + 1


def test_gerar_pdf_sem_reajuste_aplicado_nao_tem_pagina_de_taxas_reajustadas(caminho_demonstrativo, caminho_inadimplentes):
    demonstrativo = parse_demonstrativo(caminho_demonstrativo)
    inadimplencia = parse_inadimplentes(caminho_inadimplentes)
    resultado = gerar_previsao(demonstrativo, inadimplencia, _formulario())

    pdf_bytes = gerar_pdf_previsao(resultado)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        paginas_texto = [pagina.extract_text() or "" for pagina in pdf.pages]
    assert not any("7. Taxas Reajustadas" in t for t in paginas_texto)


def test_gerar_pdf_com_reajuste_aplicado_adiciona_pagina_de_taxas_reajustadas(caminho_demonstrativo, caminho_inadimplentes):
    demonstrativo = parse_demonstrativo(caminho_demonstrativo)
    inadimplencia = parse_inadimplentes(caminho_inadimplentes)
    # Rateio baixo o suficiente para forcar deficit (e portanto reajuste automatico > 0).
    formulario = _formulario(configuracao_rateio=ConfiguracaoArrecadacao(modo="igual", valor_unico=1000.0))
    resultado_draft = gerar_previsao(demonstrativo, inadimplencia, formulario)
    assert resultado_draft.percentual_reajuste_automatico > 0

    resultado = calcular_taxas_reajustadas(resultado_draft, percentual_reajuste=0.2, aplicar_ao_fundo_reserva=True)

    pdf_bytes = gerar_pdf_previsao(resultado)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        paginas_texto = [pagina.extract_text() or "" for pagina in pdf.pages]
    assert any("7. Taxas Reajustadas" in t for t in paginas_texto)


def test_calcular_balanco_reconhece_superavit_e_deficit():
    class _Resultado:
        def __init__(self, receita_mensal, possui_fundo, fundo_mensal, outras_arrecadacoes, outras_receitas_anual,
                     despesas_anual, pct_inadimplencia, pct_reajuste):
            self.receita_rateio_necessaria = receita_mensal
            self.possui_fundo_reserva = possui_fundo
            self.fundo_reserva_valor = fundo_mensal
            self.outras_arrecadacoes_detalhe = outras_arrecadacoes
            self.total_outras_receitas_previsto = outras_receitas_anual
            self.total_despesas_previsto = despesas_anual
            self.despesas_classificadas = pd.DataFrame(
                [{"categoria_pai": "Categoria A", "subcategoria": "Item", "total": despesas_anual, "classificacao": "ordinaria"}]
            )
            self.despesas_previstas = [
                LinhaDespesaPrevista(
                    categoria_pai="Categoria A", subcategoria="Item", valor_historico=despesas_anual,
                    percentual_reajuste_aplicado=0.0, valor_previsto=despesas_anual, ajuste_manual=False,
                )
            ]
            self.percentual_inadimplencia = pct_inadimplencia
            self.percentual_reajuste_automatico = pct_reajuste
            self.desconto_receita_historico_anual = 0.0

    # Receita anual (1000*12=12000) folgada frente a despesas (6000) mesmo com inadimplencia -> superavit.
    superavit = _calcular_balanco(
        _Resultado(1000.0, False, 0.0, [], 0.0, despesas_anual=6000.0, pct_inadimplencia=0.1, pct_reajuste=0.0)
    )
    assert superavit["receita_total"] == pytest.approx(12000.0)
    assert superavit["saldo_final"] > 0

    # Receita anual (500*12=6000) apertada frente a despesas (6000) - a inadimplencia sozinha ja gera deficit.
    deficit = _calcular_balanco(
        _Resultado(500.0, False, 0.0, [], 0.0, despesas_anual=6000.0, pct_inadimplencia=0.2, pct_reajuste=0.0)
    )
    assert deficit["saldo_final"] < 0

    # Fundo de reserva e outras arrecadacoes entram como itens separados na receita.
    com_extras = _calcular_balanco(
        _Resultado(1000.0, True, 100.0, [("Rateio de agua", 50.0)], 0.0, despesas_anual=6000.0, pct_inadimplencia=0.0, pct_reajuste=0.0)
    )
    assert com_extras["receita_total"] == pytest.approx((1000.0 + 100.0 + 50.0) * 12)
    assert [nome for nome, _ in com_extras["receita_itens"]] == ["Rateio mensal", "Fundo de reserva", "Rateio de agua"]

    # Regressao: o reajuste sugerido NAO deve ser somado ao saldo final - um
    # deficit ordinario (sem reajuste) precisa continuar aparecendo como
    # deficit, mesmo que o percentual de reajuste automatico seja alto o
    # suficiente para "tampar o buraco" se fosse somado de volta.
    deficit_com_reajuste = _calcular_balanco(
        _Resultado(500.0, False, 0.0, [], 0.0, despesas_anual=6000.0, pct_inadimplencia=0.2, pct_reajuste=0.5)
    )
    assert deficit_com_reajuste["saldo_final"] == pytest.approx(deficit["saldo_final"])
    assert "reajuste_valor" not in deficit_com_reajuste
