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
    """Dados obrigatórios e opcionais preenchidos pelo usuário.

    O percentual de reajuste é calculado automaticamente pelo motor de
    cálculo a partir do próprio Demonstrativo de Receitas e Despesas (veja
    `src/calculo/previsao.py`). O fundo de reserva é controlado manualmente
    pelo usuário (sem fundo, percentual sobre o rateio, ou valor fixo por
    unidade)."""

    nome_condominio: str
    periodo: str
    numero_unidades: int

    # Rateio
    rateio_tipo: str = "igualitario"  # "igualitario" ou "fracao_ideal"
    valor_unico_por_unidade: float | None = None  # quando informado, substitui o cálculo automático
    fracoes_ideais: pd.DataFrame | None = None  # colunas: unidade, fracao (soma = 1.0)

    # Fundo de reserva
    possui_fundo_reserva: bool = False
    fundo_reserva_modo: str = "percentual"  # "percentual" ou "valor_fixo"
    fundo_reserva_valor_input: float = 0.0  # percentual (ex 0.05) ou R$ por unidade, conforme o modo

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
    periodo: str
    observacoes: str

    despesas_previstas: list[LinhaDespesaPrevista]
    total_despesas_historico: float
    total_despesas_previsto: float

    total_outras_receitas_previsto: float

    percentual_reajuste_automatico: float
    fundo_reserva_valor: float
    fundo_reserva_percentual: float
    possui_fundo_reserva: bool
    fundo_reserva_modo: str

    receita_rateio_necessaria: float
    numero_unidades: int
    valor_por_unidade_sem_ajuste: float
    valor_por_unidade_com_inadimplencia: float
    percentual_inadimplencia: float
    valor_por_unidade_sugerido_pelo_sistema: float | None = None

    rateio_tipo: str = "igualitario"
    rateio_por_unidade: pd.DataFrame = None  # colunas: unidade, fracao_ou_igual, valor

    total_despesas_historico_por_mes: dict = field(default_factory=dict)  # {mes: valor}
    total_receitas_historico_por_mes: dict = field(default_factory=dict)

    receitas_classificadas: pd.DataFrame = None  # colunas: categoria, <meses>, total, classificacao
    despesas_classificadas: pd.DataFrame = None  # colunas: categoria_pai, subcategoria, <meses>, total, classificacao
    concentracao_inadimplencia: pd.DataFrame = None  # colunas: competencia, valor_total
    mes_pico_inadimplencia: str | None = None
    data_geracao: str = ""

    arrecadacao_prevista_mensal: float = 0.0
    inadimplencia_valor_total: float = 0.0
    inadimplencia_unidades: list[str] = field(default_factory=list)
