"""Estruturas de dados do sistema de finanças pessoais."""
from dataclasses import dataclass
from datetime import date

TIPO_RECEITA = "receita"
TIPO_DESPESA = "despesa"
TIPOS = (TIPO_RECEITA, TIPO_DESPESA)

REPETICAO_UNICA = "unica"
REPETICAO_FIXA = "fixa"
REPETICAO_PARCELADA = "parcelada"
REPETICOES = (REPETICAO_UNICA, REPETICAO_FIXA, REPETICAO_PARCELADA)

USUARIOS_PADRAO = ["Matheus", "Walkiria"]

CATEGORIAS_RECEITA = [
    "Salário",
    "Renda extra",
    "Freelance",
    "Investimentos",
    "Outras receitas",
]

CATEGORIAS_DESPESA = [
    "Moradia",
    "Contas (água/luz/internet)",
    "Alimentação",
    "Transporte",
    "Saúde",
    "Educação",
    "Lazer",
    "Vestuário",
    "Cartão de crédito",
    "Assinaturas",
    "Investimentos/Poupança",
    "Outras despesas",
]


@dataclass
class Lancamento:
    """Um lançamento financeiro: pode ser único, fixo (recorrente todo mês) ou parcelado.

    - unica: ocorre só no mês/ano de `data`.
    - fixa: ocorre todo mês a partir de `data` enquanto `ativa` for True
      (e, se houver, até `data_fim`).
    - parcelada: ocorre por `parcela_total` meses consecutivos a partir de `data`.
    """

    descricao: str
    categoria: str
    tipo: str  # receita | despesa
    valor: float
    data: date  # primeira ocorrência (dia de vencimento/competência)
    usuario: str
    repeticao: str = REPETICAO_UNICA
    parcela_total: int | None = None
    ativa: bool = True
    data_fim: date | None = None
    observacao: str = ""
    id: int | None = None
