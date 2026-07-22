"""Monta o relatório final em PDF: páginas fixas (capa, arrecadações, despesas,
inadimplência, balanço orçamentário consolidado, reajuste), com a marca da Azul
Administradora em todas as páginas: maior e no canto superior direito na
capa, menor e no canto superior esquerdo nas demais."""
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
    grafico_indicador_inadimplencia,
    grafico_receitas_ordinaria_x_extraordinaria,
)
from src.ui.formatacao import fmt_moeda, fmt_pct

# Arquivo real da logo (fundo branco) - usado automaticamente no lugar do
# wordmark de texto (ver header() e _pagina_capa() abaixo) quando presente.
CAMINHO_LOGO = Path(__file__).resolve().parents[2] / "data" / "assets" / "logo_azul.png"

# Fonte DejaVu Sans (licença livre, ver data/assets/fonts/LICENSE-DejaVuSans.txt)
# embutida no PDF para desenhar simbolos Unicode (✓ ⚠ ▲ € ⚖ etc.) que as
# fontes core do fpdf2 (Helvetica) nao suportam - nao inclui emoji colorido
# de verdade (esses usam um formato de fonte que o fpdf2 nao le), mas cobre
# um bom conjunto de simbolos/dingbats para servir de "icone" vetorial.
CAMINHO_FONTE_ICONES = Path(__file__).resolve().parents[2] / "data" / "assets" / "fonts" / "DejaVuSans.ttf"
FONTE_ICONES = "DejaVuSans"

# Icones (caracteres Unicode da fonte acima) usados como indicador de cada
# pagina/badge do relatorio - nomes descritivos para facilitar a leitura do
# codigo que os usa.
ICONE_ARRECADACOES = "€"  # €
ICONE_DESPESAS = "▼"  # ▼
ICONE_INADIMPLENCIA = "⚠"  # ⚠
ICONE_BALANCO = "⚖"  # ⚖
ICONE_REAJUSTE = "▲"  # ▲
ICONE_CHECK = "✓"  # ✓

CARD_BG = "#EEF4FA"
DESTAQUE_BG = "#E4F5FA"


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


def _despesas_previstas_ordinarias(resultado) -> list:
    """Filtra `despesas_previstas` para só as subcategorias classificadas como
    ordinarias (mesma base usada no calculo do reajuste automatico), a partir
    de `despesas_classificadas` (categoria_pai + subcategoria + classificacao)."""
    df = resultado.despesas_classificadas
    if df is None or df.empty:
        return list(resultado.despesas_previstas)
    ordinarias = set(
        zip(df[df["classificacao"] == "ordinaria"]["categoria_pai"], df[df["classificacao"] == "ordinaria"]["subcategoria"])
    )
    return [
        linha for linha in resultado.despesas_previstas
        if (linha.categoria_pai, linha.subcategoria) in ordinarias
    ]


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if CAMINHO_FONTE_ICONES.exists():
            self.add_font(FONTE_ICONES, "", str(CAMINHO_FONTE_ICONES))

    def header(self):
        if self.page_no() == 1:
            return
        # Reserva uma faixa fixa no topo esquerdo para a marca (imagem real
        # ou o wordmark de texto), independente da altura exata da logo,
        # para o título da página (desenhado logo em seguida por
        # titulo_pagina) nunca ficar colado ou sobreposto a ela.
        if CAMINHO_LOGO.exists():
            self.image(str(CAMINHO_LOGO), x=self.l_margin, y=6, w=16)
        else:
            self.set_xy(self.l_margin, 9)
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*_hex_para_rgb(CYAN))
            self.cell(14, 5, "AZUL")
            self.set_font("Helvetica", "B", 7)
            self.set_text_color(*_hex_para_rgb(NAVY))
            self.cell(40, 5, " ADMINISTRADORA")
            self.set_text_color(0, 0, 0)
        self.set_y(26)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", size=8)
        self.set_text_color(*_hex_para_rgb(GRAY))
        self.cell(0, 10, f"Pagina {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)

    def titulo_pagina(self, titulo: str, cor_indicador: str = None, icone: str = None):
        """Título de seção com uma bolinha colorida à esquerda - com um
        símbolo Unicode (fonte DejaVu Sans embutida, ver CAMINHO_FONTE_ICONES)
        dentro quando `icone` é informado, ou só a bolinha lisa quando não
        (fallback caso a fonte não esteja disponível)."""
        cor_indicador = cor_indicador or CYAN
        diametro = 5.5
        y_topo = self.get_y()
        self.set_fill_color(*_hex_para_rgb(cor_indicador))
        self.ellipse(self.l_margin, y_topo + 2, diametro, diametro, style="F")
        if icone and CAMINHO_FONTE_ICONES.exists():
            self.set_font(FONTE_ICONES, size=7)
            self.set_text_color(255, 255, 255)
            self.set_xy(self.l_margin, y_topo + 2)
            self.cell(diametro, diametro, icone, align="C")
            self.set_text_color(0, 0, 0)
        self.set_xy(self.l_margin + diametro + 3, y_topo)
        self.set_font("Helvetica", "B", 16)
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
    valor grande em destaque, no lugar de simples linhas de texto. Cada
    cartão tem cantos arredondados e uma barra de destaque colorida à
    esquerda (mesmo raio dos cantos, para os dois elementos se alinharem
    visualmente)."""
    largura_util = _largura_util(pdf)
    gap = 8
    largura_cartao = (largura_util - gap * (colunas - 1)) / colunas
    altura_cartao = 28
    raio = 2.5
    largura_barra = 2.2
    x_inicial = pdf.l_margin
    y_inicial = pdf.get_y()

    for i, (rotulo, valor) in enumerate(itens):
        col = i % colunas
        linha = i // colunas
        x = x_inicial + col * (largura_cartao + gap)
        y = y_inicial + linha * (altura_cartao + gap)

        pdf.set_fill_color(*_hex_para_rgb(CARD_BG))
        pdf.rect(x, y, largura_cartao, altura_cartao, style="F", round_corners=True, corner_radius=raio)
        pdf.set_fill_color(*_hex_para_rgb(CYAN))
        pdf.rect(
            x, y, largura_barra, altura_cartao, style="F",
            round_corners=("TOP_LEFT", "BOTTOM_LEFT"), corner_radius=raio,
        )

        pdf.set_xy(x + 6, y + 5)
        pdf.set_font("Helvetica", size=8)
        pdf.set_text_color(*_hex_para_rgb(GRAY))
        pdf.multi_cell(largura_cartao - 10, 4, rotulo)

        pdf.set_xy(x + 6, y + 16)
        pdf.set_font("Helvetica", "B", 15)
        pdf.set_text_color(*_hex_para_rgb(NAVY))
        pdf.cell(largura_cartao - 10, 8, valor)
        pdf.set_text_color(0, 0, 0)

    linhas_de_cartoes = (len(itens) + colunas - 1) // colunas
    pdf.set_xy(pdf.l_margin, y_inicial + linhas_de_cartoes * (altura_cartao + gap))


def _caixa_consideracoes(pdf: RelatorioPDF, texto: str, titulo: str = "Considerações da análise"):
    """Desenha uma caixa com fundo destacado em volta de um texto de análise,
    para chamar atenção de forma simples e objetiva."""
    largura_util = _largura_util(pdf)
    padding = 4

    pdf.set_font("Helvetica", "B", 10.5)
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
    pdf.rect(x, y, largura_util, altura_caixa, style="F", round_corners=True, corner_radius=2.5)

    pdf.set_xy(x + padding, y + padding)
    if titulo:
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.set_text_color(*_hex_para_rgb(NAVY))
        pdf.cell(largura_util - 2 * padding, 6, titulo, new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(x + padding)

    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(largura_util - 2 * padding, 5.5, texto)

    pdf.set_xy(pdf.l_margin, y + altura_caixa + 8)


def _caixas_lado_a_lado(
    pdf: RelatorioPDF, caixas: list[tuple[str, str]],
    font_size: float = 10, line_height: float = 5.5, reserva_inferior: float = 0,
):
    """Como _caixa_consideracoes, mas desenha N caixas lado a lado (mesma
    altura, a maior necessária entre elas) em vez de empilhadas - usado
    quando 2 blocos de texto relacionados devem ficar sempre na mesma
    página: lado a lado, a altura total consumida é a da caixa mais alta,
    não a soma das duas, o que aumenta a chance de caberem juntas.

    `font_size`/`line_height` permitem reduzir o texto quando a página é
    apertada (ex: página de Reajuste, que ainda precisa de espaço para o
    bloco grande de assinatura no rodapé). `reserva_inferior` reserva uma
    faixa no fim da página (ex: para a assinatura) que a caixa não deve
    invadir ao decidir se cabe."""
    n = len(caixas)
    largura_util = _largura_util(pdf)
    gap = 8
    padding = 4
    altura_titulo_linha = font_size * 0.6
    largura_caixa = (largura_util - gap * (n - 1)) / n
    largura_texto = largura_caixa - 2 * padding

    alturas = []
    for titulo, texto in caixas:
        pdf.set_font("Helvetica", "B", font_size + 0.5)
        linhas_titulo = pdf.multi_cell(largura_texto, altura_titulo_linha, titulo, dry_run=True, output="LINES") if titulo else []
        pdf.set_font("Helvetica", size=font_size)
        linhas_texto = pdf.multi_cell(largura_texto, line_height, texto, dry_run=True, output="LINES")
        alturas.append(len(linhas_titulo) * altura_titulo_linha + len(linhas_texto) * line_height + 2 * padding)
    altura_linha = max(alturas)

    # Mesma logica de _caixa_consideracoes: se a linha inteira nao couber no
    # espaco restante (ja descontada a reserva do rodape), comeca uma pagina
    # nova para as duas caixas juntas.
    if pdf.get_y() + altura_linha > pdf.h - pdf.b_margin - reserva_inferior:
        pdf.add_page()

    x_inicial = pdf.l_margin
    y = pdf.get_y()
    for i, (titulo, texto) in enumerate(caixas):
        x = x_inicial + i * (largura_caixa + gap)
        pdf.set_fill_color(*_hex_para_rgb(DESTAQUE_BG))
        pdf.rect(x, y, largura_caixa, altura_linha, style="F", round_corners=True, corner_radius=2.5)

        pdf.set_xy(x + padding, y + padding)
        if titulo:
            pdf.set_font("Helvetica", "B", font_size + 0.5)
            pdf.set_text_color(*_hex_para_rgb(NAVY))
            pdf.multi_cell(largura_texto, altura_titulo_linha, titulo)
            pdf.set_x(x + padding)

        pdf.set_font("Helvetica", size=font_size)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(largura_texto, line_height, texto)

    pdf.set_xy(pdf.l_margin, y + altura_linha + 8)


def _badge(
    pdf: RelatorioPDF, texto: str, cor_fundo: str, x: float = None, y: float = None,
    cor_texto: str = "#FFFFFF", icone: str = None,
) -> float:
    """Desenha um selo (retângulo arredondado colorido com texto curto
    dentro, com um símbolo Unicode opcional à esquerda - fonte DejaVu Sans
    embutida, ver CAMINHO_FONTE_ICONES) - mesmo espírito visual do selo
    branco usado atrás da logo na capa. Usado no lugar de emoji (as fontes
    core do fpdf2 não suportam) para marcar visualmente classificações/
    status. Retorna a largura usada, para posicionar badges lado a lado sem
    sobrepor."""
    x = pdf.l_margin if x is None else x
    y = pdf.get_y() if y is None else y
    padding = 3
    altura = 6

    tem_icone = bool(icone) and CAMINHO_FONTE_ICONES.exists()
    largura_icone = 4.5 if tem_icone else 0

    pdf.set_font("Helvetica", "B", 8)
    largura = pdf.get_string_width(texto) + 2 * padding + largura_icone
    pdf.set_fill_color(*_hex_para_rgb(cor_fundo))
    pdf.rect(x, y, largura, altura, style="F", round_corners=True, corner_radius=altura / 2)

    x_cursor = x + padding
    if tem_icone:
        pdf.set_font(FONTE_ICONES, size=7)
        pdf.set_text_color(*_hex_para_rgb(cor_texto))
        pdf.set_xy(x_cursor, y + 1)
        pdf.cell(largura_icone, altura - 2, icone, align="L")
        x_cursor += largura_icone

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_xy(x_cursor, y + 1)
    pdf.set_text_color(*_hex_para_rgb(cor_texto))
    pdf.cell(largura - (x_cursor - x) - padding, altura - 2, texto, align="L")
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(x, y)
    return largura


def _bloco_assinatura(pdf: RelatorioPDF, resultado, final: bool = False):
    """Assinatura de quem emitiu o relatorio, ancorada no rodape da pagina -
    a partir da pagina 2. Nas paginas normais e uma linha unica e compacta
    (as paginas de conteudo costumam usar quase todo o espaco disponivel, sem
    sobra para um bloco maior sem invadir a faixa do rodape). Na ultima
    pagina do relatorio (`final=True`) a assinatura fecha o documento
    formalmente: bloco maior, centralizado, ancorado no rodape da propria
    pagina, com todos os detalhes (registro profissional e credito, quando
    existirem).

    NUNCA cria uma pagina nova so para a assinatura (nem na versao final): o
    relatorio deve sempre terminar na mesma pagina do ultimo conteudo, sem
    pagina em branco/quase em branco no fim. O bloco final e ancorado no
    rodape da pagina; garantir que o conteudo acima nao invada essa faixa e
    responsabilidade de quem monta a pagina (ex: _pagina_reajuste usa fonte/
    espacamento reduzidos para o conteudo caber com folga acima da
    assinatura).

    Desliga a quebra automatica de pagina para este bloco (e dai em diante),
    pois ele e sempre o ultimo conteudo desenhado na pagina - o resto do
    relatorio ja usa checagens manuais de espaco (_caixa_consideracoes,
    _linha_ledger), entao isso nao afeta nenhum outro conteudo."""
    # fpdf2's set_auto_page_break(auto) tem margin=0 como padrao e SEMPRE
    # sobrescreve pdf.b_margin com esse valor, mesmo quando so queremos
    # desligar a quebra automatica - sem preservar o valor atual aqui,
    # pdf.b_margin viraria 0 permanentemente, quebrando as checagens de
    # espaco de _caixa_consideracoes/_linha_ledger em todas as paginas
    # seguintes (que tambem leem pdf.b_margin).
    pdf.set_auto_page_break(False, margin=pdf.b_margin)
    largura_util = _largura_util(pdf)
    limite_inferior = pdf.h - pdf.b_margin  # abaixo disso e a faixa do rodape

    if final:
        # Ancora o bloco de fechamento no rodape da propria pagina (nunca cria
        # pagina nova). Altura ~28mm: linha + nome + registro + funcao (+
        # credito, quando existe). Se por acaso o conteudo acima ja tiver
        # descido demais, ainda ancora no rodape - preferimos uma pequena
        # sobreposicao com o conteudo a uma pagina extra so com a assinatura;
        # na pratica _pagina_reajuste garante folga suficiente acima.
        altura_bloco = 32 if resultado.assinatura_credito else 26
        pdf.set_y(limite_inferior - altura_bloco)
    else:
        # Nas paginas normais NUNCA pula para uma pagina nova so pela
        # assinatura - o bloco e minimo (uma linha), entao ainda sobra folga
        # real antes do texto "Pagina N" (desenhado bem mais embaixo, em
        # pdf.h - 15) mesmo quando o conteudo da pagina esta quase cheio.
        altura_bloco = 5
        gap_topo = 2
        y_padrao = limite_inferior - altura_bloco  # posicao "ideal" quando sobra espaco
        y_maximo_seguro = (pdf.h - 17) - altura_bloco  # nunca ultrapassa isso, mesmo com pouco espaco
        pdf.set_y(min(max(pdf.get_y() + gap_topo, y_padrao), y_maximo_seguro))

    if final:
        pdf.set_draw_color(*_hex_para_rgb(GRAY))
        x_linha_inicio = pdf.l_margin + largura_util * 0.3
        pdf.line(x_linha_inicio, pdf.get_y(), x_linha_inicio + largura_util * 0.4, pdf.get_y())
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 15)
        pdf.set_text_color(*_hex_para_rgb(NAVY))
        pdf.cell(largura_util, 8, resultado.assinatura_nome, align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(*_hex_para_rgb(GRAY))
        if resultado.assinatura_registro:
            pdf.cell(largura_util, 5.5, resultado.assinatura_registro, align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(largura_util, 5.5, "Responsavel pela emissao deste relatorio", align="C", new_x="LMARGIN", new_y="NEXT")
        if resultado.assinatura_credito:
            pdf.ln(3)
            pdf.set_font("Helvetica", "I", 8)
            pdf.multi_cell(largura_util, 4, resultado.assinatura_credito, align="C")
        pdf.set_text_color(0, 0, 0)
    else:
        # Linha unica e compacta: nome (+ registro, se houver) em negrito,
        # seguido de "Responsavel pela emissao deste relatorio" - cabe no
        # pouco espaco que sobra mesmo em paginas quase cheias.
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(*_hex_para_rgb(NAVY))
        nome_texto = resultado.assinatura_nome
        if resultado.assinatura_registro:
            nome_texto += f" ({resultado.assinatura_registro})"
        largura_nome = pdf.get_string_width(nome_texto) + 2
        pdf.cell(largura_nome, 4, nome_texto)
        pdf.set_font("Helvetica", size=7.5)
        pdf.set_text_color(*_hex_para_rgb(GRAY))
        pdf.cell(0, 4, "- Responsavel pela emissao deste relatorio", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)


def _pagina_capa(pdf: RelatorioPDF, resultado):
    pdf.add_page()
    pdf.set_fill_color(*_hex_para_rgb(NAVY))
    pdf.rect(0, 0, pdf.w, pdf.h, style="F")

    if CAMINHO_LOGO.exists():
        # A logo real tem fundo branco - um "selo" branco atras dela evita
        # que esse fundo apareça como um retangulo cru sobre o navy da capa.
        largura_logo = 46
        x_logo = pdf.w - 18 - largura_logo
        y_logo = 12
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(x_logo - 5, y_logo - 5, largura_logo + 10, largura_logo + 10, style="F", round_corners=True, corner_radius=4)
        pdf.image(str(CAMINHO_LOGO), x=x_logo, y=y_logo, w=largura_logo)
    else:
        pdf.set_xy(pdf.w - 90, 12)
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(*_hex_para_rgb(CYAN))
        pdf.cell(80, 9, "AZUL", align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(pdf.w - 90, 22)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(80, 6, "ADMINISTRADORA", align="R")

    pdf.set_text_color(*_hex_para_rgb(CYAN))
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_xy(20, 98)
    pdf.cell(0, 8, "PREVISAO ORCAMENTARIA CONDOMINIAL", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(pdf.get_y() + 4)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 28)
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
    pdf.titulo_pagina("2. Arrecadacoes", icone=ICONE_ARRECADACOES)

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

    # Grafico em barras horizontais (baixo e largo) - ocupa a largura util da
    # pagina sem custar muita altura, diferente da pizza anterior (quadrada),
    # que empurrava a caixa de considerações para uma pagina extra.
    largura_grafico = _largura_util(pdf)
    pdf.imagem_temporaria(
        grafico_receitas_ordinaria_x_extraordinaria(resultado),
        x=pdf.l_margin,
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
                f" Ja esta descontado o desconto de pontualidade ({descricao_desconto}), que reduz "
                f"o rateio em {fmt_moeda(resultado.desconto_pontualidade_total_mensal)} por mes no total."
            )
        if resultado.unidades_isentas:
            nomes_isentas = ", ".join(
                f"{unidade} ({fmt_pct(percentual)})" for unidade, percentual in resultado.unidades_isentas
            )
            texto_desconto += (
                f" Ja esta descontada a isencao de {nomes_isentas}, que reduz o rateio em "
                f"{fmt_moeda(resultado.isencao_total_mensal)} por mes no total."
            )
        if resultado.desconto_receita_historico_anual:
            texto_desconto += (
                f" O valor previsto ja esta liquido de {fmt_moeda(resultado.desconto_receita_historico_anual / 12)} "
                "por mes em descontos identificados no campo de receita do historico (ex: isencoes, compensacoes "
                "bancarias), tratados como uma deducao da arrecadacao esperada."
            )
        texto = (
            f"A arrecadacao mensal prevista para o proximo periodo e de {fmt_moeda(resultado.arrecadacao_prevista_mensal)}, "
            f"com base no rateio, fundo de reserva e demais arrecadacoes.{texto_desconto} "
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
    _bloco_assinatura(pdf, resultado)


def _pagina_despesas(pdf: RelatorioPDF, resultado):
    pdf.add_page()
    pdf.titulo_pagina("3. Despesas", icone=ICONE_DESPESAS)

    totais = _total_por_classificacao(resultado.despesas_classificadas)
    total_historico = totais["ordinaria"] + totais["extraordinaria"]
    pct_ordinaria = totais["ordinaria"] / total_historico if total_historico else 0.0
    pct_extraordinaria = 1 - pct_ordinaria if total_historico else 0.0

    _cartoes_estatisticas(
        pdf,
        [
            ("Ordinarias (recorrente ou anual)", fmt_moeda(totais["ordinaria"])),
            ("Extraordinarias (total anual)", fmt_moeda(totais["extraordinaria"])),
            ("Total apurado no periodo", fmt_moeda(resultado.total_despesas_historico)),
        ],
        colunas=3,
    )

    pdf.ln(2)
    # Grafico em barras horizontais (em vez de pizza) - categorias pequenas
    # nao tem mais o rotulo/percentual sobreposto, e a altura da imagem fica
    # bem menor que a pizza quadrada anterior.
    largura_grafico = _largura_util(pdf)
    pdf.imagem_temporaria(
        grafico_despesas_por_categoria_pai(resultado),
        x=pdf.l_margin,
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
            f"No historico dos ultimos 12 meses, {fmt_pct(pct_ordinaria)} da despesa foi ordinaria "
            f"(recorrente) e {fmt_pct(pct_extraordinaria)} foi extraordinaria (eventual).\n\n"
            "Criterio: despesas ordinarias sao recorrentes, com regularidade mensal; despesas "
            "extraordinarias sao eventuais, sem garantia de que se repitam no proximo periodo.\n\n"
            f"Das {qtd_total} subcategorias de despesa analisadas, {qtd_ordinarias} foram classificadas como "
            f"ordinarias e {qtd_extraordinarias} como extraordinarias. Despesas extraordinarias nao devem compor "
            "a base de calculo do reajuste, ja que nao ha garantia de que se repitam no proximo periodo."
        )
    else:
        texto = "Nao ha dados de despesa suficientes no historico para esta analise."

    _caixa_consideracoes(pdf, texto)
    _bloco_assinatura(pdf, resultado)


def _pagina_inadimplencia(pdf: RelatorioPDF, resultado):
    pdf.add_page()
    pdf.titulo_pagina("4. Inadimplencia", icone=ICONE_INADIMPLENCIA)

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
    # Quando nao ha dados suficientes para o grafico de evolucao por
    # competencia (ex: relatorio de inadimplentes sem lista de unidades, so
    # com o percentual geral), ainda mostra um indicador visual simples do
    # percentual apurado, em vez de deixar a pagina sem nenhum grafico.
    tem_grafico_indicador = not tem_grafico and resultado.percentual_inadimplencia > 0

    _cartoes_estatisticas(
        pdf,
        [
            ("Percentual de inadimplencia apurado", fmt_pct(resultado.percentual_inadimplencia)),
            ("Valor principal em aberto", fmt_moeda(resultado.inadimplencia_valor_total)),
        ],
    )
    pdf.ln(2)

    if tem_grafico:
        # Largura reduzida (nao a pagina toda) para sobrar espaco vertical
        # para a caixa de considerações e a tabela por unidade, que também
        # precisam caber na mesma página sempre que possível.
        largura_grafico = _largura_util(pdf) * 0.65
        pdf.imagem_temporaria(
            grafico_evolucao_inadimplencia(resultado), w=largura_grafico, x=pdf.l_margin + (_largura_util(pdf) - largura_grafico) / 2
        )
        pdf.ln(3)
    elif tem_grafico_indicador:
        largura_grafico = _largura_util(pdf) * 0.65
        pdf.imagem_temporaria(
            grafico_indicador_inadimplencia(resultado), w=largura_grafico, x=pdf.l_margin + (_largura_util(pdf) - largura_grafico) / 2
        )
        pdf.ln(3)

    partes_texto = [
        f"O condominio apresenta {fmt_pct(resultado.percentual_inadimplencia)} de inadimplencia apurada, "
        f"totalizando {fmt_moeda(resultado.inadimplencia_valor_total)} de valor principal em aberto "
        "(sem juros, multa ou honorarios)."
    ]
    if qtd_unidades == 0:
        partes_texto.append(
            "Nao ha unidades inadimplentes identificadas no relatorio de inadimplentes enviado."
        )
        if tem_grafico_indicador:
            partes_texto.append(
                "O grafico acima ilustra esse percentual em relacao ao total - nao ha dados suficientes no "
                "relatorio de inadimplentes enviado para detalhar a concentracao por mes de competencia."
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
            "A tabela abaixo detalha o valor total em aberto e a quantidade de meses em atraso de cada unidade."
        )

    _caixa_consideracoes(pdf, " ".join(partes_texto))

    if tem_unidades:
        pdf.ln(3)
        _tabela_unidades_inadimplentes(pdf, resultado.inadimplencia_valor_por_unidade)

    _bloco_assinatura(pdf, resultado)


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

    Usa a mesma base do calculo automatico do reajuste (rateio + fundo de
    reserva + outras arrecadacoes, sem receitas extraordinarias/taxas extras;
    despesas ordinarias, sem despesas extraordinarias/eventuais), para o
    Balanco e o Reajuste sempre concordarem sobre haver ou nao deficit.

    receita_rateio_necessaria, fundo_reserva_valor e cada item de
    outras_arrecadacoes_detalhe sao valores MENSAIS (mesma convencao de
    ConfiguracaoArrecadacao, usada tambem em arrecadacao_prevista_mensal) -
    por isso sao multiplicados por 12 aqui.

    O saldo final NAO soma o reajuste sugerido: o Balanco mede se a operacao
    ordinaria (sem reajuste) fecha em superavit ou deficit. Um deficit aqui e
    justamente o sinal de que ha reajuste a propor - a pagina/aba de Reajuste
    e a unica que apresenta o percentual em si."""
    receita_itens = [("Rateio mensal", resultado.receita_rateio_necessaria * 12)]
    if resultado.possui_fundo_reserva:
        receita_itens.append(("Fundo de reserva", resultado.fundo_reserva_valor * 12))
    for nome, valor in resultado.outras_arrecadacoes_detalhe:
        receita_itens.append((nome, valor * 12))
    if resultado.desconto_receita_historico_anual:
        receita_itens.append(("Descontos identificados no historico de receitas", -resultado.desconto_receita_historico_anual))

    receita_total = sum(valor for _, valor in receita_itens)
    despesas_total = _total_por_classificacao(resultado.despesas_classificadas)["ordinaria"]
    inadimplencia_valor = resultado.percentual_inadimplencia * receita_total
    total_geral = despesas_total + inadimplencia_valor
    saldo_final = receita_total - total_geral
    return {
        "receita_itens": receita_itens,
        "receita_total": receita_total,
        "despesas_total": despesas_total,
        "inadimplencia_valor": inadimplencia_valor,
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


def _tabela_unidades_inadimplentes(pdf: RelatorioPDF, df):
    """Desenha a tabela de unidades inadimplentes (unidade | valor em aberto |
    meses em atraso). Com poucas unidades usa uma coluna unica; com muitas,
    divide em DUAS colunas lado a lado (metade das unidades em cada) para a
    pagina de Inadimplencia caber inteira numa unica pagina - numeros,
    grafico, consideracoes e o detalhamento por unidade juntos."""
    registros = [
        (str(l["unidade"]), fmt_moeda(l["valor_total"]), str(int(l["meses_em_atraso"])))
        for _, l in df.iterrows()
    ]
    largura_util = _largura_util(pdf)
    altura = 5.5

    # Ate 8 unidades cabem numa coluna so sem apertar a pagina; acima disso,
    # duas colunas.
    duas_colunas = len(registros) > 8
    n_colunas = 2 if duas_colunas else 1
    gap = 8
    largura_coluna = (largura_util - gap * (n_colunas - 1)) / n_colunas
    # Sub-larguras dentro de cada coluna: unidade / valor / meses.
    sub = [largura_coluna * 0.42, largura_coluna * 0.34, largura_coluna * 0.24]
    align = ["L", "R", "R"]

    metade = (len(registros) + 1) // 2 if duas_colunas else len(registros)
    colunas_registros = [registros[:metade], registros[metade:]] if duas_colunas else [registros]

    x_base = pdf.l_margin
    y_topo = pdf.get_y()

    def desenhar_celulas(x, y, celulas, fill=None, cor_texto=None, bold=False):
        if fill:
            pdf.set_fill_color(*_hex_para_rgb(fill))
        pdf.set_text_color(*_hex_para_rgb(cor_texto)) if cor_texto else pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "B" if bold else "", 8)
        cx = x
        for texto, larg, al in zip(celulas, sub, align):
            pdf.set_xy(cx, y)
            pdf.cell(larg, altura, texto, align=al, fill=bool(fill))
            cx += larg
        pdf.set_text_color(0, 0, 0)

    for i_col, registros_col in enumerate(colunas_registros):
        x = x_base + i_col * (largura_coluna + gap)
        y = y_topo
        desenhar_celulas(x, y, ["Unidade", "Valor em aberto", "Meses"], fill=NAVY, cor_texto="#FFFFFF", bold=True)
        y += altura
        for celulas in registros_col:
            desenhar_celulas(x, y, celulas)
            y += altura

    linhas_por_coluna = max(len(c) for c in colunas_registros) + 1  # +1 do cabecalho
    pdf.set_xy(pdf.l_margin, y_topo + linhas_por_coluna * altura)


def _pagina_balanco(pdf: RelatorioPDF, resultado):
    """Reproduz a estrutura, cores e organizacao da planilha "ANALISE" que a
    Azul ja usa manualmente para preparar previsoes (Receita / Despesas por
    categoria), preenchida com os dados reais dos documentos anexados e da
    configuracao do formulario. Inadimplencia, reajuste e saldo final ja tem
    paginas proprias no relatorio, entao nao sao repetidos aqui."""
    pdf.add_page()
    pdf.titulo_pagina("5. Balanco Orcamentario Consolidado", icone=ICONE_BALANCO)

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

    despesas_previstas_ordinarias = _despesas_previstas_ordinarias(resultado)
    despesas_total = balanco["despesas_total"]
    despesas_por_categoria: dict[str, list] = {}
    for linha_despesa in despesas_previstas_ordinarias:
        despesas_por_categoria.setdefault(linha_despesa.categoria_pai, []).append(linha_despesa)

    _linha_ledger(pdf, larguras, ["DESPESAS", "Anual", "Mensal", "% do Total"], fill=FILL_DESPESAS, cor_texto="#FFFFFF", bold=True)
    for categoria_pai, linhas_despesa in despesas_por_categoria.items():
        _linha_ledger(pdf, larguras, [categoria_pai.upper(), "", "", ""], fill=FILL_SUBGRUPO, bold=True)
        subtotal = 0.0
        for linha_despesa in linhas_despesa:
            pct = linha_despesa.valor_historico / despesas_total if despesas_total else 0.0
            _linha_ledger(
                pdf, larguras,
                [linha_despesa.subcategoria, fmt_moeda(linha_despesa.valor_historico),
                 fmt_moeda(linha_despesa.valor_historico / 12), fmt_pct(pct)],
                cor_texto=COR_TEXTO_DESPESA,
            )
            subtotal += linha_despesa.valor_historico
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
    pdf.ln(6)
    _bloco_assinatura(pdf, resultado)


def _pagina_reajuste(pdf: RelatorioPDF, resultado, ultima_pagina: bool = True):
    pdf.add_page()
    pdf.titulo_pagina("6. Reajuste", icone=ICONE_REAJUSTE)

    largura_util = _largura_util(pdf)
    pdf.set_fill_color(*_hex_para_rgb(NAVY))
    # Caixa de destaque um pouco mais compacta (era 40mm) - junto com a fonte
    # menor nas caixas de consideracoes abaixo, deixa folga para o bloco
    # grande de assinatura ancorado no rodape desta pagina (que e a ultima
    # quando nao ha reajuste aplicado), sem empurrar nada para outra pagina.
    altura_destaque = 32
    y_destaque = pdf.get_y()
    pdf.rect(pdf.l_margin, y_destaque, largura_util, altura_destaque, style="F", round_corners=True, corner_radius=4)

    pdf.set_xy(pdf.l_margin, y_destaque + 5)
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(largura_util, 6, "Percentual de reajuste proposto", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_xy(pdf.l_margin, y_destaque + 11)
    pdf.set_font("Helvetica", "B", 32)
    pdf.set_text_color(*_hex_para_rgb(CYAN))
    pdf.cell(largura_util, 18, fmt_pct(resultado.percentual_reajuste_automatico), align="C")
    pdf.set_text_color(0, 0, 0)

    pdf.set_xy(pdf.l_margin, y_destaque + altura_destaque + 6)
    if resultado.percentual_reajuste_automatico > 0:
        _badge(pdf, "REAJUSTE NECESSARIO", "#F25C54", icone=ICONE_INADIMPLENCIA)
    else:
        _badge(pdf, "SEM REAJUSTE NECESSARIO", "#2E7D5B", icone=ICONE_CHECK)
    pdf.ln(8)

    totais_receitas = _total_por_classificacao(resultado.receitas_classificadas)
    totais_despesas = _total_por_classificacao(resultado.despesas_classificadas)

    receita_total = resultado.receita_total_anual_base_reajuste
    despesas_ordinarias = totais_despesas["ordinaria"]
    inadimplencia_valor = resultado.percentual_inadimplencia * receita_total
    resultado_geral = receita_total - despesas_ordinarias - inadimplencia_valor
    texto_reajuste = (
        "Criterio tecnico: o percentual de reajuste e apurado comparando a receita total prevista (rateio + "
        "fundo de reserva + outras arrecadacoes, anualizados - sem receitas extraordinarias ou "
        "taxas extras do historico, que nao entram nessa conta) com as despesas ORDINARIAS apuradas no periodo "
        "avaliado (12 meses, sem despesas extraordinarias/eventuais) e com a inadimplencia esperada.\n\n"
        f"Receita total apurada: {fmt_moeda(receita_total)}. Despesas ordinarias apuradas: "
        f"{fmt_moeda(despesas_ordinarias)}. Inadimplencia esperada ({fmt_pct(resultado.percentual_inadimplencia)} "
        f"da receita total): {fmt_moeda(inadimplencia_valor)}. Resultado (receita total menos despesas "
        f"ordinarias menos inadimplencia): {fmt_moeda(resultado_geral)}."
    )
    if resultado_geral >= 0:
        texto_reajuste += (
            "\n\nComo o resultado e maior ou igual a zero, a receita total ja cobre integralmente as "
            "despesas ordinarias do periodo e a inadimplencia esperada - nao ha deficit a equacionar, portanto "
            "nao ha justificativa tecnica para propor reajuste. Elevar a taxa condominial nesse cenario oneraria "
            "os condominos sem necessidade comprovada pelos numeros do periodo avaliado."
        )
    else:
        deficit = despesas_ordinarias + inadimplencia_valor - receita_total
        texto_reajuste += (
            f"\n\nComo o resultado e negativo, ha um deficit de {fmt_moeda(deficit)}: as despesas ordinarias "
            "somadas a inadimplencia esperada superam a receita total do periodo. O percentual de reajuste "
            f"proposto ({fmt_pct(resultado.percentual_reajuste_automatico)}) e exatamente esse deficit dividido "
            "pela receita total apurada - aplicado a receita atual, o valor resultante passa a cobrir as "
            "despesas ordinarias e a inadimplencia esperada sem sobra nem falta, equilibrando a operacao "
            "recorrente do condominio."
        )
    receita_extraordinaria = totais_receitas["extraordinaria"]
    despesa_extraordinaria = totais_despesas["extraordinaria"]
    texto_atencao = (
        "As receitas extraordinarias/taxas extras e as despesas extraordinarias (eventuais, sem recorrencia "
        "mensal) ficam de fora do calculo do reajuste acima, "
        "por nao haver garantia de que se repitam no proximo periodo - mas merecem atencao separada pelo "
        "impacto que tem no caixa do condominio quando ocorrem.\n\n"
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

    # Lado a lado (nao empilhadas) para as duas caixas ficarem sempre juntas
    # na mesma pagina - a altura total consumida passa a ser a da caixa mais
    # alta, nao a soma das duas. Fonte um pouco menor (9pt) e uma reserva no
    # rodape (`reserva_inferior`) garantem espaco para o bloco grande de
    # assinatura quando esta e a ultima pagina do relatorio, sem empurrar as
    # caixas nem a assinatura para uma pagina extra.
    reserva = 42 if ultima_pagina else 0
    _caixas_lado_a_lado(
        pdf,
        [
            ("Como o reajuste foi apurado", texto_reajuste),
            ("Pontos de atencao: extraordinarias e impacto no caixa", texto_atencao),
        ],
        font_size=9,
        line_height=4.8,
        reserva_inferior=reserva,
    )

    _bloco_assinatura(pdf, resultado, final=ultima_pagina)


def _pagina_taxas_reajustadas(pdf: RelatorioPDF, resultado):
    """Só chamada quando ha reajuste aplicado - mostra as taxas resultantes
    (rateio + fundo de reserva, ja com o percentual escolhido pelo usuario) e
    as outras arrecadacoes configuradas, somadas sem reajuste."""
    pdf.add_page()
    pdf.titulo_pagina("7. Taxas Reajustadas", icone=ICONE_REAJUSTE)

    total_mensal = (
        resultado.rateio_reajustado + resultado.fundo_reserva_reajustado + resultado.total_outras_arrecadacoes_previsto
    )
    itens = [
        ("Rateio mensal reajustado", fmt_moeda(resultado.rateio_reajustado)),
        (
            "Fundo de reserva (reajustado)" if resultado.reajuste_aplicado_ao_fundo_reserva else "Fundo de reserva (mantido)",
            fmt_moeda(resultado.fundo_reserva_reajustado),
        ),
        ("Outras arrecadações", fmt_moeda(resultado.total_outras_arrecadacoes_previsto)),
        ("Total mensal", fmt_moeda(total_mensal)),
    ]
    _cartoes_estatisticas(pdf, itens, colunas=2)
    pdf.ln(4)

    texto = (
        f"As taxas acima refletem o percentual de reajuste de {fmt_pct(resultado.percentual_reajuste_aplicado)} "
        "aplicado ao rateio mensal"
    )
    if resultado.reajuste_aplicado_ao_fundo_reserva:
        texto += " e ao fundo de reserva, "
    else:
        texto += ", mantendo o fundo de reserva sem alteração, "
    texto += (
        "somadas as outras arrecadações já configuradas (ex: água), que não recebem reajuste. O total mensal "
        "acima representa a nova taxa condominial resultante, a partir da vigência do reajuste."
    )
    _caixa_consideracoes(pdf, texto, titulo="Taxas resultantes após o reajuste")

    taxas_por_unidade = resultado.taxas_reajustadas_por_unidade
    if taxas_por_unidade is not None and not taxas_por_unidade.empty:
        pdf.ln(4)
        largura_util = _largura_util(pdf)
        # A coluna "Fracao" so faz sentido quando o rateio foi configurado
        # por fracao ideal ou indexador - nos modos "igual"/"tipos" a fracao
        # e so o peso derivado (1/N ou por tipo), nao uma informacao que o
        # condominio configurou de verdade, entao a tabela mostra so
        # unidade e valor da taxa nesses modos.
        mostrar_fracao = resultado.rateio_modo in ("fracao_ideal", "indexador")
        if mostrar_fracao:
            larguras = [largura_util * 0.4, largura_util * 0.3, largura_util * 0.3]
            _linha_ledger(
                pdf, larguras, ["Unidade", "Fração", "Valor da taxa"],
                fill=NAVY, cor_texto="#FFFFFF", bold=True,
            )
            for _, linha in taxas_por_unidade.iterrows():
                _linha_ledger(
                    pdf, larguras,
                    [str(linha["unidade"]), fmt_pct(linha["fracao"]), fmt_moeda(linha["valor_taxa"])],
                )
        else:
            larguras = [largura_util * 0.6, largura_util * 0.4]
            _linha_ledger(
                pdf, larguras, ["Unidade", "Valor da taxa"],
                fill=NAVY, cor_texto="#FFFFFF", bold=True,
            )
            for _, linha in taxas_por_unidade.iterrows():
                _linha_ledger(
                    pdf, larguras,
                    [str(linha["unidade"]), fmt_moeda(linha["valor_taxa"])],
                )

    pdf.ln(6)
    _bloco_assinatura(pdf, resultado, final=True)


def gerar_pdf_previsao(resultado) -> bytes:
    """Gera o PDF final (capa, arrecadacoes, despesas, inadimplencia,
    balanco consolidado, reajuste, e - quando ha reajuste aplicado - uma
    pagina extra com as taxas reajustadas) e retorna os bytes prontos para
    download."""
    pdf = RelatorioPDF()
    pdf.arquivos_temp = []
    try:
        ha_taxas_reajustadas = resultado.percentual_reajuste_aplicado > 0
        _pagina_capa(pdf, resultado)
        _pagina_arrecadacoes(pdf, resultado)
        _pagina_despesas(pdf, resultado)
        _pagina_inadimplencia(pdf, resultado)
        _pagina_balanco(pdf, resultado)
        _pagina_reajuste(pdf, resultado, ultima_pagina=not ha_taxas_reajustadas)
        if ha_taxas_reajustadas:
            _pagina_taxas_reajustadas(pdf, resultado)
        return bytes(pdf.output())
    finally:
        import os

        for caminho in pdf.arquivos_temp:
            try:
                os.remove(caminho)
            except OSError:
                pass
