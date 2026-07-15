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
class TipoUnidade:
    """Uma categoria de unidade que paga um valor mensal próprio (ex: 'Apartamento
    2 quartos', 'Cobertura'), usada no modo "tipos" de uma ConfiguracaoArrecadacao."""

    nome: str
    quantidade: int
    valor: float  # valor mensal por unidade desse tipo


@dataclass
class ConfiguracaoArrecadacao:
    """Como uma arrecadação (rateio principal, fundo de reserva, ou uma "outra
    arrecadação") é dividida entre as unidades. A mesma estrutura é reaproveitada
    nos 3 contextos do formulário.

    Modos:
    - "igual": todas as unidades pagam o mesmo valor (`valor_unico`).
    - "tipos": unidades agrupadas por tipo, cada tipo com seu próprio valor (`tipos`).
    - "fracao_ideal" / "indexador": valor de cada unidade = fração dela (`fracoes`)
      vezes o valor total mensal a arrecadar (`valor_total_mensal`); os dois modos
      usam exatamente a mesma lógica, só o nome exibido ao usuário muda.
    """

    modo: str = "igual"
    valor_unico: float = 0.0
    tipos: list[TipoUnidade] = field(default_factory=list)
    valor_total_mensal: float = 0.0
    fracoes: pd.DataFrame | None = None  # colunas: unidade, fracao, proprietario


@dataclass
class DadosFormulario:
    """Dados obrigatórios e opcionais preenchidos pelo usuário.

    O percentual de reajuste é calculado automaticamente pelo motor de
    cálculo a partir do próprio Demonstrativo de Receitas e Despesas (veja
    `src/calculo/previsao.py`). O rateio principal, o fundo de reserva e
    qualquer "outra arrecadação" são configurados com a mesma estrutura
    (ConfiguracaoArrecadacao), permitindo dividir cada um de forma diferente
    entre as unidades (igual, por tipo, ou por fração ideal/indexador)."""

    nome_condominio: str
    periodo: str
    numero_unidades: int  # deduzido a partir da configuração de rateio no formulário

    configuracao_rateio: ConfiguracaoArrecadacao = field(default_factory=ConfiguracaoArrecadacao)

    unidades_isentas: list[tuple[str, float]] = field(default_factory=list)  # (unidade, percentual de isencao 0-1)

    # Classificacao ordinaria/extraordinaria marcada manualmente pelo usuario
    # na tela de upload: nomes de categoria (receitas) / subcategoria
    # (despesas) marcados como extraordinarios; as demais linhas sao tratadas
    # como ordinarias.
    receitas_extraordinarias: list[str] = field(default_factory=list)
    despesas_extraordinarias: list[str] = field(default_factory=list)

    possui_desconto_pontualidade: bool = False
    desconto_pontualidade_modo: str = "valor_fixo"  # "valor_fixo" (R$/unidade) ou "percentual" (fração, ex: 0.05)
    desconto_pontualidade_valor: float = 0.0

    possui_fundo_reserva: bool = False
    configuracao_fundo_reserva: ConfiguracaoArrecadacao | None = None

    outras_arrecadacoes: list[tuple[str, ConfiguracaoArrecadacao]] = field(default_factory=list)

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
    possui_fundo_reserva: bool

    receita_rateio_necessaria: float
    numero_unidades: int
    percentual_inadimplencia: float

    total_outras_arrecadacoes_previsto: float = 0.0
    outras_arrecadacoes_detalhe: list[tuple[str, float]] = field(default_factory=list)

    valores_por_unidade: pd.DataFrame = None  # colunas: unidade, rateio, fundo_reserva, <outras...>, total

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
    inadimplencia_valor_por_unidade: pd.DataFrame = None  # colunas: unidade, valor_total, meses_em_atraso

    possui_desconto_pontualidade: bool = False
    desconto_pontualidade_modo: str = "valor_fixo"
    desconto_pontualidade_valor: float = 0.0
    desconto_pontualidade_total_mensal: float = 0.0

    # Base (anual) usada para calcular percentual_reajuste_automatico:
    # receita total = rateio + fundo de reserva + outras arrecadacoes
    # (configurados, anualizados) - sem receitas extraordinarias ou taxas
    # extras do historico.
    receita_total_anual_base_reajuste: float = 0.0

    unidades_isentas: list[tuple[str, float]] = field(default_factory=list)  # (unidade, percentual de isencao)
    isencao_total_mensal: float = 0.0

    # Soma (valor absoluto, anual) das linhas de receita do historico com
    # total negativo (descontos/deducoes lancados no campo de receita, ex:
    # "Isencao do Sindico", "Compensacao de boletos") - deduzida da
    # arrecadacao prevista e da base do reajuste.
    desconto_receita_historico_anual: float = 0.0
