"""Monta o relatório financeiro em PDF: capa com o período/filtros aplicados,
resumo com cartões e gráficos, comparação por pessoa, evolução no período
(quando abrange mais de um mês) e o detalhamento de todos os lançamentos."""
import datetime
import os
import tempfile

from fpdf import FPDF

from src.pessoal.graficos import (
    AZUL,
    CINZA,
    VERDE,
    VERMELHO,
    grafico_evolucao_mensal,
    grafico_pizza_categoria,
    grafico_por_pessoa,
)
from src.pessoal.modelos import TIPO_RECEITA
from src.pessoal.relatorio import ResumoPeriodo, evolucao_mensal
from src.pessoal.ui.estilo import fmt_moeda

CARD_BG = "#F3F4F6"
DESTAQUE_BG = "#EFF6FF"

COLUNAS_TABELA = [
    ("Data", 20),
    ("Tipo", 16),
    ("Descrição", 46),
    ("Categoria", 34),
    ("Pessoa", 22),
    ("Valor", 22),
]


def _hex_para_rgb(cor_hex: str) -> tuple[int, int, int]:
    cor_hex = cor_hex.lstrip("#")
    return tuple(int(cor_hex[i : i + 2], 16) for i in (0, 2, 4))


class RelatorioPessoalPDF(FPDF):
    arquivos_temp: list[str]

    def header(self):
        if self.page_no() == 1:
            return
        self.set_xy(self.w - 70, 8)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*_hex_para_rgb(CINZA))
        self.cell(60, 6, "RELATORIO FINANCEIRO", align="R")
        self.set_text_color(0, 0, 0)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", size=8)
        self.set_text_color(*_hex_para_rgb(CINZA))
        self.cell(0, 10, f"Pagina {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)

    def titulo_pagina(self, titulo: str):
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(*_hex_para_rgb(AZUL))
        self.cell(0, 10, titulo, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def imagem_temporaria(self, figura, **kwargs):
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        figura.savefig(tmp.name, dpi=150)
        self.arquivos_temp.append(tmp.name)
        self.image(tmp.name, **kwargs)


def _largura_util(pdf: RelatorioPessoalPDF) -> float:
    return pdf.w - pdf.l_margin - pdf.r_margin


def _cartoes_estatisticas(pdf: RelatorioPessoalPDF, itens: list[tuple[str, str, str]], colunas: int = 2):
    """itens: lista de (rotulo, valor, cor_hex_do_valor)."""
    largura_util = _largura_util(pdf)
    gap = 8
    largura_cartao = (largura_util - gap * (colunas - 1)) / colunas
    altura_cartao = 26
    x_inicial = pdf.l_margin
    y_inicial = pdf.get_y()

    for i, (rotulo, valor, cor) in enumerate(itens):
        col = i % colunas
        linha = i // colunas
        x = x_inicial + col * (largura_cartao + gap)
        y = y_inicial + linha * (altura_cartao + gap)

        pdf.set_fill_color(*_hex_para_rgb(CARD_BG))
        pdf.rect(x, y, largura_cartao, altura_cartao, style="F")

        pdf.set_xy(x + 4, y + 4)
        pdf.set_font("Helvetica", size=8.5)
        pdf.set_text_color(*_hex_para_rgb(CINZA))
        pdf.multi_cell(largura_cartao - 8, 4, rotulo)

        pdf.set_xy(x + 4, y + 13)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*_hex_para_rgb(cor))
        pdf.cell(largura_cartao - 8, 8, valor)
        pdf.set_text_color(0, 0, 0)

    linhas_de_cartoes = (len(itens) + colunas - 1) // colunas
    pdf.set_xy(pdf.l_margin, y_inicial + linhas_de_cartoes * (altura_cartao + gap))


def _caixa_texto(pdf: RelatorioPessoalPDF, texto: str, titulo: str = ""):
    largura_util = _largura_util(pdf)
    padding = 4

    pdf.set_font("Helvetica", size=10)
    linhas = pdf.multi_cell(largura_util - 2 * padding, 5.5, texto, dry_run=True, output="LINES")
    altura_titulo = 6 if titulo else 0
    altura_texto = len(linhas) * 5.5
    altura_caixa = altura_titulo + altura_texto + 2 * padding

    if pdf.get_y() + altura_caixa > pdf.h - pdf.b_margin:
        pdf.add_page()

    x = pdf.l_margin
    y = pdf.get_y()
    pdf.set_fill_color(*_hex_para_rgb(DESTAQUE_BG))
    pdf.rect(x, y, largura_util, altura_caixa, style="F")

    pdf.set_xy(x + padding, y + padding)
    if titulo:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*_hex_para_rgb(AZUL))
        pdf.cell(largura_util - 2 * padding, 6, titulo, new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(x + padding)

    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(largura_util - 2 * padding, 5.5, texto)
    pdf.set_xy(pdf.l_margin, y + altura_caixa + 8)


def _cabecalho_tabela(pdf: RelatorioPessoalPDF, colunas: list[tuple[str, float]]):
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(*_hex_para_rgb(AZUL))
    pdf.set_text_color(255, 255, 255)
    for nome, largura in colunas:
        pdf.cell(largura, 7, nome, fill=True, align="L")
    pdf.ln(7)
    pdf.set_text_color(0, 0, 0)


def _tabela_lancamentos(pdf: RelatorioPessoalPDF, ocorrencias: list):
    largura_util = _largura_util(pdf)
    soma_larguras = sum(w for _, w in COLUNAS_TABELA)
    colunas = [(nome, largura / soma_larguras * largura_util) for nome, largura in COLUNAS_TABELA]

    _cabecalho_tabela(pdf, colunas)
    pdf.set_font("Helvetica", size=8)
    linha_par = False
    for oc in ocorrencias:
        if pdf.get_y() + 6 > pdf.h - pdf.b_margin:
            pdf.add_page()
            _cabecalho_tabela(pdf, colunas)
            pdf.set_font("Helvetica", size=8)

        pdf.set_fill_color(*(_hex_para_rgb(CARD_BG) if linha_par else (255, 255, 255)))
        linha_par = not linha_par

        valores = [
            oc.data.strftime("%d/%m/%Y"),
            "Receita" if oc.tipo == TIPO_RECEITA else "Despesa",
            oc.descricao_completa[:28],
            oc.categoria[:20],
            oc.usuario[:14],
            fmt_moeda(oc.valor),
        ]
        for (_, largura), valor in zip(colunas, valores):
            pdf.cell(largura, 6, valor, fill=True, align="L")
        pdf.ln(6)


def _pagina_capa(pdf: RelatorioPessoalPDF, resumo: ResumoPeriodo, filtros: dict):
    pdf.add_page()
    pdf.set_fill_color(*_hex_para_rgb(AZUL))
    pdf.rect(0, 0, pdf.w, pdf.h, style="F")

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_xy(20, 80)
    pdf.cell(0, 8, "RELATORIO FINANCEIRO DA FAMILIA", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 22)
    pdf.set_x(20)
    periodo = f"{resumo.data_inicio.strftime('%d/%m/%Y')} a {resumo.data_fim.strftime('%d/%m/%Y')}"
    pdf.multi_cell(pdf.w - 40, 11, periodo, align="L")

    pdf.ln(4)
    pdf.set_font("Helvetica", size=11)
    pdf.set_x(20)
    pdf.cell(0, 6.5, f"Pessoas: {filtros.get('pessoas') or 'Todas'}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(20)
    pdf.cell(0, 6.5, f"Categorias: {filtros.get('categorias') or 'Todas'}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(20)
    pdf.cell(0, 6.5, f"Tipo: {filtros.get('tipos') or 'Receitas e despesas'}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(20)
    pdf.cell(0, 6.5, f"Total de lançamentos no período: {len(resumo.ocorrencias)}", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(pdf.h - 30)
    pdf.set_font("Helvetica", size=10)
    pdf.set_x(20)
    data_emissao = datetime.date.today().strftime("%d/%m/%Y")
    pdf.cell(0, 6, f"Relatorio gerado em {data_emissao}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)


def _pagina_resumo(pdf: RelatorioPessoalPDF, resumo: ResumoPeriodo, numero: int):
    pdf.add_page()
    pdf.titulo_pagina(f"{numero}. Resumo do período")

    cor_saldo = VERDE if resumo.saldo >= 0 else VERMELHO
    itens = [
        ("Receitas no período", fmt_moeda(resumo.total_receitas), AZUL),
        ("Despesas no período", fmt_moeda(resumo.total_despesas), VERMELHO),
        ("Saldo do período", fmt_moeda(resumo.saldo), cor_saldo),
        ("Total de lançamentos", str(len(resumo.ocorrencias)), CINZA),
    ]
    _cartoes_estatisticas(pdf, itens, colunas=2)
    pdf.ln(4)

    largura_meia = (_largura_util(pdf) - 6) / 2
    y_inicio = pdf.get_y()
    pdf.imagem_temporaria(
        grafico_pizza_categoria(resumo.por_categoria_despesa, "despesa"), x=pdf.l_margin, y=y_inicio, w=largura_meia
    )
    pdf.imagem_temporaria(
        grafico_pizza_categoria(resumo.por_categoria_receita, "receita"),
        x=pdf.l_margin + largura_meia + 6,
        y=y_inicio,
        w=largura_meia,
    )
    pdf.set_y(y_inicio + largura_meia * 0.85)


def _pagina_por_pessoa(pdf: RelatorioPessoalPDF, resumo: ResumoPeriodo, numero: int) -> bool:
    if len(resumo.por_usuario) < 2:
        return False
    pdf.add_page()
    pdf.titulo_pagina(f"{numero}. Receitas e despesas por pessoa")
    pdf.imagem_temporaria(grafico_por_pessoa(resumo.por_usuario), x=(pdf.w - 160) / 2, w=160)
    return True


def _pagina_evolucao(pdf: RelatorioPessoalPDF, resumo: ResumoPeriodo, numero: int) -> bool:
    resumos_mensais = evolucao_mensal(resumo.ocorrencias)
    if len(resumos_mensais) < 2:
        return False
    pdf.add_page()
    pdf.titulo_pagina(f"{numero}. Evolução no período")
    pdf.imagem_temporaria(grafico_evolucao_mensal(resumos_mensais), w=_largura_util(pdf))
    pdf.ln(3)
    _caixa_texto(
        pdf,
        "O gráfico acima mostra receitas (azul) e despesas (vermelho) de cada mês do período, "
        "com o saldo mensal em destaque (verde quando positivo, vermelho quando negativo).",
    )
    return True


def _pagina_detalhamento(pdf: RelatorioPessoalPDF, resumo: ResumoPeriodo, numero: int):
    pdf.add_page()
    pdf.titulo_pagina(f"{numero}. Detalhamento de todos os lançamentos")
    if not resumo.ocorrencias:
        pdf.set_font("Helvetica", size=10)
        pdf.cell(0, 6, "Nenhum lançamento encontrado com os filtros escolhidos.")
        return
    _tabela_lancamentos(pdf, resumo.ocorrencias)


def gerar_pdf_relatorio(resumo: ResumoPeriodo, filtros: dict) -> bytes:
    """Gera o relatório em PDF (capa, resumo com gráficos, comparação por
    pessoa, evolução no período e detalhamento completo) e retorna os bytes
    prontos para download.

    `filtros` é um dict com chaves opcionais "pessoas", "categorias" e
    "tipos" (strings já formatadas para exibição, ou None/"" para "todos")."""
    pdf = RelatorioPessoalPDF()
    pdf.arquivos_temp = []
    try:
        numero = 1
        _pagina_capa(pdf, resumo, filtros)
        _pagina_resumo(pdf, resumo, numero)
        numero += 1
        if _pagina_por_pessoa(pdf, resumo, numero):
            numero += 1
        if _pagina_evolucao(pdf, resumo, numero):
            numero += 1
        _pagina_detalhamento(pdf, resumo, numero)
        return bytes(pdf.output())
    finally:
        for caminho in pdf.arquivos_temp:
            try:
                os.remove(caminho)
            except OSError:
                pass
