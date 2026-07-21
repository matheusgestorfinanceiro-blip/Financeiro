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
from collections import Counter

import pandas as pd
import pdfplumber

from src.models.schema import DadosDemonstrativo
from src.parsers.pdf_utils import extrair_numeros, parse_moeda_brl, remover_cabecalho_inline, rotulo_da_linha

MES_RE = re.compile(r"^[A-Za-zç]{3}/\d{4}$")

RODAPE_OU_CABECALHO_RE = re.compile(
    r"^[\w.+-]+@[\w.-]+\.\w+|^\d+\s+de\s+\d+$|^CONDOMINIO\b|Tel:|^AVENIDA\b|^RUA\b|^AV\.\b"
)

# Alguns relatorios reais repetem a cidade/UF do imovel (ex: "PORTO SEGURO /
# BA") como parte do cabecalho de cada pagina, colada sem espaco a outro
# texto quando a quebra de pagina cai no meio de um rotulo - mesmo problema
# do cabecalho "email em data" (ver CABECALHO_INLINE_RE em pdf_utils.py), so
# que o texto da cidade/UF nao e conhecido de antemao. Palavras em maiusculas
# seguidas de "/ UF" no fim (ou seguidas de espaco) sao removidas de onde
# aparecerem, do mesmo jeito.
CIDADE_UF_RE = re.compile(r"\b[A-ZÀ-Ý][A-ZÀ-Ý ]*/\s*[A-Z]{2}\b")

CABECALHOS_CONHECIDOS = {
    "com pessoal", "mensais", "manutenção", "diversas",
    "manutenções preventivas", "serviços tercerizados",
}


def _detectar_cabecalhos_repetidos(paginas_linhas: list[list[str]], linhas_topo: int = 4) -> list[str]:
    """Descobre quais linhas se repetem no topo das paginas (identificacao do
    imovel, endereco, cidade/UF, CEP etc.) - sem depender de saber de antemao
    o formato exato do endereco (rua, avenida, praca, travessa...) nem de uma
    lista fixa de palavras.

    Conta cada linha distinta que aparece entre as primeiras `linhas_topo`
    linhas de cada pagina (uma contagem por pagina): qualquer uma que apareca
    no topo de 2 ou mais paginas e cabecalho repetido, nao conteudo. Isso e
    mais robusto do que exigir que o bloco seja um prefixo identico de todas
    as paginas (abordagem anterior, que falhava quando o endereco vinha
    colado no meio de uma linha de dados numa pagina de quebra, ou quando
    uma pagina comecava de forma um pouco diferente). Retorna as linhas
    ordenadas da mais longa para a mais curta, para que a remocao por
    substring (ver _linhas_do_pdf) tire primeiro o texto maior, evitando
    sobras quando um cabecalho e prefixo de outro."""
    paginas_com_conteudo = [p for p in paginas_linhas if p]
    if len(paginas_com_conteudo) < 2:
        return []
    contagem: Counter = Counter()
    for pagina in paginas_com_conteudo:
        # dict.fromkeys preserva a ordem e conta cada linha uma vez por pagina
        for linha in dict.fromkeys(pagina[:linhas_topo]):
            contagem[linha] += 1
    # Linhas muito curtas (poucos caracteres) nao valem a pena remover (baixo
    # risco de coincidencia, baixo beneficio); linhas com valores monetarios
    # nunca sao cabecalho (sao dados/subtotais) e nao devem ser removidas.
    repetidos = [
        linha for linha, n in contagem.items()
        if n >= 2 and len(linha) >= 4 and not extrair_numeros(linha)
    ]
    return sorted(repetidos, key=len, reverse=True)


def _linhas_do_pdf(caminho_pdf: str) -> list[str]:
    """Le o texto de cada pagina e remove o ruido de cabecalho/rodape.

    Alem do padrao fixo "email em data" (removido em qualquer posicao da
    linha, ver remover_cabecalho_inline) e do padrao de cidade/UF
    (CIDADE_UF_RE), o sistema de gestao tambem repete um pequeno bloco de
    linhas (identificacao do imovel, endereco completo etc.) no topo de toda
    pagina - esse bloco e descoberto dinamicamente comparando as paginas
    entre si (ver _detectar_cabecalhos_repetidos), entao funciona qualquer
    que seja o formato do endereco. Qualquer ocorrencia dessas linhas
    (inteira ou colada no meio de outra linha, quando a quebra de pagina cai
    bem ali) e removida de onde aparecer.
    """
    with pdfplumber.open(caminho_pdf) as pdf:
        paginas_linhas = []
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ""
            linhas_pagina = []
            for linha in texto.split("\n"):
                linha = remover_cabecalho_inline(linha)
                linha = CIDADE_UF_RE.sub("", linha).strip()
                if not linha or RODAPE_OU_CABECALHO_RE.search(linha):
                    continue
                linhas_pagina.append(linha)
            paginas_linhas.append(linhas_pagina)

    cabecalhos_repetidos = _detectar_cabecalhos_repetidos(paginas_linhas)

    # A 1a linha de conteudo da 1a pagina e a identificacao do imovel (usada
    # por _extrair_condominio). Como ela tambem se repete no topo de cada
    # pagina, cai em cabecalhos_repetidos e seria removida de TODO lugar - o
    # que apagaria tambem o nome do condominio. Por isso ela e preservada e
    # reinserida uma unica vez no inicio (as demais ocorrencias, e o endereco,
    # continuam sendo removidos como ruido).
    condominio_linha = next((p[0] for p in paginas_linhas if p), None)

    linhas: list[str] = []
    for linhas_pagina in paginas_linhas:
        for linha in linhas_pagina:
            for cabecalho in cabecalhos_repetidos:
                linha = linha.replace(cabecalho, "").strip()
            if linha:
                linhas.append(linha)

    if condominio_linha and (not linhas or linhas[0] != condominio_linha):
        linhas.insert(0, condominio_linha)
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
