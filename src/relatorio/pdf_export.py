"""Monta o relatório final em PDF: 6 páginas fixas (capa, arrecadações, despesas,
inadimplência, balanço orçamentário consolidado, reajuste), com a marca da Azul
Administradora no canto superior direito de todas as páginas (exceto a capa,
que já tem identidade visual própria)."""
import tempfile
from pathlib import Path

import pandas as pd
from fpdf import FPDF

from src.relatorio.graficos import (
    CYAN,
    GRAY,
    NAVY,
    grafico_despesas_por_categoria_pai,
    grafico_evolucao_inadimplencia,
    grafico_receitas_ordinaria_x_extraordinaria,
)
from src.ui.formatacao import fmt_moeda, fmt_pct

CAMINHO_LOGO = Path(__file__).resolve().parents[2] / "data" / "assets" / "logo_branca.png"

CARD_BG = "#EEF4FA"
DESTAQUE_BG = "#E4F5FA"

RESPONSAVEL_TECNICO_NOME = "Matheus Rodrigues Costa"
RESPONSAVEL_TECNICO_REGISTROS = "CRA-BA 2-01714 | CRECI-BA 20719"


def _hex_para_rgb(cor_hex: str) -> tuple[int, int, int]:
    cor_hex = cor_hex.lstrip("#")
    return tuple(int(cor_hex[i : i + 2], 16) for i in (0, 2, 4))


def _total_por_classificacao(df) -> dict:
    if df is None or df.empty:
        return {"ordinaria": 0.0, "extraordinaria": 0.0}
    agrupado = df.groupby("classificacao")["total"].sum()
    return {
        "ordinaria": float(agrupado.get("ordinaria", 0.0)),
        "extraordinaria": float(agrupado.get("extraordinaria", 0.0)),
    }


def _top_despesas_extraordinarias(resultado, n: int = 3) -> list[tuple[str, str, float]]:
    df = resultado.despesas_classificadas
    if df is None or df.empty:
        return []
    filtrado = df[df["classificacao"] == "extraordinaria"].sort_values("total", ascending=False)
    return [
        (row["categoria_pai"], row["subcategoria"], float(row["total"]))
        for _, row in filtrado.head(n).iterrows()
    ]


class RelatorioPDF(FPDF):
    arquivos_temp: list[str]

    def header(self):
        if self.page_no() == 1:
            return
        if CAMINHO_LOGO.exists():
            self.image(str(CAMINHO_LOGO), x=self.w - 32, y=6, w=22)
        else:
            self.set_xy(self.w - 70, 8)
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*_hex_para_rgb(CYAN))
            self.cell(60, 6, "AZUL ADMINISTRADORA", align="R")
            self.set_text_color(0, 0, 0)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", size=8)
        self.set_text_color(*_hex_para_rgb(GRAY))
        self.cell(0, 10, f"Pagina {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)

    def titulo_pagina(self, titulo: str):
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(*_hex_para_rgb(NAVY))
        self.cell(0, 10, titulo, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def imagem_temporaria(self, figura, **kwargs):
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        figura.savefig(tmp.name, dpi=150)
        self.arquivos_temp.append(tmp.name)
        self.image(tmp.name, **kwargs)


def _largura_util(pdf: RelatorioPDF) -> float:
    return pdf.w - pdf.l_margin - pdf.r_margin


def _cartoes_estatisticas(pdf: RelatorioPDF, itens: list[tuple[str, str]], colunas: int = 2):
    """Desenha uma grade de "cartões" (N por linha) com um rótulo pequeno e um
    valor grande em destaque, no lugar de simples linhas de texto."""
    largura_util = _largura_util(pdf)
    gap = 8
    largura_cartao = (largura_util - gap * (colunas - 1)) / colunas
    altura_cartao = 28
    x_inicial = pdf.l_margin
    y_inicial = pdf.get_y()

    for i, (rotulo, valor) in enumerate(itens):
        col = i % colunas
        linha = i // colunas
        x = x_inicial + col * (largura_cartao + gap)
        y = y_inicial + linha * (altura_cartao + gap)

        pdf.set_fill_color(*_hex_para_rgb(CARD_BG))
        pdf.rect(x, y, largura_cartao, altura_cartao, style="F")

        pdf.set_xy(x + 4, y + 4)
        pdf.set_font("Helvetica", size=8.5)
        pdf.set_text_color(*_hex_para_rgb(GRAY))
        pdf.multi_cell(largura_cartao - 8, 4, rotulo)

        pdf.set_xy(x + 4, y + 15)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*_hex_para_rgb(NAVY))
        pdf.cell(largura_cartao - 8, 8, valor)
        pdf.set_text_color(0, 0, 0)

    linhas_de_cartoes = (len(itens) + colunas - 1) // colunas
    pdf.set_xy(pdf.l_margin, y_inicial + linhas_de_cartoes * (altura_cartao + gap))


def _caixa_consideracoes(pdf: RelatorioPDF, texto: str, titulo: str = "Considerações da análise"):
    """Desenha uma caixa com fundo destacado em volta de um texto de análise,
    para chamar atenção de forma simples e objetiva."""
    largura_util = _largura_util(pdf)
    padding = 4

    pdf.set_font("Helvetica", "B", 10)
    altura_titulo = 6 if titulo else 0

    pdf.set_font("Helvetica", size=10)
    linhas = pdf.multi_cell(largura_util - 2 * padding, 5.5, texto, dry_run=True, output="LINES")
    altura_texto = len(linhas) * 5.5
    altura_caixa = altura_titulo + altura_texto + 2 * padding

    # Se a caixa nao couber no espaco restante da pagina, comeca uma pagina
    # nova para ela inteira, em vez de deixar a quebra automatica do fpdf2
    # cortar o texto no meio (o que espalhava conteudo numa pagina extra).
    if pdf.get_y() + altura_caixa > pdf.h - pdf.b_margin:
        pdf.add_page()

    x = pdf.l_margin
    y = pdf.get_y()

    pdf.set_fill_color(*_hex_para_rgb(DESTAQUE_BG))
    pdf.rect(x, y, largura_util, altura_caixa, style="F")

    pdf.set_xy(x + padding, y + padding)
    if titulo:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*_hex_para_rgb(NAVY))
        pdf.cell(largura_util - 2 * padding, 6, titulo, new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(x + padding)

    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(largura_util - 2 * padding, 5.5, texto)

    pdf.set_xy(pdf.l_margin, y + altura_caixa + 8)


def _pagina_capa(pdf: RelatorioPDF, resultado):
    pdf.add_page()
    pdf.set_fill_color(*_hex_para_rgb(NAVY))
    pdf.rect(0, 0, pdf.w, pdf.h, style="F")

    if CAMINHO_LOGO.exists():
        pdf.image(str(CAMINHO_LOGO), x=pdf.w - 40, y=10, w=28)
    else:
        pdf.set_xy(pdf.w - 80, 12)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(70, 6, "AZUL ADMINISTRADORA", align="R")

    pdf.set_text_color(*_hex_para_rgb(CYAN))
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_xy(20, 100)
    pdf.cell(0, 8, "PREVISAO ORCAMENTARIA CONDOMINIAL", new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_x(20)
    pdf.multi_cell(pdf.w - 40, 14, resultado.nome_condominio, align="L")

    pdf.ln(6)
    pdf.set_font("Helvetica", size=14)
    pdf.set_x(20)
    pdf.cell(0, 8, f"Periodo de avaliacao: {resultado.periodo}", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(pdf.h - 30)
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(*_hex_para_rgb(GRAY))
    pdf.set_x(20)
    pdf.cell(0, 6, f"Relatorio gerado em {resultado.data_geracao}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)


def _pagina_arrecadacoes(pdf: RelatorioPDF, resultado):
    pdf.add_page()
    pdf.titulo_pagina("2. Arrecadacoes")

    totais = _total_por_classificacao(resultado.receitas_classificadas)
    total_historico = totais["ordinaria"] + totais["extraordinaria"]
    pct_ordinaria = totais["ordinaria"] / total_historico if total_historico else 0.0
    pct_extraordinaria = 1 - pct_ordinaria if total_historico else 0.0

    _cartoes_estatisticas(
        pdf,
        [
            ("Ordinario (recorrente ou anual)", fmt_moeda(totais["ordinaria"])),
            ("Extraordinario (eventual)", fmt_moeda(totais["extraordinaria"])),
            ("Arrecadacao prevista mensalmente", fmt_moeda(resultado.arrecadacao_prevista_mensal)),
        ],
        colunas=3,
    )

    pdf.ln(2)

    if resultado.outras_arrecadacoes_detalhe:
        _cartoes_estatisticas(
            pdf,
            [(nome, fmt_moeda(valor)) for nome, valor in resultado.outras_arrecadacoes_detalhe],
            colunas=min(len(resultado.outras_arrecadacoes_detalhe), 3),
        )
        pdf.ln(2)

    # O grafico e menor quando ha outras arrecadacoes ocupando espaco acima,
    # para sempre caber com folga antes das considerações.
    largura_grafico = 80 if resultado.outras_arrecadacoes_detalhe else 130
    pdf.imagem_temporaria(
        grafico_receitas_ordinaria_x_extraordinaria(resultado),
        x=(pdf.w - largura_grafico) / 2,
        w=largura_grafico,
    )
    pdf.ln(3)

    if total_historico:
        texto_desconto = ""
        if resultado.possui_desconto_pontualidade and resultado.desconto_pontualidade_total_mensal:
            if resultado.desconto_pontualidade_modo == "valor_fixo":
                descricao_desconto = f"{fmt_moeda(resultado.desconto_pontualidade_valor)} por unidade"
            else:
                descricao_desconto = fmt_pct(resultado.desconto_pontualidade_valor)
            texto_desconto = (
                f" Ja esta descontado o desconto de pontualidade configurado ({descricao_desconto}), que reduz "
                f"o rateio em {fmt_moeda(resultado.desconto_pontualidade_total_mensal)} por mes no total."
            )
        texto = (
            f"A arrecadacao mensal prevista para o proximo periodo e de {fmt_moeda(resultado.arrecadacao_prevista_mensal)}, "
            f"com base no rateio, fundo de reserva e demais arrecadacoes configurados.{texto_desconto} "
            f"No historico dos ultimos 12 meses (periodo avaliado), a arrecadacao ordinaria somou "
            f"{fmt_moeda(totais['ordinaria'])} ({fmt_pct(pct_ordinaria)} do total arrecadado) - valores recorrentes "
            "e regulares mes a mes, como o rateio mensal, que servem de base confiavel para o calculo do reajuste. "
            f"Ja as arrecadacoes extraordinarias somaram {fmt_moeda(totais['extraordinaria'])} ({fmt_pct(pct_extraordinaria)} "
            "do total): sao receitas eventuais e nao recorrentes (ex: juros, multas, receitas pontuais), que nao "
            "se repetem todo mes e por isso nao devem ser usadas como base para o calculo do reajuste ou do "
            "rateio do proximo periodo, pois nao ha garantia de que voltem a ocorrer."
        )
    else:
        texto = "Nao ha dados de receita suficientes no historico para esta analise."
    _caixa_consideracoes(pdf, texto)


def _pagina_despesas(pdf: RelatorioPDF, resultado):
    pdf.add_page()
    pdf.titulo_pagina("3. Despesas")

    totais = _total_por_classificacao(resultado.despesas_classificadas)
    total_historico = totais["ordinaria"] + totais["extraordinaria"]
    pct_ordinaria = totais["ordinaria"] / total_historico if total_historico else 0.0
    pct_extraordinaria = 1 - pct_ordinaria if total_historico else 0.0

    _cartoes_estatisticas(
        pdf,
        [
            ("Ordinarias (recorrente ou anual)", fmt_moeda(totais["ordinaria"])),
            ("Extraordinarias (total anual)", fmt_moeda(totais["extraordinaria"])),
            ("Despesas totais previstas para 12 meses", fmt_moeda(resultado.total_despesas_previsto)),
        ],
        colunas=3,
    )

    pdf.ln(2)
    largura_grafico = 130
    pdf.imagem_temporaria(
        grafico_despesas_por_categoria_pai(resultado),
        x=(pdf.w - largura_grafico) / 2,
        w=largura_grafico,
    )
    pdf.ln(3)

    if total_historico:
        contagem = (
            resultado.despesas_classificadas["classificacao"].value_counts()
            if resultado.despesas_classificadas is not None
            else pd.Series(dtype="int64")
        )
        qtd_ordinarias = int(contagem.get("ordinaria", 0))
        qtd_extraordinarias = int(contagem.get("extraordinaria", 0))
        qtd_total = qtd_ordinarias + qtd_extraordinarias
        texto = (
            f"No historico dos ultimos 12 meses, {fmt_pct(pct_ordinaria)} da despesa foi recorrente "
            f"(aparece de forma regular ao longo do ano) e {fmt_pct(pct_extraordinaria)} foi "
            "extraordinaria ou eventual (concentrada em poucos meses).\n\n"
            "Criterio tecnico: cada subcategoria e classificada pelo coeficiente de variacao "
            "(desvio padrao dividido pela media) dos seus 12 valores mensais. Coeficiente de variacao ate 50% "
            "indica uma distribuicao regular ao longo do ano (despesa ordinaria/recorrente); acima de 50% "
            "indica valores concentrados em poucos meses (despesa extraordinaria/eventual). E uma classificacao "
            "estatistica, nao uma categorizacao contabil oficial.\n\n"
            f"Das {qtd_total} subcategorias de despesa analisadas, {qtd_ordinarias} foram classificadas como "
            f"ordinarias e {qtd_extraordinarias} como extraordinarias. Despesas extraordinarias nao devem compor "
            "a base de calculo do reajuste, ja que nao ha garantia de que se repitam no proximo periodo."
        )
    else:
        texto = "Nao ha dados de despesa suficientes no historico para esta analise."

    _caixa_consideracoes(pdf, texto)


def _pagina_inadimplencia(pdf: RelatorioPDF, resultado):
    pdf.add_page()
    pdf.titulo_pagina("4. Inadimplencia")

    tem_unidades = (
        resultado.inadimplencia_valor_por_unidade is not None
        and not resultado.inadimplencia_valor_por_unidade.empty
    )
    tem_concentracao = resultado.concentracao_inadimplencia is not None and not resultado.concentracao_inadimplencia.empty
    qtd_unidades = len(resultado.inadimplencia_unidades)
    max_meses_atraso = int(resultado.inadimplencia_valor_por_unidade["meses_em_atraso"].max()) if tem_unidades else 0
    # Grafico de evolucao so faz sentido quando ha mais de um mes de
    # competencia em atraso (em alguma unidade) ou mais de uma unidade
    # inadimplente - com 1 unidade e 1 mes, um grafico de 1 barra nao ajuda.
    tem_grafico = tem_concentracao and (max_meses_atraso > 1 or qtd_unidades > 1)

    _cartoes_estatisticas(
        pdf,
        [
            ("Percentual de inadimplencia apurado", fmt_pct(resultado.percentual_inadimplencia)),
            ("Valor principal em aberto", fmt_moeda(resultado.inadimplencia_valor_total)),
        ],
    )
    pdf.ln(2)

    if tem_grafico:
        pdf.imagem_temporaria(grafico_evolucao_inadimplencia(resultado), w=_largura_util(pdf))
        pdf.ln(3)

    if tem_unidades:
        largura_util = _largura_util(pdf)
        larguras = [largura_util * 0.55, largura_util * 0.25, largura_util * 0.20]
        _linha_ledger(
            pdf, larguras, ["Unidade", "Valor em aberto", "Meses em atraso"],
            fill=NAVY, cor_texto="#FFFFFF", bold=True,
        )
        for _, linha_unidade in resultado.inadimplencia_valor_por_unidade.iterrows():
            _linha_ledger(
                pdf, larguras,
                [str(linha_unidade["unidade"]), fmt_moeda(linha_unidade["valor_total"]), str(int(linha_unidade["meses_em_atraso"]))],
            )
        pdf.ln(5)

    partes_texto = [
        f"O condominio apresenta {fmt_pct(resultado.percentual_inadimplencia)} de inadimplencia apurada, "
        f"totalizando {fmt_moeda(resultado.inadimplencia_valor_total)} de valor principal em aberto "
        "(sem juros, multa ou honorarios)."
    ]
    if qtd_unidades == 0:
        partes_texto.append(
            "Nao ha unidades inadimplentes identificadas no relatorio de inadimplentes enviado."
        )
    else:
        partes_texto.append(f"Ao todo, {qtd_unidades} unidade(s) estao inadimplentes atualmente.")
        if max_meses_atraso > 1:
            partes_texto.append(
                f"Algumas unidades acumulam atraso em mais de um mes de competencia (ate {max_meses_atraso} "
                "meses), o que indica um padrao de inadimplencia recorrente, nao apenas pontual."
            )
        if tem_grafico:
            partes_texto.append(
                "O grafico acima mostra o valor em aberto por mes de competencia das cobrancas atualmente "
                "inadimplentes (nao e uma serie historica do percentual de inadimplencia, e sim a "
                f"concentracao das cobrancas em aberto hoje). O mes de competencia com maior concentracao "
                f"de valores em aberto foi {resultado.mes_pico_inadimplencia}, o que merece atencao especial "
                "do sindico e da administradora para identificar a causa (ex: aumento pontual de taxa, "
                "dificuldade financeira concentrada em um periodo, etc.)."
            )
        partes_texto.append(
            "A tabela acima detalha o valor total em aberto e a quantidade de meses em atraso de cada unidade."
        )

    _caixa_consideracoes(pdf, " ".join(partes_texto))


FILL_RECEITA = "#2E5496"
FILL_DESPESAS = "#FF0000"
FILL_SUBGRUPO = "#A6A6A6"
FILL_SUBTOTAL = "#D9D9D9"
FILL_TOTAL_GERAL = "#808080"
COR_TEXTO_DESPESA = "#FF0000"


def _calcular_balanco(resultado) -> dict:
    """Resumo consolidado no mesmo espirito da planilha manual "ANALISE" ja
    usada pela Azul (Receita / Despesas / Inadimplencia / Reajuste / Saldo
    Final, tudo anual). `receita_itens` guarda cada linha de receita prevista
    (nome, valor anual) para montar o "livro-razao" da pagina.

    receita_rateio_necessaria, fundo_reserva_valor e cada item de
    outras_arrecadacoes_detalhe sao valores MENSAIS (mesma convencao de
    ConfiguracaoArrecadacao, usada tambem em arrecadacao_prevista_mensal) -
    por isso sao multiplicados por 12 aqui. total_outras_receitas_previsto ja
    vem anual do historico."""
    receita_itens = [("Rateio mensal", resultado.receita_rateio_necessaria * 12)]
    if resultado.possui_fundo_reserva:
        receita_itens.append(("Fundo de reserva", resultado.fundo_reserva_valor * 12))
    for nome, valor in resultado.outras_arrecadacoes_detalhe:
        receita_itens.append((nome, valor * 12))
    if resultado.total_outras_receitas_previsto:
        receita_itens.append(("Outras receitas (historico, extraordinarias)", resultado.total_outras_receitas_previsto))

    receita_total = sum(valor for _, valor in receita_itens)
    inadimplencia_valor = resultado.percentual_inadimplencia * receita_total
    reajuste_valor = resultado.percentual_reajuste_automatico * receita_total
    total_geral = resultado.total_despesas_previsto + inadimplencia_valor
    saldo_final = receita_total - total_geral + reajuste_valor
    return {
        "receita_itens": receita_itens,
        "receita_total": receita_total,
        "inadimplencia_valor": inadimplencia_valor,
        "reajuste_valor": reajuste_valor,
        "total_geral": total_geral,
        "saldo_final": saldo_final,
    }


def _linha_ledger(pdf: RelatorioPDF, larguras, celulas, fill=None, cor_texto=None, bold=False, align=None):
    """Uma linha da "planilha" (categoria | anual | mensal | % do total),
    com fundo e cor de texto opcionais - reaproveitada em todas as linhas da
    pagina de balanco, do mesmo jeito que a planilha original usa faixas de
    cor para separar cabecalhos, subtotais e totais."""
    if align is None:
        align = ["L"] + ["R"] * (len(celulas) - 1)
    altura = 6

    # Garante espaco antes de desenhar a linha inteira: como as 4 celulas sao
    # posicionadas com set_xy usando um y fixo capturado uma unica vez, uma
    # quebra de pagina automatica disparada no meio de uma celula (fpdf2)
    # deixaria as celulas seguintes reusando esse y antigo (agora invalido na
    # pagina nova) - cada uma delas dispararia sua propria quebra de novo,
    # gerando dezenas de paginas em branco. Verificar o espaco ANTES evita
    # que a quebra automatica dispare no meio de uma linha.
    if pdf.get_y() + altura > pdf.h - pdf.b_margin:
        pdf.add_page()

    if fill:
        pdf.set_fill_color(*_hex_para_rgb(fill))
    pdf.set_text_color(*_hex_para_rgb(cor_texto)) if cor_texto else pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B" if bold else "", 8.5)
    x0 = pdf.l_margin
    y0 = pdf.get_y()
    x = x0
    for texto, largura, alinhamento in zip(celulas, larguras, align):
        pdf.set_xy(x, y0)
        pdf.cell(largura, altura, texto, align=alinhamento, fill=bool(fill))
        x += largura
    pdf.set_xy(x0, y0 + altura)
    pdf.set_text_color(0, 0, 0)


def _pagina_balanco(pdf: RelatorioPDF, resultado):
    """Reproduz a estrutura, cores e organizacao da planilha "ANALISE" que a
    Azul ja usa manualmente para preparar previsoes (Receita / Despesas por
    categoria), preenchida com os dados reais dos documentos anexados e da
    configuracao do formulario. Inadimplencia, reajuste e saldo final ja tem
    paginas proprias no relatorio, entao nao sao repetidos aqui."""
    pdf.add_page()
    pdf.titulo_pagina("5. Balanco Orcamentario Consolidado")

    largura_util = _largura_util(pdf)
    larguras = [largura_util * 0.46, largura_util * 0.18, largura_util * 0.18, largura_util * 0.18]

    balanco = _calcular_balanco(resultado)
    receita_total = balanco["receita_total"]

    _linha_ledger(pdf, larguras, ["RECEITA", "Anual", "Mensal", "% do Total"], fill=FILL_RECEITA, cor_texto="#FFFFFF", bold=True)
    for nome, valor_anual in balanco["receita_itens"]:
        pct = valor_anual / receita_total if receita_total else 0.0
        _linha_ledger(pdf, larguras, [nome, fmt_moeda(valor_anual), fmt_moeda(valor_anual / 12), fmt_pct(pct)])
    _linha_ledger(
        pdf, larguras,
        ["TOTAL", fmt_moeda(receita_total), fmt_moeda(receita_total / 12), fmt_pct(1.0 if receita_total else 0.0)],
        fill=FILL_SUBTOTAL, bold=True,
    )

    pdf.ln(2)

    despesas_total = resultado.total_despesas_previsto
    despesas_por_categoria: dict[str, list] = {}
    for linha_despesa in resultado.despesas_previstas:
        despesas_por_categoria.setdefault(linha_despesa.categoria_pai, []).append(linha_despesa)

    _linha_ledger(pdf, larguras, ["DESPESAS", "Anual", "Mensal", "% do Total"], fill=FILL_DESPESAS, cor_texto="#FFFFFF", bold=True)
    for categoria_pai, linhas_despesa in despesas_por_categoria.items():
        _linha_ledger(pdf, larguras, [categoria_pai.upper(), "", "", ""], fill=FILL_SUBGRUPO, bold=True)
        subtotal = 0.0
        for linha_despesa in linhas_despesa:
            pct = linha_despesa.valor_previsto / despesas_total if despesas_total else 0.0
            _linha_ledger(
                pdf, larguras,
                [linha_despesa.subcategoria, fmt_moeda(linha_despesa.valor_previsto),
                 fmt_moeda(linha_despesa.valor_previsto / 12), fmt_pct(pct)],
                cor_texto=COR_TEXTO_DESPESA,
            )
            subtotal += linha_despesa.valor_previsto
        pct_subtotal = subtotal / despesas_total if despesas_total else 0.0
        _linha_ledger(
            pdf, larguras,
            [f"Total de despesas {categoria_pai}", fmt_moeda(subtotal), fmt_moeda(subtotal / 12), fmt_pct(pct_subtotal)],
            fill=FILL_SUBTOTAL, bold=True,
        )
    _linha_ledger(
        pdf, larguras,
        ["DESPESAS TOTAIS", fmt_moeda(despesas_total), fmt_moeda(despesas_total / 12), fmt_pct(1.0 if despesas_total else 0.0)],
        fill=FILL_TOTAL_GERAL, cor_texto="#FFFFFF", bold=True,
    )


def _pagina_reajuste(pdf: RelatorioPDF, resultado):
    pdf.add_page()
    pdf.titulo_pagina("6. Reajuste")

    largura_util = _largura_util(pdf)
    pdf.set_fill_color(*_hex_para_rgb(NAVY))
    altura_destaque = 40
    y_destaque = pdf.get_y()
    pdf.rect(pdf.l_margin, y_destaque, largura_util, altura_destaque, style="F")

    pdf.set_xy(pdf.l_margin, y_destaque + 6)
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(largura_util, 6, "Percentual de reajuste proposto", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_xy(pdf.l_margin, y_destaque + 12)
    pdf.set_font("Helvetica", "B", 40)
    pdf.set_text_color(*_hex_para_rgb(CYAN))
    pdf.cell(largura_util, 20, fmt_pct(resultado.percentual_reajuste_automatico), align="C")
    pdf.set_text_color(0, 0, 0)

    pdf.set_xy(pdf.l_margin, y_destaque + altura_destaque + 8)

    totais_receitas = _total_por_classificacao(resultado.receitas_classificadas)
    totais_despesas = _total_por_classificacao(resultado.despesas_classificadas)

    receita_total = resultado.receita_total_anual_base_reajuste
    despesas_totais = resultado.total_despesas_historico
    inadimplencia_valor = resultado.percentual_inadimplencia * receita_total
    resultado_geral = receita_total - despesas_totais - inadimplencia_valor
    texto_reajuste = (
        "Criterio tecnico: o percentual de reajuste e apurado comparando a receita total prevista (rateio + "
        "fundo de reserva + outras arrecadacoes configuradas, anualizados, mais as receitas extraordinarias "
        "identificadas no historico) com as despesas totais apuradas no periodo avaliado (12 meses) e com a "
        "inadimplencia esperada - a mesma conta usada no Balanco Orcamentario Consolidado, para as duas paginas "
        "do relatorio ficarem sempre consistentes entre si.\n\n"
        f"Receita total apurada: {fmt_moeda(receita_total)}. Despesas totais apuradas: {fmt_moeda(despesas_totais)}. "
        f"Inadimplencia esperada ({fmt_pct(resultado.percentual_inadimplencia)} da receita total): "
        f"{fmt_moeda(inadimplencia_valor)}. Resultado (receita total menos despesas totais menos inadimplencia): "
        f"{fmt_moeda(resultado_geral)}."
    )
    if resultado_geral >= 0:
        texto_reajuste += (
            "\n\nComo o resultado e maior ou igual a zero, a receita total configurada ja cobre integralmente as "
            "despesas totais do periodo e a inadimplencia esperada - nao ha deficit a equacionar, portanto nao ha "
            "justificativa tecnica para propor reajuste. Elevar a taxa condominial nesse cenario oneraria os "
            "condominos sem necessidade comprovada pelos numeros do periodo avaliado."
        )
    else:
        deficit = despesas_totais + inadimplencia_valor - receita_total
        texto_reajuste += (
            f"\n\nComo o resultado e negativo, ha um deficit de {fmt_moeda(deficit)}: as despesas totais somadas "
            "a inadimplencia esperada superam a receita total do periodo. O percentual de reajuste proposto "
            f"({fmt_pct(resultado.percentual_reajuste_automatico)}) e exatamente esse deficit dividido pela "
            "receita total apurada - aplicado a receita atual, o valor resultante passa a cobrir as despesas "
            "totais e a inadimplencia esperada sem sobra nem falta, equilibrando o orcamento do condominio."
        )
    _caixa_consideracoes(pdf, texto_reajuste, titulo="Como o reajuste foi apurado")

    receita_extraordinaria = totais_receitas["extraordinaria"]
    despesa_extraordinaria = totais_despesas["extraordinaria"]
    texto_atencao = (
        "As receitas e despesas extraordinarias (eventuais, sem regularidade mensal) ja entram na conta do "
        "reajuste acima (a receita extraordinaria compoe a receita total, e a despesa extraordinaria compoe as "
        "despesas totais) - mas, por nao haver garantia de que se repitam no proximo periodo, merecem atencao "
        "separada pelo impacto que tem no caixa do condominio quando ocorrem.\n\n"
        f"No periodo avaliado, as arrecadacoes extraordinarias somaram {fmt_moeda(receita_extraordinaria)} "
        f"e as despesas extraordinarias somaram {fmt_moeda(despesa_extraordinaria)}."
    )
    if despesa_extraordinaria > receita_extraordinaria:
        diferenca_extraordinaria = despesa_extraordinaria - receita_extraordinaria
        texto_atencao += (
            f" Como as despesas extraordinarias superaram as arrecadacoes extraordinarias em "
            f"{fmt_moeda(diferenca_extraordinaria)}, esse desequilibrio pontual tende a consumir caixa ou "
            "fundo de reserva nos meses em que ocorre, ja que o condominio gastou eventualmente mais do que "
            "arrecadou eventualmente - vale avaliar se essas despesas continuarao ocorrendo e se o fundo de "
            "reserva esta dimensionado para absorve-las."
        )
    elif receita_extraordinaria > despesa_extraordinaria:
        diferenca_extraordinaria = receita_extraordinaria - despesa_extraordinaria
        texto_atencao += (
            f" Como as arrecadacoes extraordinarias superaram as despesas extraordinarias em "
            f"{fmt_moeda(diferenca_extraordinaria)}, esses periodos geraram folga eventual de caixa, que "
            "pode ter sido usada para reforcar o fundo de reserva ou reduzir a necessidade de reajuste nos "
            "proximos periodos - desde que essa folga nao seja tratada como receita recorrente."
        )
    else:
        texto_atencao += " Arrecadacoes e despesas extraordinarias se equilibraram no periodo avaliado."

    top_extraordinarias = _top_despesas_extraordinarias(resultado)
    if top_extraordinarias:
        texto_atencao += "\n\nMaiores despesas extraordinarias identificadas no periodo:"
        for categoria_pai, subcategoria, total in top_extraordinarias:
            texto_atencao += f"\n- {categoria_pai} / {subcategoria}: {fmt_moeda(total)}"

    _caixa_consideracoes(pdf, texto_atencao, titulo="Pontos de atencao: extraordinarias e impacto no caixa")

    # Assinatura sempre ancorada no rodape da pagina, mesmo que o conteudo
    # acima varie de tamanho - por isso a quebra automatica fica desligada
    # só para este bloco (é o ultimo conteudo desta pagina, então não há
    # risco de "perder" a quebra automática para o resto do relatório).
    pdf.set_auto_page_break(False)
    pdf.set_y(max(pdf.get_y() + 6, pdf.h - 42))
    pdf.set_draw_color(*_hex_para_rgb(GRAY))
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + 80, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*_hex_para_rgb(NAVY))
    pdf.cell(0, 5, RESPONSAVEL_TECNICO_NOME, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(*_hex_para_rgb(GRAY))
    pdf.cell(0, 5, RESPONSAVEL_TECNICO_REGISTROS, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Responsavel tecnico pela previsao orcamentaria", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)


def gerar_pdf_previsao(resultado) -> bytes:
    """Gera o PDF final de 6 paginas (capa, arrecadacoes, despesas, inadimplencia,
    balanco consolidado, reajuste) e retorna os bytes prontos para download."""
    pdf = RelatorioPDF()
    pdf.arquivos_temp = []
    try:
        _pagina_capa(pdf, resultado)
        _pagina_arrecadacoes(pdf, resultado)
        _pagina_despesas(pdf, resultado)
        _pagina_inadimplencia(pdf, resultado)
        _pagina_balanco(pdf, resultado)
        _pagina_reajuste(pdf, resultado)
        return bytes(pdf.output())
    finally:
        import os

        for caminho in pdf.arquivos_temp:
            try:
                os.remove(caminho)
            except OSError:
                pass
