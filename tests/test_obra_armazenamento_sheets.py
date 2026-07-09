from src.obra.armazenamento_sheets import (
    adicionar_gasto,
    carregar_dados_obra,
    carregar_gastos,
    disponivel,
    remover_gasto,
    salvar_dados_obra,
)
from src.obra.schema import DadosObra, GastoObra


class FakeConexao:
    """Simula a conexão da streamlit-gsheets, guardando cada aba em memória."""

    def __init__(self):
        self.abas = {}

    def read(self, *, worksheet, ttl=0, **kwargs):
        if worksheet not in self.abas:
            raise KeyError(worksheet)
        return self.abas[worksheet].copy()

    def update(self, *, worksheet, data, **kwargs):
        self.abas[worksheet] = data.copy()

    def create(self, *, worksheet, data, **kwargs):
        self.abas[worksheet] = data.copy()


def test_disponivel_e_falso_sem_secrets():
    assert disponivel() is False


def test_carregar_gastos_aba_inexistente_cria_vazia_automaticamente():
    conexao = FakeConexao()
    df = carregar_gastos(conexao)
    assert df.empty
    assert "gastos_obra" in conexao.abas


def test_adicionar_e_remover_gasto():
    conexao = FakeConexao()
    gasto1 = adicionar_gasto(
        conexao, GastoObra(data="2026-01-10", categoria="Material", descricao="Cimento", valor=250.0)
    )
    gasto2 = adicionar_gasto(
        conexao,
        GastoObra(data="2026-01-15", categoria="Mão de obra", descricao="Pedreiro", valor=800.0, pago=False),
    )

    assert gasto1.id == 1
    assert gasto2.id == 2

    df = carregar_gastos(conexao)
    assert len(df) == 2
    assert df["valor"].sum() == 1050.0
    assert df["pago"].tolist() == [True, False]

    remover_gasto(conexao, gasto1.id)
    df = carregar_gastos(conexao)
    assert len(df) == 1
    assert df.iloc[0]["descricao"] == "Pedreiro"


def test_dados_obra_ida_e_volta():
    conexao = FakeConexao()
    assert carregar_dados_obra(conexao) is None

    dados = DadosObra(
        nome_obra="Reforma da cozinha",
        proprietario="Maria Silva",
        endereco="Rua das Flores, 123",
        data_inicio="2026-01-01",
        previsao_termino="2026-06-01",
        orcamento_previsto=50000.0,
        status_obra="Em andamento",
        observacoes_gerais="Obra dentro do previsto.",
    )
    salvar_dados_obra(conexao, dados)

    carregado = carregar_dados_obra(conexao)
    assert carregado == dados
