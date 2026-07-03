"""Estruturas de dados usadas em todo o sistema (entrada e saída)."""
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class DadosInadimplencia:
    """Resultado da leitura do PDF 'Inadimplentes'."""

    condominio: str
    unidades: pd.DataFrame  # colunas: unidade, vencimento, competencia, atraso_dias, codigo, principal, juros, multa, honorarios, total
    qtd_unidades_inadimplentes: int
    percentual_inadimplencia: float  # ex: 0.175 = 17,5%
    total_principal: float
    total_geral: float


@dataclass
class DadosDemonstrativo:
    """Resultado da leitura do PDF 'Demonstrativo de Receitas e Despesas'."""

    condominio: str
    meses: list[str]  # ex: ["Mai/2025", "Jun/2025", ...]
    df_receitas: pd.DataFrame  # colunas: categoria, <cada mês>, total
    df_despesas: pd.DataFrame  # colunas: categoria_pai, subcategoria, <cada mês>, total
    total_receitas: float
    total_despesas: float
    saldo_anterior: float | None = None
    saldo_final: float | None = None


@dataclass
class AjusteManual:
    """Ajuste pontual de reajuste para uma categoria específica de despesa."""

    subcategoria: str
    percentual_reajuste: float


@dataclass
class DadosFormulario:
    """Dados obrigatórios e opcionais preenchidos pelo usuário."""

    nome_condominio: str
    periodo_inicio: str
    periodo_fim: str
    percentual_reajuste: float
    numero_unidades: int

    # Fundo de reserva
    fundo_reserva_percentual: float
    fundo_reserva_base: str = "rateio"  # "rateio" ou "despesas"

    # Taxa de administração
    taxa_administracao_modo: str = "percentual_despesas"  # "percentual_despesas" | "percentual_rateio" | "valor_fixo"
    taxa_administracao_valor: float = 0.0  # percentual (ex 0.08) ou valor em R$, conforme o modo

    # Rateio
    rateio_tipo: str = "igualitario"  # "igualitario" ou "fracao_ideal"
    fracoes_ideais: pd.DataFrame | None = None  # colunas: unidade, fracao (soma = 1.0)

    observacoes: str = ""
    ajustes_manuais: list[AjusteManual] = field(default_factory=list)


@dataclass
class LinhaDespesaPrevista:
    categoria_pai: str
    subcategoria: str
    valor_historico: float
    percentual_reajuste_aplicado: float
    valor_previsto: float
    ajuste_manual: bool = False


@dataclass
class ResultadoPrevisao:
    """Todos os números já calculados, prontos para montar as 5 páginas finais."""

    nome_condominio: str
    periodo_inicio: str
    periodo_fim: str
    observacoes: str

    despesas_previstas: list[LinhaDespesaPrevista]
    total_despesas_historico: float
    total_despesas_previsto: float

    total_outras_receitas_previsto: float

    fundo_reserva_valor: float
    taxa_administracao_valor: float

    receita_rateio_necessaria: float
    numero_unidades: int
    valor_por_unidade_sem_ajuste: float
    valor_por_unidade_com_inadimplencia: float
    percentual_inadimplencia: float

    rateio_tipo: str
    rateio_por_unidade: pd.DataFrame  # colunas: unidade, fracao_ou_igual, valor

    total_despesas_historico_por_mes: dict  # {mes: valor}
    total_receitas_historico_por_mes: dict
