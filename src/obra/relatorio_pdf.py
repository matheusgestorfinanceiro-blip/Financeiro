"""Monta o relatório final em PDF da obra: capa, resumo executivo, gastos por
categoria, evolução no tempo, detalhamento de todos os lançamentos, fotos da
evolução da obra, notas fiscais e comprovantes (quando houver) e
considerações finais sobre o andamento/finalização da obra."""
import datetime
import io
import os
import tempfile
from pathlib import Path

import fitz  # PyMuPDF
from fpdf import FPDF
from PIL import Image

from src.obra.calculo import (
    fmt_data_br,
    percentual_orcamento,
    periodo_coberto,
    resumo_proprietario_inquilino,
    total_geral,
)
from src.obra.graficos import (
    CYAN,
    GRAY,
    NAVY,
    grafico_evolucao_gastos,
    grafico_gastos_por_categoria,
)
from src.ui.formatacao import fmt_moeda, fmt_pct

CARD_BG = "#EEF4FA"
DESTAQUE_BG = "#E4F5FA"

COLUNAS_TABELA = [
    ("Data", 20),
    ("Categoria", 36),
    ("Descrição", 58),
    ("Fornecedor", 34),
    ("Valor", 28),
]


def _hex_para_rgb(cor_hex: str) -> tuple[int, int, int]:
    cor_hex = cor_hex.lstrip("#")
    return tuple(int(cor_hex[i : i + 2], 16) for i in (0, 2, 4))


class RelatorioObraPDF(FPDF):
    arquivos_temp: list[str]

    def header(self):
        if self.page_no() == 1:
            return
        self.set_xy(self.w - 70, 8)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*_hex_para_rgb(GRAY))
        self.cell(60, 6, "RELATORIO DE OBRA", align="R")
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


def _largura_util(pdf: RelatorioObraPDF) -> float:
    return pdf.w - pdf.l_margin - pdf.r_margin


def _cartoes_estatisticas(pdf: RelatorioObraPDF, itens: list[tuple[str, str]], colunas: int = 2):
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


def _caixa_consideracoes(pdf: RelatorioObraPDF, texto: str, titulo: str = "Considerações"):
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
        pdf.set_text_color(*_hex_para_rgb(NAVY))
        pdf.cell(largura_util - 2 * padding, 6, titulo, new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(x + padding)

    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(largura_util - 2 * padding, 5.5, texto)

    pdf.set_xy(pdf.l_margin, y + altura_caixa + 8)


def _cabecalho_tabela(pdf: RelatorioObraPDF, colunas: list[tuple[str, float]]):
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(*_hex_para_rgb(NAVY))
    pdf.set_text_color(255, 255, 255)
    for nome, largura in colunas:
        pdf.cell(largura, 7, nome, fill=True, align="L")
    pdf.ln(7)
    pdf.set_text_color(0, 0, 0)


def _tabela_gastos(pdf: RelatorioObraPDF, df):
    largura_util = _largura_util(pdf)
    soma_larguras = sum(w for _, w in COLUNAS_TABELA)
    colunas = [(nome, largura / soma_larguras * largura_util) for nome, largura in COLUNAS_TABELA]

    _cabecalho_tabela(pdf, colunas)
    pdf.set_font("Helvetica", size=8)
    linha_par = False
    for gasto in df.itertuples():
        if pdf.get_y() + 6 > pdf.h - pdf.b_margin:
            pdf.add_page()
            _cabecalho_tabela(pdf, colunas)
            pdf.set_font("Helvetica", size=8)

        pdf.set_fill_color(*(_hex_para_rgb(CARD_BG) if linha_par else (255, 255, 255)))
        linha_par = not linha_par

        valores = [
            fmt_data_br(gasto.data),
            str(gasto.categoria)[:24],
            str(gasto.descricao)[:36],
            str(gasto.fornecedor)[:22],
            fmt_moeda(float(gasto.valor)),
        ]
        for (_, largura), valor in zip(colunas, valores):
            pdf.cell(largura, 6, valor, fill=True, align="L")
        pdf.ln(6)


def _pagina_capa(pdf: RelatorioObraPDF, dados_obra, df_gastos):
    pdf.add_page()
    pdf.set_fill_color(*_hex_para_rgb(NAVY))
    pdf.rect(0, 0, pdf.w, pdf.h, style="F")

    pdf.set_text_color(*_hex_para_rgb(CYAN))
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_xy(20, 85)
    pdf.cell(0, 8, "RELATORIO DE OBRA", new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_x(20)
    pdf.multi_cell(pdf.w - 40, 12, dados_obra.nome_obra or "Reforma residencial", align="L")

    pdf.ln(3)
    pdf.set_font("Helvetica", size=12)
    if dados_obra.endereco:
        pdf.set_x(20)
        pdf.multi_cell(pdf.w - 40, 6.5, dados_obra.endereco)
    if dados_obra.proprietario:
        pdf.set_x(20)
        pdf.cell(0, 6.5, f"Preparado para: {dados_obra.proprietario}", new_x="LMARGIN", new_y="NEXT")

    periodo = periodo_coberto(df_gastos)
    pdf.set_x(20)
    if periodo:
        pdf.cell(0, 6.5, f"Periodo dos gastos registrados: {periodo[0]} a {periodo[1]}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(20)
    pdf.cell(0, 6.5, f"Status atual da obra: {dados_obra.status_obra}", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(pdf.h - 30)
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(*_hex_para_rgb(GRAY))
    pdf.set_x(20)
    data_emissao = datetime.date.today().strftime("%d/%m/%Y")
    pdf.cell(0, 6, f"Relatorio gerado em {data_emissao}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)


def _pagina_resumo(pdf: RelatorioObraPDF, dados_obra, df_gastos, numero: int):
    pdf.add_page()
    pdf.titulo_pagina(f"{numero}. Resumo executivo")

    total = total_geral(df_gastos)
    pct_orcamento = percentual_orcamento(total, dados_obra.orcamento_previsto)

    itens = [
        ("Total gasto ate o momento", fmt_moeda(total)),
        ("Numero de lancamentos", str(len(df_gastos))),
    ]
    if dados_obra.orcamento_previsto:
        itens.insert(1, ("Orcamento previsto", fmt_moeda(dados_obra.orcamento_previsto)))
        if pct_orcamento is not None:
            itens.insert(2, ("Percentual do orcamento utilizado", fmt_pct(pct_orcamento)))

    _cartoes_estatisticas(pdf, itens, colunas=2)
    pdf.ln(4)

    texto = f"A obra \"{dados_obra.nome_obra or 'sem nome informado'}\" encontra-se com status \"{dados_obra.status_obra}\"."
    if dados_obra.data_inicio:
        texto += f" Inicio em {fmt_data_br(dados_obra.data_inicio)}."
    if dados_obra.previsao_termino:
        texto += f" Previsao de termino em {fmt_data_br(dados_obra.previsao_termino)}."

    if dados_obra.orcamento_previsto and pct_orcamento is not None:
        if pct_orcamento > 1:
            texto += (
                f" O total gasto ja ultrapassa o orcamento previsto em "
                f"{fmt_moeda(total - dados_obra.orcamento_previsto)} "
                f"({fmt_pct(pct_orcamento - 1)} acima do previsto)."
            )
        else:
            texto += (
                f" Ainda ha {fmt_moeda(dados_obra.orcamento_previsto - total)} de saldo dentro do "
                "orcamento previsto."
            )

    _caixa_consideracoes(pdf, texto, titulo="Situacao geral")


def _pagina_categoria(pdf: RelatorioObraPDF, df_gastos, numero: int):
    pdf.add_page()
    pdf.titulo_pagina(f"{numero}. Gastos por categoria")

    largura_grafico = 160
    pdf.imagem_temporaria(grafico_gastos_por_categoria(df_gastos), x=(pdf.w - largura_grafico) / 2, w=largura_grafico)


def _pagina_evolucao(pdf: RelatorioObraPDF, df_gastos, numero: int):
    pdf.add_page()
    pdf.titulo_pagina(f"{numero}. Evolucao dos gastos ao longo do tempo")

    pdf.imagem_temporaria(grafico_evolucao_gastos(df_gastos), w=_largura_util(pdf))
    pdf.ln(3)

    texto = (
        "O grafico acima mostra o valor gasto em cada mes (barras, eixo da esquerda) e o total acumulado "
        "da obra ao longo do tempo (linha, eixo da direita), com os valores de cada ponto em destaque, "
        "permitindo acompanhar o ritmo de desembolso desde o inicio dos registros."
    )
    _caixa_consideracoes(pdf, texto)


def _pagina_detalhamento(pdf: RelatorioObraPDF, df_gastos, numero: int):
    pdf.add_page()
    pdf.titulo_pagina(f"{numero}. Detalhamento de todos os lancamentos")
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(*_hex_para_rgb(GRAY))
    pdf.multi_cell(_largura_util(pdf), 5, "Lista de todos os itens comprados nesta obra.")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)
    _tabela_gastos(pdf, df_gastos.sort_values("data"))


def _preparar_imagem_para_exibir(referencia: str, dados: bytes) -> bytes:
    """Se o arquivo for um PDF (comprovante anexado em PDF), converte a
    primeira página numa imagem para servir de pré-visualização no relatório."""
    if Path(referencia).suffix.lower() == ".pdf":
        with fitz.open(stream=dados, filetype="pdf") as documento:
            pixmap = documento[0].get_pixmap(dpi=150)
            return pixmap.tobytes("png")
    return dados


def _dimensionar_para_celula(largura_px: int, altura_px: int, largura_max: float, altura_max: float) -> tuple[float, float]:
    """Calcula w/h (em mm) para a imagem caber dentro de uma célula
    largura_max x altura_max, preservando a proporção original."""
    escala = min(largura_max / largura_px, altura_max / altura_px)
    return largura_px * escala, altura_px * escala


def _pagina_fotos(pdf: RelatorioObraPDF, fotos_df, obter_bytes_foto, numero: int):
    largura_util = _largura_util(pdf)
    colunas = 2  # ate 3 linhas x 2 colunas = 6 fotos por pagina
    gap_col, gap_linha = 6, 6
    altura_max_img = 62
    altura_legenda = 9
    largura_celula = (largura_util - gap_col * (colunas - 1)) / colunas
    altura_linha = altura_max_img + altura_legenda + gap_linha

    pdf.add_page()
    pdf.titulo_pagina(f"{numero}. Fotos da evolucao da obra")
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(*_hex_para_rgb(GRAY))
    pdf.multi_cell(largura_util, 5, "Fotos organizadas na ordem cronologica de execucao da obra.")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    fotos = list(fotos_df.itertuples())
    for i in range(0, len(fotos), colunas):
        linha_fotos = fotos[i : i + colunas]

        if pdf.get_y() + altura_linha > pdf.h - pdf.b_margin:
            pdf.add_page()
        y_linha = pdf.get_y()

        for col, foto in enumerate(linha_fotos):
            x_celula = pdf.l_margin + col * (largura_celula + gap_col)
            try:
                dados_imagem = _preparar_imagem_para_exibir(foto.nome_arquivo, obter_bytes_foto(foto.nome_arquivo))
                with Image.open(io.BytesIO(dados_imagem)) as imagem:
                    largura_px, altura_px = imagem.size
                w, h = _dimensionar_para_celula(largura_px, altura_px, largura_celula, altura_max_img)
            except Exception:
                continue

            x_img = x_celula + (largura_celula - w) / 2
            y_img = y_linha + (altura_max_img - h) / 2
            pdf.image(io.BytesIO(dados_imagem), x=x_img, y=y_img, w=w, h=h)

            legenda = f"{fmt_data_br(foto.data)}" + (f" - {foto.legenda}" if foto.legenda else "")
            pdf.set_xy(x_celula, y_linha + altura_max_img + 1)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*_hex_para_rgb(NAVY))
            pdf.multi_cell(largura_celula, 4, legenda, align="C")
            pdf.set_text_color(0, 0, 0)

        pdf.set_xy(pdf.l_margin, y_linha + altura_linha)


def _pagina_notas_fiscais(pdf: RelatorioObraPDF, notas_df, obter_bytes_nota_fiscal, numero: int):
    largura_util = _largura_util(pdf)
    colunas = 2  # ate 2 linhas x 2 colunas = 4 notas fiscais por pagina
    gap_col, gap_linha = 8, 8
    altura_max_img = 95
    altura_legenda = 9
    largura_celula = (largura_util - gap_col * (colunas - 1)) / colunas
    altura_linha = altura_max_img + altura_legenda + gap_linha

    pdf.add_page()
    pdf.titulo_pagina(f"{numero}. Notas fiscais e comprovantes")
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(*_hex_para_rgb(GRAY))
    pdf.multi_cell(largura_util, 5, "Notas fiscais e comprovantes anexados a esta obra.")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    notas = list(notas_df.itertuples())
    for i in range(0, len(notas), colunas):
        linha_notas = notas[i : i + colunas]

        if pdf.get_y() + altura_linha > pdf.h - pdf.b_margin:
            pdf.add_page()
        y_linha = pdf.get_y()

        for col, nota in enumerate(linha_notas):
            x_celula = pdf.l_margin + col * (largura_celula + gap_col)
            try:
                dados_imagem = _preparar_imagem_para_exibir(
                    nota.nome_arquivo, obter_bytes_nota_fiscal(nota.nome_arquivo)
                )
                with Image.open(io.BytesIO(dados_imagem)) as imagem:
                    largura_px, altura_px = imagem.size
                w, h = _dimensionar_para_celula(largura_px, altura_px, largura_celula, altura_max_img)
            except Exception:
                pdf.set_xy(x_celula, y_linha + altura_max_img / 2 - 4)
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(*_hex_para_rgb(GRAY))
                pdf.multi_cell(largura_celula, 5, "(nao foi possivel carregar o arquivo)", align="C")
                pdf.set_text_color(0, 0, 0)
                continue

            x_img = x_celula + (largura_celula - w) / 2
            y_img = y_linha + (altura_max_img - h) / 2
            pdf.image(io.BytesIO(dados_imagem), x=x_img, y=y_img, w=w, h=h)

            legenda = fmt_data_br(nota.data) + (f" - {nota.legenda}" if nota.legenda else "")
            pdf.set_xy(x_celula, y_linha + altura_max_img + 1)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*_hex_para_rgb(NAVY))
            pdf.multi_cell(largura_celula, 4, legenda, align="C")
            pdf.set_text_color(0, 0, 0)

        pdf.set_xy(pdf.l_margin, y_linha + altura_linha)


def _pagina_consideracoes_finais(pdf: RelatorioObraPDF, dados_obra, df_gastos, numero: int):
    pdf.add_page()
    pdf.titulo_pagina(f"{numero}. Consideracoes finais")

    total = total_geral(df_gastos)
    texto = (
        f"Ate a data de emissao deste relatorio, foram registrados {len(df_gastos)} lancamentos de gastos, "
        f"totalizando {fmt_moeda(total)}. O status atual da obra e \"{dados_obra.status_obra}\"."
    )
    if dados_obra.status_obra == "Concluída":
        texto += " A obra foi concluida e este relatorio reflete o total definitivo investido na reforma."
    _caixa_consideracoes(pdf, texto, titulo="Andamento e finalizacao")

    if dados_obra.orcamento_previsto:
        divisao = resumo_proprietario_inquilino(total, dados_obra.orcamento_previsto)
        texto_divisao = (
            f"Do total gasto de {fmt_moeda(total)}, {fmt_moeda(divisao['proprietario'])} correspondem ao "
            f"valor previsto e sao de responsabilidade do proprietario."
        )
        if divisao["inquilino"] > 0:
            texto_divisao += (
                f" A diferenca de {fmt_moeda(divisao['inquilino'])}, que ultrapassa o valor previsto, "
                "corresponde ao gasto de responsabilidade do inquilino."
            )
        else:
            texto_divisao += " O total gasto nao ultrapassou o valor previsto, nao havendo gasto adicional do inquilino."
        _caixa_consideracoes(pdf, texto_divisao, titulo="Divisao entre proprietario e inquilino")

    if dados_obra.observacoes_gerais:
        _caixa_consideracoes(pdf, dados_obra.observacoes_gerais, titulo="Observacoes do responsavel pela obra")


def gerar_pdf_obra(
    dados_obra,
    df_gastos,
    fotos_df=None,
    obter_bytes_foto=None,
    tipo_relatorio: str = "parcial",
    notas_fiscais_df=None,
    obter_bytes_nota_fiscal=None,
) -> bytes:
    """Gera o relatorio em PDF (capa, resumo, gastos por categoria, evolucao no
    tempo, detalhamento completo, fotos da evolucao da obra, notas fiscais e
    comprovantes quando houver, e consideracoes finais) e retorna os bytes
    prontos para download.

    `obter_bytes_foto`/`obter_bytes_nota_fiscal` são funções que recebem a
    referência salva (nome de arquivo local ou ID do Drive) e devolvem os
    bytes do arquivo - o relatório não precisa saber onde cada arquivo está
    guardado. tipo_relatorio "parcial" pode ser gerado com ou sem fotos. Ja o
    "final" exige ao menos uma foto de evolucao cadastrada."""
    tem_fotos = fotos_df is not None and not fotos_df.empty
    tem_notas_fiscais = notas_fiscais_df is not None and not notas_fiscais_df.empty

    if tipo_relatorio == "final" and not tem_fotos:
        raise ValueError("Inclua ao menos uma foto de evolucao da obra para gerar o relatorio final.")

    pdf = RelatorioObraPDF()
    pdf.arquivos_temp = []
    try:
        numero = 1
        _pagina_capa(pdf, dados_obra, df_gastos)
        _pagina_resumo(pdf, dados_obra, df_gastos, numero)
        numero += 1
        _pagina_categoria(pdf, df_gastos, numero)
        numero += 1
        _pagina_evolucao(pdf, df_gastos, numero)
        numero += 1
        _pagina_detalhamento(pdf, df_gastos, numero)
        numero += 1
        if tem_fotos:
            _pagina_fotos(pdf, fotos_df, obter_bytes_foto, numero)
            numero += 1
        if tem_notas_fiscais:
            _pagina_notas_fiscais(pdf, notas_fiscais_df, obter_bytes_nota_fiscal, numero)
            numero += 1
        _pagina_consideracoes_finais(pdf, dados_obra, df_gastos, numero)
        return bytes(pdf.output())
    finally:
        for caminho in pdf.arquivos_temp:
            try:
                os.remove(caminho)
            except OSError:
                pass
