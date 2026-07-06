"""Monta o PDF final com as 5 páginas da previsão orçamentária."""
import tempfile

from fpdf import FPDF

from src.relatorio.graficos import (
    grafico_composicao_taxa_condominial,
    grafico_despesas_por_categoria,
    grafico_evolucao_mensal,
    grafico_indicador_inadimplencia,
)


def _fmt_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_pct(valor: float) -> str:
    return f"{valor * 100:.2f}".replace(".", ",") + "%"


class RelatorioPDF(FPDF):
    def cabecalho_pagina(self, titulo: str, resultado):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, titulo, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", size=10)
        self.cell(
            0, 6,
            f"{resultado.nome_condominio}  |  Período: {resultado.periodo_inicio} a {resultado.periodo_fim}",
            new_x="LMARGIN", new_y="NEXT",
        )
        self.ln(4)


def _pagina_resumo_executivo(pdf: RelatorioPDF, resultado):
    pdf.add_page()
    pdf.cabecalho_pagina("1. Resumo executivo da previsão orçamentária", resultado)

    pdf.set_font("Helvetica", size=11)
    linhas = [
        ("Total de despesas previsto (12 meses)", _fmt_moeda(resultado.total_despesas_previsto)),
        ("Total de despesas no histórico (12 meses)", _fmt_moeda(resultado.total_despesas_historico)),
        ("Reajuste aplicado (calculado automaticamente)", _fmt_pct(resultado.percentual_reajuste_automatico)),
        ("Fundo de reserva previsto", _fmt_moeda(resultado.fundo_reserva_valor)),
        ("Receita de rateio necessária (total)", _fmt_moeda(resultado.receita_rateio_necessaria)),
        ("Valor sugerido por unidade (sem ajuste de inadimplência)", _fmt_moeda(resultado.valor_por_unidade_sem_ajuste)),
        (
            f"Valor sugerido por unidade (ajustado p/ inadimplência de {_fmt_pct(resultado.percentual_inadimplencia)})",
            _fmt_moeda(resultado.valor_por_unidade_com_inadimplencia),
        ),
    ]
    if resultado.valor_por_unidade_sugerido_pelo_sistema is not None:
        linhas.append(
            ("Valor que o sistema calcularia automaticamente (referência)", _fmt_moeda(resultado.valor_por_unidade_sugerido_pelo_sistema))
        )
    for rotulo, valor in linhas:
        pdf.set_font("Helvetica", size=11)
        pdf.cell(130, 8, rotulo)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, valor, new_x="LMARGIN", new_y="NEXT")

    if not resultado.fundo_reserva_linha_encontrada:
        pdf.ln(2)
        pdf.set_font("Helvetica", "I", 9)
        pdf.multi_cell(
            0, 5,
            "Nenhuma linha de receita de 'fundo de reserva' foi encontrada no demonstrativo - "
            "o percentual do fundo de reserva foi considerado 0%.",
        )

    if resultado.observacoes:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, "Observações", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(0, 6, resultado.observacoes)


def _pagina_despesas_por_categoria(pdf: RelatorioPDF, resultado):
    pdf.add_page()
    pdf.cabecalho_pagina("2. Detalhamento de despesas por categoria", resultado)

    pdf.set_font("Helvetica", "B", 9)
    larguras = [45, 60, 30, 25, 30]
    cabecalhos = ["Categoria", "Subcategoria", "Histórico", "Reajuste", "Previsto"]
    for largura, texto in zip(larguras, cabecalhos):
        pdf.cell(largura, 7, texto, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", size=8)
    for linha in resultado.despesas_previstas:
        marcador = " *" if linha.ajuste_manual else ""
        valores = [
            linha.categoria_pai,
            linha.subcategoria,
            _fmt_moeda(linha.valor_historico),
            _fmt_pct(linha.percentual_reajuste_aplicado) + marcador,
            _fmt_moeda(linha.valor_previsto),
        ]
        for largura, texto in zip(larguras, valores):
            pdf.cell(largura, 6, str(texto)[:40], border=1)
        pdf.ln()

    pdf.ln(2)
    pdf.set_font("Helvetica", size=8)
    pdf.multi_cell(0, 5, "* Categoria com ajuste manual definido na área de análise.")


def _pagina_receitas_e_rateio(pdf: RelatorioPDF, resultado):
    pdf.add_page()
    pdf.cabecalho_pagina("3. Receitas e rateio por unidade", resultado)

    pdf.set_font("Helvetica", size=11)
    tipo_rateio = "Fração ideal" if resultado.rateio_tipo == "fracao_ideal" else "Taxa única por unidade"
    pdf.cell(0, 8, f"Tipo de rateio: {tipo_rateio}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0, 8,
        f"Inadimplência considerada no cálculo: {_fmt_pct(resultado.percentual_inadimplencia)}",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(70, 7, "Unidade", border=1)
    pdf.cell(40, 7, "Fração", border=1)
    pdf.cell(40, 7, "Valor previsto", border=1)
    pdf.ln()

    pdf.set_font("Helvetica", size=8)
    for _, row in resultado.rateio_por_unidade.iterrows():
        pdf.cell(70, 6, str(row["unidade"])[:40], border=1)
        pdf.cell(40, 6, f"{row['fracao'] * 100:.4f}%".replace(".", ","), border=1)
        pdf.cell(40, 6, _fmt_moeda(row["valor"]), border=1)
        pdf.ln()


def _pagina_fundo_e_taxa(pdf: RelatorioPDF, resultado):
    pdf.add_page()
    pdf.cabecalho_pagina("4. Fundo de reserva", resultado)

    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(
        0, 7,
        "Este demonstrativo mostra como o fundo de reserva foi calculado, para apresentação em assembleia.",
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Fundo de reserva", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 7, f"Valor previsto: {_fmt_moeda(resultado.fundo_reserva_valor)}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0, 7,
        f"Percentual automático sobre a receita de rateio: {_fmt_pct(resultado.fundo_reserva_percentual_automatico)}",
        new_x="LMARGIN", new_y="NEXT",
    )
    if not resultado.fundo_reserva_linha_encontrada:
        pdf.set_font("Helvetica", "I", 9)
        pdf.multi_cell(0, 5, "Nenhuma linha de 'fundo de reserva' encontrada no demonstrativo - considerado 0%.")
    if resultado.fundo_reserva_percentual_limitado:
        pdf.set_font("Helvetica", "I", 9)
        pdf.multi_cell(
            0, 5,
            "O percentual calculado automaticamente ficou muito alto (maior ou igual a 50%) e foi "
            "limitado a 50% para o cálculo não travar. Confira a linha de 'fundo de reserva' no "
            "demonstrativo original.",
        )


def _pagina_graficos(pdf: RelatorioPDF, resultado, arquivos_temp: list[str]):
    pdf.add_page()
    pdf.cabecalho_pagina("5. Gráficos e indicadores comparativos", resultado)

    figuras = [
        grafico_despesas_por_categoria(resultado),
        grafico_evolucao_mensal(resultado),
        grafico_composicao_taxa_condominial(resultado),
        grafico_indicador_inadimplencia(resultado),
    ]
    for fig in figuras:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        fig.savefig(tmp.name, dpi=150)
        arquivos_temp.append(tmp.name)
        pdf.image(tmp.name, w=170)
        pdf.ln(4)


def gerar_pdf_previsao(resultado) -> bytes:
    """Gera o PDF final de 5 páginas e retorna os bytes prontos para download."""
    pdf = RelatorioPDF()
    arquivos_temp: list[str] = []
    try:
        _pagina_resumo_executivo(pdf, resultado)
        _pagina_despesas_por_categoria(pdf, resultado)
        _pagina_receitas_e_rateio(pdf, resultado)
        _pagina_fundo_e_taxa(pdf, resultado)
        _pagina_graficos(pdf, resultado, arquivos_temp)
        return bytes(pdf.output())
    finally:
        import os

        for caminho in arquivos_temp:
            try:
                os.remove(caminho)
            except OSError:
                pass
