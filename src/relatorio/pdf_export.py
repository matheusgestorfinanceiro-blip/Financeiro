"""Monta o relatório final em PDF: 5 páginas fixas (capa, receitas, despesas,
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


def _hex_para_rgb(cor_hex: str) -> tuple[int, int, int]:
    cor_hex = cor_hex.lstrip("#")
    return tuple(int(cor_hex[i : i + 2], 16) for i in (0, 2, 4))


def _descricao_fundo_reserva(resultado) -> str:
    if not resultado.possui_fundo_reserva:
        return "Este condominio nao possui fundo de reserva nesta previsao."
    if resultado.fundo_reserva_modo == "valor_fixo":
        return "Fundo de reserva: valor fixo por unidade."
    return f"Fundo de reserva: {fmt_pct(resultado.fundo_reserva_percentual)} sobre a receita de rateio."


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


def _pagina_receitas(pdf: RelatorioPDF, resultado):
    pdf.add_page()
    pdf.titulo_pagina("2. Receitas")

    totais = _total_por_classificacao(resultado.receitas_classificadas)
    total_historico = totais["ordinaria"] + totais["extraordinaria"]
    pct_ordinaria = totais["ordinaria"] / total_historico if total_historico else 0.0
    pct_extraordinaria = 1 - pct_ordinaria if total_historico else 0.0

    linhas = [
        ("Receita ordinaria (recorrente) no historico", fmt_moeda(totais["ordinaria"])),
        ("Receita extraordinaria/eventual no historico", fmt_moeda(totais["extraordinaria"])),
        ("Receita de rateio necessaria (previsto)", fmt_moeda(resultado.receita_rateio_necessaria)),
        ("Outras receitas previstas", fmt_moeda(resultado.total_outras_receitas_previsto)),
    ]
    for rotulo, valor in linhas:
        pdf.set_font("Helvetica", size=11)
        pdf.cell(130, 8, rotulo)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, valor, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)
    pdf.imagem_temporaria(grafico_receitas_ordinaria_x_extraordinaria(resultado), w=90)

    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 10)
    if total_historico:
        texto = (
            f"No historico dos ultimos 12 meses, {fmt_pct(pct_ordinaria)} da receita veio de fontes "
            f"ordinarias e recorrentes (como o rateio mensal), enquanto {fmt_pct(pct_extraordinaria)} "
            "veio de fontes extraordinarias ou eventuais (ex: juros, multas, receitas pontuais). Receitas "
            "eventuais nao devem ser usadas como base para o calculo do reajuste ou do rateio do proximo "
            "periodo, pois nao ha garantia de que se repitam."
        )
    else:
        texto = "Nao ha dados de receita suficientes no historico para esta analise."
    pdf.multi_cell(0, 6, texto)


def _pagina_despesas(pdf: RelatorioPDF, resultado):
    pdf.add_page()
    pdf.titulo_pagina("3. Despesas")

    totais = _total_por_classificacao(resultado.despesas_classificadas)
    total_historico = totais["ordinaria"] + totais["extraordinaria"]
    pct_ordinaria = totais["ordinaria"] / total_historico if total_historico else 0.0
    pct_extraordinaria = 1 - pct_ordinaria if total_historico else 0.0

    linhas = [
        ("Despesa ordinaria (recorrente) no historico", fmt_moeda(totais["ordinaria"])),
        ("Despesa extraordinaria/eventual no historico", fmt_moeda(totais["extraordinaria"])),
        ("Total de despesas previsto (12 meses)", fmt_moeda(resultado.total_despesas_previsto)),
        ("Total de despesas no historico (12 meses)", fmt_moeda(resultado.total_despesas_historico)),
    ]
    for rotulo, valor in linhas:
        pdf.set_font("Helvetica", size=11)
        pdf.cell(130, 8, rotulo)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, valor, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)
    pdf.imagem_temporaria(grafico_despesas_ordinaria_x_extraordinaria(resultado), w=90)

    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 10)
    if total_historico:
        texto = (
            f"No historico dos ultimos 12 meses, {fmt_pct(pct_ordinaria)} da despesa foi recorrente "
            f"(aparece de forma regular ao longo do ano) e {fmt_pct(pct_extraordinaria)} foi "
            "extraordinaria ou eventual (concentrada em poucos meses)."
        )
    else:
        texto = "Nao ha dados de despesa suficientes no historico para esta analise."
    pdf.multi_cell(0, 6, texto)

    top_extraordinarias = _top_despesas_extraordinarias(resultado)
    if top_extraordinarias:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "Categorias com maior peso extraordinario/eventual no historico:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=10)
        for categoria_pai, subcategoria, total in top_extraordinarias:
            pdf.cell(0, 6, f"- {categoria_pai} / {subcategoria}: {fmt_moeda(total)}", new_x="LMARGIN", new_y="NEXT")


def _pagina_inadimplencia(pdf: RelatorioPDF, resultado):
    pdf.add_page()
    pdf.titulo_pagina("4. Inadimplencia")

    pdf.set_font("Helvetica", size=11)
    pdf.cell(130, 8, "Percentual de inadimplencia considerado")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, fmt_pct(resultado.percentual_inadimplencia), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)
    pdf.imagem_temporaria(grafico_evolucao_inadimplencia(resultado), w=170)

    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 10)
    if resultado.mes_pico_inadimplencia:
        texto = (
            "O grafico acima mostra o valor em aberto por mes de competencia das cobrancas atualmente "
            "inadimplentes (nao e uma serie historica do percentual de inadimplencia, e sim a concentracao "
            f"das cobrancas em aberto hoje). O mes de competencia com maior concentracao de valores em "
            f"aberto foi {resultado.mes_pico_inadimplencia}, o que merece atencao especial do sindico e da "
            "administradora para identificar a causa (ex: aumento pontual de taxa, dificuldade financeira "
            "concentrada em um periodo, etc.)."
        )
    else:
        texto = "Nao ha cobrancas em aberto registradas no relatorio de inadimplentes enviado."
    pdf.multi_cell(0, 6, texto)


def _pagina_reajuste(pdf: RelatorioPDF, resultado):
    pdf.add_page()
    pdf.titulo_pagina("5. Reajuste")

    pdf.set_font("Helvetica", size=11)
    pdf.cell(130, 8, "Percentual de reajuste apurado")
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*_hex_para_rgb(CYAN))
    pdf.cell(0, 8, fmt_pct(resultado.percentual_reajuste_automatico), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)

    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 10)
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
    pdf.multi_cell(0, 6, texto_reajuste)

    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Fundo de reserva", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, f"Valor previsto: {fmt_moeda(resultado.fundo_reserva_valor)}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, _descricao_fundo_reserva(resultado), new_x="LMARGIN", new_y="NEXT")

    top_extraordinarias = _top_despesas_extraordinarias(resultado)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Pontos de atencao para equilibrar despesas e receitas", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    if top_extraordinarias:
        pdf.multi_cell(
            0, 6,
            "As categorias de despesa abaixo tiveram comportamento extraordinario/eventual no historico e "
            "merecem atencao especial para avaliar se devem se repetir no proximo periodo:",
        )
        pdf.ln(1)
        for categoria_pai, subcategoria, total in top_extraordinarias:
            pdf.cell(0, 6, f"- {categoria_pai} / {subcategoria}: {fmt_moeda(total)}", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.multi_cell(
            0, 6,
            "Nao foram identificadas categorias de despesa com comportamento fora do padrao no historico "
            "analisado.",
        )
    if resultado.total_outras_receitas_previsto > 0:
        pdf.ln(2)
        pdf.multi_cell(
            0, 6,
            f"O condominio conta com {fmt_moeda(resultado.total_outras_receitas_previsto)} em outras receitas "
            "previstas (juros, multas, eventuais). E recomendavel nao depender dessas receitas para cobrir "
            "despesas recorrentes, pois nao ha garantia de que se mantenham no mesmo patamar.",
        )


def gerar_pdf_previsao(resultado) -> bytes:
    """Gera o PDF final de 5 paginas (capa, receitas, despesas, inadimplencia,
    reajuste) e retorna os bytes prontos para download."""
    pdf = RelatorioPDF()
    pdf.arquivos_temp = []
    try:
        _pagina_capa(pdf, resultado)
        _pagina_receitas(pdf, resultado)
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
