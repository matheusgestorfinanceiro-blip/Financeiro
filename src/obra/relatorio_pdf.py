"""Monta o relatório final em PDF da obra: capa, resumo executivo, gastos por
categoria, evolução no tempo, detalhamento de todos os lançamentos, fotos da
evolução da obra, anexos dos comprovantes (quando houver) e considerações
finais sobre o andamento/finalização da obra."""
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
    resumo_pagamento,
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
    ("Categoria", 34),
    ("Descrição", 52),
    ("Fornecedor", 30),
    ("Valor", 22),
    ("Status", 18),
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
            "Pago" if gasto.pago else "Pendente",
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
    pagamento = resumo_pagamento(df_gastos)
    pct_orcamento = percentual_orcamento(total, dados_obra.orcamento_previsto)

    itens = [
        ("Total gasto ate o momento", fmt_moeda(total)),
        ("Numero de lancamentos", str(len(df_gastos))),
        ("Ja pago", fmt_moeda(pagamento["pago"])),
        ("Pendente de pagamento", fmt_moeda(pagamento["pendente"])),
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

    if pagamento["pendente"] > 0:
        texto += f" Ha {fmt_moeda(pagamento['pendente'])} em pagamentos ainda pendentes."

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
    _tabela_gastos(pdf, df_gastos.sort_values("data"))


def _preparar_imagem_para_exibir(referencia: str, dados: bytes) -> bytes:
    """Se o arquivo for um PDF (comprovante anexado em PDF), converte a
    primeira página numa imagem para servir de pré-visualização no relatório."""
    if Path(referencia).suffix.lower() == ".pdf":
        with fitz.open(stream=dados, filetype="pdf") as documento:
            pixmap = documento[0].get_pixmap(dpi=150)
            return pixmap.tobytes("png")
    return dados


def _pagina_fotos(pdf: RelatorioObraPDF, fotos_df, obter_bytes_foto, numero: int):
    largura_util = _largura_util(pdf)

    pdf.add_page()
    pdf.titulo_pagina(f"{numero}. Fotos da evolucao da obra")
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(*_hex_para_rgb(GRAY))
    pdf.multi_cell(largura_util, 5, "Fotos organizadas na ordem cronologica de execucao da obra.")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    for foto in fotos_df.itertuples():
        try:
            dados_imagem = _preparar_imagem_para_exibir(foto.nome_arquivo, obter_bytes_foto(foto.nome_arquivo))
            with Image.open(io.BytesIO(dados_imagem)) as imagem:
                largura_px, altura_px = imagem.size
        except Exception:
            continue

        altura_imagem = largura_util * (altura_px / largura_px)
        altura_legenda = 8
        altura_bloco = altura_imagem + altura_legenda + 6

        if pdf.get_y() + altura_bloco > pdf.h - pdf.b_margin:
            pdf.add_page()

        pdf.image(io.BytesIO(dados_imagem), x=pdf.l_margin, w=largura_util)
        pdf.ln(1)

        legenda = f"{fmt_data_br(foto.data)}" + (f" - {foto.legenda}" if foto.legenda else "")
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_hex_para_rgb(NAVY))
        pdf.cell(largura_util, 6, legenda, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)


def _pagina_anexos(pdf: RelatorioObraPDF, df_gastos, obter_bytes_anexo, numero: int):
    largura_util = _largura_util(pdf)

    pdf.add_page()
    pdf.titulo_pagina(f"{numero}. Anexos dos comprovantes")
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(*_hex_para_rgb(GRAY))
    pdf.multi_cell(largura_util, 5, "Comprovantes anexados aos lancamentos desta obra.")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    com_anexo = df_gastos[df_gastos["anexo"].astype(str).str.strip() != ""]
    for referencia, grupo in com_anexo.groupby("anexo"):
        descricoes = ", ".join(grupo["descricao"].astype(str).tolist())
        total_grupo = float(grupo["valor"].sum())
        legenda = f"{descricoes} - {fmt_moeda(total_grupo)}"

        dados_imagem = None
        largura_imagem = altura_imagem = 0.0
        try:
            dados_imagem = _preparar_imagem_para_exibir(referencia, obter_bytes_anexo(referencia))
            with Image.open(io.BytesIO(dados_imagem)) as imagem:
                largura_px, altura_px = imagem.size
            altura_imagem = min(largura_util * (altura_px / largura_px), 130)
            largura_imagem = altura_imagem * (largura_px / altura_px)
        except Exception:
            dados_imagem = None

        linhas_legenda = pdf.multi_cell(largura_util, 5, legenda, dry_run=True, output="LINES")
        altura_bloco = altura_imagem + len(linhas_legenda) * 5 + 8

        if pdf.get_y() + altura_bloco > pdf.h - pdf.b_margin:
            pdf.add_page()

        if dados_imagem:
            pdf.image(io.BytesIO(dados_imagem), x=pdf.l_margin, w=largura_imagem)
            pdf.ln(1)
        else:
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(*_hex_para_rgb(GRAY))
            pdf.cell(largura_util, 6, "(nao foi possivel carregar o anexo)", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)

        pdf.set_font("Helvetica", size=9)
        pdf.multi_cell(largura_util, 5, legenda)
        pdf.ln(4)


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

    if dados_obra.observacoes_gerais:
        _caixa_consideracoes(pdf, dados_obra.observacoes_gerais, titulo="Observacoes do responsavel pela obra")


def gerar_pdf_obra(
    dados_obra,
    df_gastos,
    fotos_df=None,
    obter_bytes_foto=None,
    tipo_relatorio: str = "parcial",
    obter_bytes_anexo=None,
) -> bytes:
    """Gera o relatorio em PDF (capa, resumo, gastos por categoria, evolucao no
    tempo, detalhamento completo, fotos da evolucao da obra, anexos dos
    comprovantes quando houver, e consideracoes finais) e retorna os bytes
    prontos para download.

    `obter_bytes_foto`/`obter_bytes_anexo` são funções que recebem a
    referência salva (nome de arquivo local ou ID do Drive) e devolvem os
    bytes do arquivo - o relatório não precisa saber onde cada arquivo está
    guardado. tipo_relatorio "parcial" pode ser gerado com ou sem fotos. Ja o
    "final" exige ao menos uma foto de evolucao cadastrada."""
    tem_fotos = fotos_df is not None and not fotos_df.empty
    tem_anexos = (
        obter_bytes_anexo is not None
        and "anexo" in df_gastos.columns
        and (df_gastos["anexo"].astype(str).str.strip() != "").any()
    )

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
        if tem_anexos:
            _pagina_anexos(pdf, df_gastos, obter_bytes_anexo, numero)
            numero += 1
        _pagina_consideracoes_finais(pdf, dados_obra, df_gastos, numero)
        return bytes(pdf.output())
    finally:
        for caminho in pdf.arquivos_temp:
            try:
                os.remove(caminho)
            except OSError:
                pass
