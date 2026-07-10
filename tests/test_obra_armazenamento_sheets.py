from src.obra.armazenamento_sheets import (
    adicionar_foto_registro,
    adicionar_gasto,
    atualizar_gasto,
    carregar_dados_obra,
    carregar_fotos,
    carregar_gastos,
    disponivel,
    remover_foto_registro,
    remover_gasto,
    salvar_dados_obra,
)
from src.obra.schema import DadosObra, FotoObra, GastoObra


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
        GastoObra(
            data="2026-01-15",
            categoria="Mão de obra",
            descricao="Pedreiro",
            valor=800.0,
            pago=False,
            anexo="drivefile123.jpg",
        ),
    )

    assert gasto1.id == 1
    assert gasto2.id == 2

    df = carregar_gastos(conexao)
    assert len(df) == 2
    assert df["valor"].sum() == 1050.0
    assert df["pago"].tolist() == [True, False]
    assert df.iloc[1]["anexo"] == "drivefile123.jpg"
    assert df.iloc[0]["anexo"] == ""

    remover_gasto(conexao, gasto1.id)
    df = carregar_gastos(conexao)
    assert len(df) == 1
    assert df.iloc[0]["descricao"] == "Pedreiro"


def test_atualizar_gasto_substitui_valores_mantendo_id():
    conexao = FakeConexao()
    gasto1 = adicionar_gasto(
        conexao, GastoObra(data="2026-01-10", categoria="Material", descricao="Cimento", valor=250.0, pago=False)
    )
    adicionar_gasto(conexao, GastoObra(data="2026-01-15", categoria="Mão de obra", descricao="Pedreiro", valor=800.0))

    atualizar_gasto(
        conexao,
        GastoObra(
            id=gasto1.id,
            data="2026-01-11",
            categoria="Material",
            descricao="Cimento CP II",
            valor=300.0,
            fornecedor="Loja ABC",
            pago=True,
            observacoes="Comprado à vista",
        ),
    )

    df = carregar_gastos(conexao)
    assert len(df) == 2
    linha = df[df["id"] == gasto1.id].iloc[0]
    assert linha["descricao"] == "Cimento CP II"
    assert linha["valor"] == 300.0
    assert linha["fornecedor"] == "Loja ABC"
    assert bool(linha["pago"]) is True


def test_carregar_fotos_aba_inexistente_cria_vazia_automaticamente():
    conexao = FakeConexao()
    df = carregar_fotos(conexao)
    assert df.empty
    assert "fotos_obra" in conexao.abas


def test_adicionar_e_remover_registro_de_foto():
    conexao = FakeConexao()
    foto1 = adicionar_foto_registro(conexao, FotoObra(data="2026-02-01", nome_arquivo="ref1.jpg", legenda="Fundação"))
    foto2 = adicionar_foto_registro(conexao, FotoObra(data="2026-01-05", nome_arquivo="ref2.jpg", legenda="Início"))

    assert foto1.id == 1
    assert foto2.id == 2

    df = carregar_fotos(conexao)
    assert len(df) == 2
    # ordenadas por data (ordem de execução), não por ordem de inserção
    assert df.iloc[0]["legenda"] == "Início"
    assert df.iloc[1]["legenda"] == "Fundação"

    remover_foto_registro(conexao, foto2.id)
    df = carregar_fotos(conexao)
    assert len(df) == 1
    assert df.iloc[0]["legenda"] == "Fundação"


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
