"""Filtra lançamentos por período/pessoa/categoria/tipo e agrega os totais
para o relatório (tela e PDF)."""
from dataclasses import dataclass, field
from datetime import date

from src.pessoal.analise import ResumoMes
from src.pessoal.modelos import TIPO_DESPESA, TIPO_RECEITA
from src.pessoal.projecao import Ocorrencia, lancamentos_do_mes, proximos_meses


def _meses_do_periodo(data_inicio: date, data_fim: date) -> list[tuple[int, int]]:
    quantidade = (data_fim.year - data_inicio.year) * 12 + (data_fim.month - data_inicio.month) + 1
    return proximos_meses(data_inicio.year, data_inicio.month, quantidade)


def ocorrencias_no_periodo(
    todos,
    data_inicio: date,
    data_fim: date,
    usuarios: set[str] | None = None,
    categorias: set[str] | None = None,
    tipos: set[str] | None = None,
) -> list[Ocorrencia]:
    """Todas as ocorrências entre `data_inicio` e `data_fim` (inclusive) que
    passam pelos filtros opcionais de pessoa, categoria e tipo."""
    brutas: list[Ocorrencia] = []
    for ano, mes in _meses_do_periodo(data_inicio, data_fim):
        brutas.extend(lancamentos_do_mes(todos, ano, mes))

    filtradas = [
        oc
        for oc in brutas
        if data_inicio <= oc.data <= data_fim
        and (not usuarios or oc.usuario in usuarios)
        and (not categorias or oc.categoria in categorias)
        and (not tipos or oc.tipo in tipos)
    ]
    return sorted(filtradas, key=lambda o: o.data)


def _agregar(ocorrencias: list[Ocorrencia]) -> dict:
    total_receitas = 0.0
    total_despesas = 0.0
    por_categoria_receita: dict[str, float] = {}
    por_categoria_despesa: dict[str, float] = {}
    por_usuario: dict[str, dict[str, float]] = {}

    for oc in ocorrencias:
        destino_categoria = por_categoria_receita if oc.tipo == TIPO_RECEITA else por_categoria_despesa
        destino_categoria[oc.categoria] = destino_categoria.get(oc.categoria, 0.0) + oc.valor

        por_usuario.setdefault(oc.usuario, {TIPO_RECEITA: 0.0, TIPO_DESPESA: 0.0})
        por_usuario[oc.usuario][oc.tipo] += oc.valor

        if oc.tipo == TIPO_RECEITA:
            total_receitas += oc.valor
        else:
            total_despesas += oc.valor

    return {
        "total_receitas": total_receitas,
        "total_despesas": total_despesas,
        "por_categoria_receita": por_categoria_receita,
        "por_categoria_despesa": por_categoria_despesa,
        "por_usuario": por_usuario,
    }


@dataclass
class ResumoPeriodo:
    data_inicio: date
    data_fim: date
    ocorrencias: list[Ocorrencia]
    total_receitas: float = 0.0
    total_despesas: float = 0.0
    por_categoria_receita: dict[str, float] = field(default_factory=dict)
    por_categoria_despesa: dict[str, float] = field(default_factory=dict)
    por_usuario: dict[str, dict[str, float]] = field(default_factory=dict)

    @property
    def saldo(self) -> float:
        return self.total_receitas - self.total_despesas


def resumir_periodo(ocorrencias: list[Ocorrencia], data_inicio: date, data_fim: date) -> ResumoPeriodo:
    agregado = _agregar(ocorrencias)
    return ResumoPeriodo(data_inicio=data_inicio, data_fim=data_fim, ocorrencias=ocorrencias, **agregado)


def evolucao_mensal(ocorrencias: list[Ocorrencia]) -> list[ResumoMes]:
    """Agrupa as ocorrências (já filtradas) por mês, para o gráfico de evolução."""
    por_mes: dict[tuple[int, int], list[Ocorrencia]] = {}
    for oc in ocorrencias:
        por_mes.setdefault((oc.data.year, oc.data.month), []).append(oc)

    resumos = []
    for ano, mes in sorted(por_mes.keys()):
        ocorrencias_do_mes = por_mes[(ano, mes)]
        agregado = _agregar(ocorrencias_do_mes)
        resumos.append(ResumoMes(ano=ano, mes=mes, ocorrencias=ocorrencias_do_mes, **agregado))
    return resumos
