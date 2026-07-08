"""Estruturas de dados do registro de gastos de uma obra/reforma residencial."""
from dataclasses import dataclass

CATEGORIAS_GASTO = [
    "Material",
    "Mão de obra",
    "Equipamento",
    "Imprevisto",
    "Outros",
]

STATUS_OBRA = ["Planejamento", "Em andamento", "Paralisada", "Concluída"]


@dataclass
class GastoObra:
    """Um lançamento de gasto da obra."""

    data: str  # "AAAA-MM-DD"
    categoria: str
    descricao: str
    valor: float
    fornecedor: str = ""
    pago: bool = True
    observacoes: str = ""
    id: int = 0


@dataclass
class DadosObra:
    """Dados gerais da obra, usados na capa e no resumo do relatório final."""

    nome_obra: str = ""
    proprietario: str = ""
    endereco: str = ""
    data_inicio: str = ""
    previsao_termino: str = ""
    orcamento_previsto: float = 0.0
    status_obra: str = "Em andamento"
    observacoes_gerais: str = ""


@dataclass
class FotoObra:
    """Uma foto de evolução da obra, usada no relatório final."""

    data: str  # "AAAA-MM-DD"
    nome_arquivo: str  # nome do arquivo salvo em data/obra/fotos/
    legenda: str = ""
    id: int = 0
