"""Lê o relatório 'Demonstrativo de Receitas e Despesas' (PDF) e monta as tabelas
de receitas e despesas dos últimos 12 meses.

O relatório é gerado sempre pelo mesmo sistema de gestão condominial, então o
layout (rótulo da linha seguido pelos valores dos 12 meses e do total do
período) é sempre igual — só mudam os nomes das categorias e os valores.

Limitação conhecida (v1): quando o nome de uma subcategoria de despesa é longo
e quebra em duas linhas no PDF (ex: "Manutenções Preventivas"), o parser pode
não reconhecer a quebra como um novo cabeçalho de grupo e manter a categoria
"pai" anterior. Isso não afeta os totais (a soma bate com o "Total do
período" impresso no PDF), só pode agrupar 1-2 linhas na categoria "pai"
errada. Ver testes de validação (soma das linhas == total do período).
"""
import re

import pandas as pd
import pdfplumber

from src.models.schema import DadosDemonstrativo
from src.parsers.pdf_utils import extrair_numeros, parse_moeda_brl, remover_cabecalho_inline, rotulo_da_linha

MES_RE = re.compile(r"^[A-Za-zç]{3}/\d{4}$")

RODAPE_OU_CABECALHO_RE = re.compile(
    r"^[\w.+-]+@[\w.-]+\.\w+|^\d+\s+de\s+\d+$|^CONDOMINIO\b|Tel:|^AVENIDA\b|^RUA\b|^AV\.\b"
)

CABECALHOS_CONHECIDOS = {
    "com pessoal", "mensais", "manutenção", "diversas",
    "manutenções preventivas", "serviços tercerizados",
}


def _linhas_do_pdf(caminho_pdf: str) -> list[str]:
    linhas: list[str] = []
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ""
            for linha in texto.split("\n"):
                linha = remover_cabecalho_inline(linha)
                if not linha or RODAPE_OU_CABECALHO_RE.search(linha):
                    continue
                linhas.append(linha)
    return linhas


def _extrair_condominio(linhas: list[str]) -> str:
    """A primeira linha que sobra depois de remover cabeçalho/rodapé é sempre a
    linha de identificação do imóvel (código + nome + número entre parênteses),
    independentemente da palavra usada para nomeá-lo (Condomínio, Residencial,
    Edifício etc.)."""
    for linha in linhas:
        if linha.strip():
            return linha.strip()
    return ""


def _extrair_meses(linhas: list[str]) -> list[str]:
    for linha in linhas:
        tokens = linha.strip().split()
        meses = [t for t in tokens if MES_RE.match(t)]
        if len(meses) >= 12:
            return meses[:12]
    return []


def _e_transferencia_entre_contas(texto: str) -> bool:
    """Identifica linhas de transferência entre contas do próprio condomínio
    (ex: "(+) Transf. da conta 'Digital PJBank' para a conta 'INVEST PJBANK'"),
    que não são receita nem despesa real e não devem entrar na análise."""
    texto_lower = texto.lower()
    return "transf" in texto_lower and "conta" in texto_lower


def parse_demonstrativo(caminho_pdf: str) -> DadosDemonstrativo:
    linhas = _linhas_do_pdf(caminho_pdf)
    condominio = _extrair_condominio(linhas)
    meses = _extrair_meses(linhas)

    secao = None  # "receitas" | "despesas"
    categoria_pai = None
    ultimo_tipo = None  # "header" | "leaf" | "subtotal"
    ultima_linha_leaf = None

    receitas: list[dict] = []
    despesas: list[dict] = []
    totais = {}

    for linha_bruta in linhas:
        linha = linha_bruta.strip()
        if not linha:
            continue

        if linha == "Receitas":
            secao = "receitas"
            categoria_pai = None
            ultimo_tipo = "header"
            continue
        if linha == "Despesas":
            secao = "despesas"
            categoria_pai = None
            ultimo_tipo = "header"
            continue

        numeros = extrair_numeros(linha)
        rotulo = rotulo_da_linha(linha, numeros)

        if rotulo.lower().startswith("saldo anterior"):
            if numeros:
                totais["saldo_anterior"] = parse_moeda_brl(numeros[0])
            ultimo_tipo = "subtotal"
            continue
        if rotulo.lower().startswith("saldo final"):
            if numeros:
                totais["saldo_final"] = parse_moeda_brl(numeros[0])
            ultimo_tipo = "subtotal"
            continue
        if rotulo.lower().startswith("mov.") or "líquido" in rotulo.lower():
            ultimo_tipo = "subtotal"
            continue

        if rotulo.lower().startswith("total de receitas"):
            if len(numeros) >= 1:
                totais["total_receitas"] = parse_moeda_brl(numeros[-1])
            ultimo_tipo = "subtotal"
            continue
        if rotulo.lower().startswith("total de despesas"):
            if len(numeros) >= 1:
                totais["total_despesas"] = parse_moeda_brl(numeros[-1])
            ultimo_tipo = "subtotal"
            continue

        if rotulo.lower().startswith("total"):
            # Subtotal de grupo (ex: "Total de Com Pessoal") - não é uma linha de detalhe.
            ultimo_tipo = "subtotal"
            continue

        if not numeros:
            # Linha sem nenhum valor numérico. Pode ser: (1) um cabeçalho de
            # grupo conhecido (sempre tratado como cabeçalho, mesmo que venha
            # logo após um item de detalhe); (2) a continuação de um rótulo
            # que quebrou em duas linhas no PDF; ou (3) a continuação do
            # rótulo de uma linha de subtotal que quebrou (nesse caso é
            # descartada, pois o subtotal já foi ignorado).
            if linha.lower() in CABECALHOS_CONHECIDOS:
                categoria_pai = linha
                ultimo_tipo = "header"
                continue
            if ultimo_tipo == "leaf" and ultima_linha_leaf is not None:
                chave = "subcategoria" if "subcategoria" in ultima_linha_leaf else "categoria"
                ultima_linha_leaf[chave] = f"{ultima_linha_leaf[chave]} {linha}".strip()
                continue
            if ultimo_tipo == "subtotal":
                continue
            categoria_pai = linha
            ultimo_tipo = "header"
            continue

        if len(numeros) < 12:
            # Linha numérica que não corresponde ao padrão esperado - ignora.
            continue

        valores_mensais = [parse_moeda_brl(n) for n in numeros[:12]]
        total = parse_moeda_brl(numeros[12]) if len(numeros) >= 13 else sum(valores_mensais)

        if secao == "receitas":
            registro = {"categoria": rotulo, "total": total}
            for mes, valor in zip(meses, valores_mensais):
                registro[mes] = valor
            receitas.append(registro)
            ultima_linha_leaf = registro
        elif secao == "despesas":
            registro = {
                "categoria_pai": categoria_pai or "Outras",
                "subcategoria": rotulo,
                "total": total,
            }
            for mes, valor in zip(meses, valores_mensais):
                registro[mes] = valor
            despesas.append(registro)
            ultima_linha_leaf = registro
        ultimo_tipo = "leaf"

    receitas = [r for r in receitas if not _e_transferencia_entre_contas(r["categoria"])]
    despesas = [d for d in despesas if not _e_transferencia_entre_contas(d["subcategoria"])]

    colunas_receitas = ["categoria", *meses, "total"]
    colunas_despesas = ["categoria_pai", "subcategoria", *meses, "total"]
    df_receitas = pd.DataFrame(receitas, columns=colunas_receitas)
    df_despesas = pd.DataFrame(despesas, columns=colunas_despesas)

    # Transferências entre contas próprias são excluídas da análise, então os
    # totais sempre refletem a soma das linhas já filtradas (não o "Total de
    # Receitas/Despesas" impresso no PDF, que ainda incluiria essas linhas).
    total_receitas = df_receitas["total"].sum() if not df_receitas.empty else 0.0
    total_despesas = df_despesas["total"].sum() if not df_despesas.empty else 0.0

    return DadosDemonstrativo(
        condominio=condominio,
        meses=meses,
        df_receitas=df_receitas,
        df_despesas=df_despesas,
        total_receitas=total_receitas,
        total_despesas=total_despesas,
        saldo_anterior=totais.get("saldo_anterior"),
        saldo_final=totais.get("saldo_final"),
    )
