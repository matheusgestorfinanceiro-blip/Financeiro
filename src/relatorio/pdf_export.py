"""Monta o relatório final em PDF: 5 páginas fixas (capa, arrecadações, despesas,
inadimplência, reajuste), com a marca da Azul Administradora no canto superior
direito de todas as páginas (exceto a capa, que já tem identidade visual própria)."""
import tempfile
from pathlib import Path

from fpdf import FPDF

from src.relatorio.graficos import (
    CYAN,
    GRAY,
    NAVY,
    grafico_despesas_ordinaria_x_extraordinaria,
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


def _cartoes_estatisticas(pdf: RelatorioPDF, itens: list[tuple[str, str]]):
    """Desenha uma grade de "cartões" (2 por linha) com um rótulo pequeno e um
    valor grande em destaque, no lugar de simples linhas de texto."""
    largura_util = _largura_util(pdf)
    gap = 6
    largura_cartao = (largura_util - gap) / 2
    altura_cartao = 24
    x_inicial = pdf.l_margin
    y_inicial = pdf.get_y()

    for i, (rotulo, valor) in enumerate(itens):
        col = i % 2
        linha = i // 2
        x = x_inicial + col * (largura_cartao + gap)
        y = y_inicial + linha * (altura_cartao + gap)

        pdf.set_fill_color(*_hex_para_rgb(CARD_BG))
        pdf.rect(x, y, largura_cartao, altura_cartao, style="F")

        pdf.set_xy(x + 4, y + 3)
        pdf.set_font("Helvetica", size=8.5)
        pdf.set_text_color(*_hex_para_rgb(GRAY))
        pdf.multi_cell(largura_cartao - 8, 4, rotulo)

        pdf.set_xy(x + 4, y + 13)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*_hex_para_rgb(NAVY))
        pdf.cell(largura_cartao - 8, 8, valor)
        pdf.set_text_color(0, 0, 0)

    linhas_de_cartoes = (len(itens) + 1) // 2
    pdf.set_xy(pdf.l_margin, y_inicial + linhas_de_cartoes * (altura_cartao + gap))


def _caixa_consideracoes(pdf: RelatorioPDF, texto: str, titulo: str = "Considerações da análise"):
    """Desenha uma caixa com fundo destacado em volta de um texto de análise,
    para chamar atenção de forma simples e objetiva."""
    largura_util = _largura_util(pdf)
    x = pdf.l_margin
    y = pdf.get_y()
    padding = 4

    pdf.set_font("Helvetica", "B", 10)
    altura_titulo = 6 if titulo else 0

    pdf.set_font("Helvetica", size=10)
    linhas = pdf.multi_cell(largura_util - 2 * padding, 5.5, texto, dry_run=True, output="LINES")
    altura_texto = len(linhas) * 5.5
    altura_caixa = altura_titulo + altura_texto + 2 * padding

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

    pdf.set_xy(pdf.l_margin, y + altura_caixa + 6)


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
            ("Ordinario (recorrente ou mensal)", fmt_moeda(totais["ordinaria"])),
            ("Extraordinario (eventual)", fmt_moeda(totais["extraordinaria"])),
            ("Arrecadacao prevista mensalmente", fmt_moeda(resultado.arrecadacao_prevista_mensal)),
            ("Outras receitas (identificadas no periodo)", fmt_moeda(resultado.total_outras_receitas_previsto)),
        ],
    )

    pdf.ln(2)
    pdf.imagem_temporaria(grafico_receitas_ordinaria_x_extraordinaria(resultado), w=90)
    pdf.ln(3)

    if total_historico:
        texto = (
            f"No historico dos ultimos 12 meses, {fmt_pct(pct_ordinaria)} da arrecadacao veio de fontes "
            f"ordinarias e recorrentes (como o rateio mensal), enquanto {fmt_pct(pct_extraordinaria)} "
            "veio de fontes extraordinarias ou eventuais (ex: juros, multas, receitas pontuais). A "
            f"arrecadacao mensal prevista para o proximo periodo e de {fmt_moeda(resultado.arrecadacao_prevista_mensal)}. "
            "Receitas eventuais nao devem ser usadas como base para o calculo do reajuste ou do rateio do "
            "proximo periodo, pois nao ha garantia de que se repitam."
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
            ("Ordinarias (recorrente ou mensal)", fmt_moeda(totais["ordinaria"])),
            ("Extraordinarias (eventuais)", fmt_moeda(totais["extraordinaria"])),
            ("Despesas totais previstas para 12 meses", fmt_moeda(resultado.total_despesas_previsto)),
            ("Total das despesas apuradas na analise", fmt_moeda(resultado.total_despesas_historico)),
        ],
    )

    pdf.ln(2)
    pdf.imagem_temporaria(grafico_despesas_ordinaria_x_extraordinaria(resultado), w=90)
    pdf.ln(3)

    if total_historico:
        texto = (
            f"No historico dos ultimos 12 meses, {fmt_pct(pct_ordinaria)} da despesa foi recorrente "
            f"(aparece de forma regular ao longo do ano) e {fmt_pct(pct_extraordinaria)} foi "
            "extraordinaria ou eventual (concentrada em poucos meses)."
        )
    else:
        texto = "Nao ha dados de despesa suficientes no historico para esta analise."

    top_extraordinarias = _top_despesas_extraordinarias(resultado)
    if top_extraordinarias:
        texto += "\n\nCategorias com maior peso extraordinario/eventual no historico:"
        for categoria_pai, subcategoria, total in top_extraordinarias:
            texto += f"\n- {categoria_pai} / {subcategoria}: {fmt_moeda(total)}"

    _caixa_consideracoes(pdf, texto)


def _pagina_inadimplencia(pdf: RelatorioPDF, resultado):
    pdf.add_page()
    pdf.titulo_pagina("4. Inadimplencia")

    tem_grafico = resultado.concentracao_inadimplencia is not None and not resultado.concentracao_inadimplencia.empty

    if tem_grafico:
        _cartoes_estatisticas(
            pdf, [("Percentual de inadimplencia apurado", fmt_pct(resultado.percentual_inadimplencia))]
        )
        pdf.ln(2)
        pdf.imagem_temporaria(grafico_evolucao_inadimplencia(resultado), w=170)
        pdf.ln(3)
        texto = (
            "O grafico acima mostra o valor em aberto por mes de competencia das cobrancas atualmente "
            "inadimplentes (nao e uma serie historica do percentual de inadimplencia, e sim a concentracao "
            "das cobrancas em aberto hoje). O mes de competencia com maior concentracao de valores em "
            f"aberto foi {resultado.mes_pico_inadimplencia}, o que merece atencao especial do sindico e da "
            "administradora para identificar a causa (ex: aumento pontual de taxa, dificuldade financeira "
            "concentrada em um periodo, etc.)."
        )
    else:
        _cartoes_estatisticas(
            pdf,
            [
                ("Percentual de inadimplencia apurado", fmt_pct(resultado.percentual_inadimplencia)),
                ("Valor total em aberto", fmt_moeda(resultado.inadimplencia_valor_total)),
            ],
        )
        pdf.ln(2)
        if resultado.inadimplencia_unidades:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, "Unidades inadimplentes:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", size=10)
            pdf.multi_cell(_largura_util(pdf), 5.5, ", ".join(resultado.inadimplencia_unidades))
            pdf.ln(2)
            texto = (
                f"O condominio apresenta {fmt_pct(resultado.percentual_inadimplencia)} de inadimplencia, "
                f"totalizando {fmt_moeda(resultado.inadimplencia_valor_total)} em aberto entre as unidades "
                "listadas acima. Nao ha dados suficientes no relatorio de inadimplentes para montar um "
                "grafico de concentracao por mes de competencia."
            )
        else:
            texto = (
                f"O condominio apresenta {fmt_pct(resultado.percentual_inadimplencia)} de inadimplencia "
                "apurada. Nao ha unidades inadimplentes nem cobrancas em aberto identificadas no relatorio "
                "enviado."
            )

    _caixa_consideracoes(pdf, texto)


def _pagina_reajuste(pdf: RelatorioPDF, resultado):
    pdf.add_page()
    pdf.titulo_pagina("5. Reajuste")

    largura_util = _largura_util(pdf)
    pdf.set_fill_color(*_hex_para_rgb(NAVY))
    altura_destaque = 34
    y_destaque = pdf.get_y()
    pdf.rect(pdf.l_margin, y_destaque, largura_util, altura_destaque, style="F")

    pdf.set_xy(pdf.l_margin, y_destaque + 4)
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(largura_util, 6, "Percentual de reajuste proposto", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_xy(pdf.l_margin, y_destaque + 10)
    pdf.set_font("Helvetica", "B", 40)
    pdf.set_text_color(*_hex_para_rgb(CYAN))
    pdf.cell(largura_util, 20, fmt_pct(resultado.percentual_reajuste_automatico), align="C")
    pdf.set_text_color(0, 0, 0)

    pdf.set_xy(pdf.l_margin, y_destaque + altura_destaque + 6)

    if resultado.percentual_reajuste_automatico > 0:
        texto_reajuste = (
            "O reajuste foi calculado comparando a receita ordinaria (rateio mensal) com a despesa "
            "ordinaria do historico dos ultimos 12 meses: como a despesa superou a receita, o percentual "
            "acima e o necessario para equilibrar as duas, mantendo a mesma base de despesas do periodo "
            "anterior."
        )
    else:
        texto_reajuste = (
            "Nao houve necessidade de reajuste: a receita ordinaria do historico ja cobriu a despesa "
            "ordinaria do mesmo periodo."
        )
    _caixa_consideracoes(pdf, texto_reajuste, titulo="Como o reajuste foi apurado")

    top_extraordinarias = _top_despesas_extraordinarias(resultado)
    if top_extraordinarias:
        texto_atencao = (
            "As categorias de despesa abaixo tiveram comportamento extraordinario/eventual no historico e "
            "merecem atencao especial para avaliar se devem se repetir no proximo periodo:"
        )
        for categoria_pai, subcategoria, total in top_extraordinarias:
            texto_atencao += f"\n- {categoria_pai} / {subcategoria}: {fmt_moeda(total)}"
    else:
        texto_atencao = (
            "Nao foram identificadas categorias de despesa com comportamento fora do padrao no historico "
            "analisado."
        )
    if resultado.total_outras_receitas_previsto > 0:
        texto_atencao += (
            f"\n\nO condominio conta com {fmt_moeda(resultado.total_outras_receitas_previsto)} em outras "
            "receitas previstas (juros, multas, eventuais). E recomendavel nao depender dessas receitas "
            "para cobrir despesas recorrentes, pois nao ha garantia de que se mantenham no mesmo patamar."
        )
    _caixa_consideracoes(pdf, texto_atencao, titulo="Pontos de atencao para equilibrar despesas e receitas")

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
    """Gera o PDF final de 5 paginas (capa, arrecadacoes, despesas, inadimplencia,
    reajuste) e retorna os bytes prontos para download."""
    pdf = RelatorioPDF()
    pdf.arquivos_temp = []
    try:
        _pagina_capa(pdf, resultado)
        _pagina_arrecadacoes(pdf, resultado)
        _pagina_despesas(pdf, resultado)
        _pagina_inadimplencia(pdf, resultado)
        _pagina_reajuste(pdf, resultado)
        return bytes(pdf.output())
    finally:
        import os

        for caminho in pdf.arquivos_temp:
            try:
                os.remove(caminho)
            except OSError:
                pass
