"""Cálculos de resumo mensal, histórico e previsão futura."""
from dataclasses import dataclass, field

from src.pessoal.modelos import TIPO_DESPESA, TIPO_RECEITA
from src.pessoal.projecao import Ocorrencia, lancamentos_do_mes, proximos_meses


@dataclass
class ResumoMes:
    ano: int
    mes: int
    ocorrencias: list[Ocorrencia]
    total_receitas: float = 0.0
    total_despesas: float = 0.0
    por_categoria_receita: dict[str, float] = field(default_factory=dict)
    por_categoria_despesa: dict[str, float] = field(default_factory=dict)
    por_usuario: dict[str, dict[str, float]] = field(default_factory=dict)

    @property
    def saldo(self) -> float:
        return self.total_receitas - self.total_despesas


def resumir_mes(todos, ano: int, mes: int) -> ResumoMes:
    ocorrencias = lancamentos_do_mes(todos, ano, mes)
    resumo = ResumoMes(ano=ano, mes=mes, ocorrencias=ocorrencias)
    for oc in ocorrencias:
        destino_categoria = (
            resumo.por_categoria_receita if oc.tipo == TIPO_RECEITA else resumo.por_categoria_despesa
        )
        destino_categoria[oc.categoria] = destino_categoria.get(oc.categoria, 0.0) + oc.valor

        resumo.por_usuario.setdefault(oc.usuario, {TIPO_RECEITA: 0.0, TIPO_DESPESA: 0.0})
        resumo.por_usuario[oc.usuario][oc.tipo] += oc.valor

        if oc.tipo == TIPO_RECEITA:
            resumo.total_receitas += oc.valor
        else:
            resumo.total_despesas += oc.valor
    return resumo


def historico_mensal(todos, ano: int, mes: int, quantidade_meses_passados: int = 6) -> list[ResumoMes]:
    """Resumo dos últimos N meses, terminando em (ano, mes) incluso, em ordem cronológica."""
    inicio_total = (mes - 1) - (quantidade_meses_passados - 1)
    ano_inicio = ano + inicio_total // 12
    mes_inicio = inicio_total % 12 + 1
    meses = proximos_meses(ano_inicio, mes_inicio, quantidade_meses_passados)
    return [resumir_mes(todos, a, m) for a, m in meses]


def previsao_futura(todos, ano: int, mes: int, quantidade_meses: int = 6) -> list[ResumoMes]:
    """Projeção dos próximos N meses (incluindo o mês atual), a partir dos lançamentos
    fixos, parcelados e únicos já cadastrados com data futura."""
    meses = proximos_meses(ano, mes, quantidade_meses)
    return [resumir_mes(todos, a, m) for a, m in meses]
