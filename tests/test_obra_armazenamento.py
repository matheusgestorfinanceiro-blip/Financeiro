from src.obra.armazenamento import (
    adicionar_gasto,
    carregar_dados_obra,
    carregar_gastos,
    remover_gasto,
    salvar_dados_obra,
)
from src.obra.schema import DadosObra, GastoObra


def test_carregar_gastos_sem_arquivo_retorna_dataframe_vazio(tmp_path):
    caminho = tmp_path / "gastos.csv"
    df = carregar_gastos(caminho)
    assert df.empty
    assert list(df.columns) == [
        "id",
        "data",
        "categoria",
        "descricao",
        "fornecedor",
        "valor",
        "pago",
        "observacoes",
    ]


def test_adicionar_gasto_atribui_ids_sequenciais(tmp_path):
    caminho = tmp_path / "gastos.csv"

    gasto1 = adicionar_gasto(
        GastoObra(data="2026-01-10", categoria="Material", descricao="Cimento", valor=250.0),
        caminho,
    )
    gasto2 = adicionar_gasto(
        GastoObra(data="2026-01-15", categoria="Mão de obra", descricao="Pedreiro", valor=800.0, pago=False),
        caminho,
    )

    assert gasto1.id == 1
    assert gasto2.id == 2

    df = carregar_gastos(caminho)
    assert len(df) == 2
    assert set(df["id"]) == {1, 2}
    assert df["valor"].sum() == 1050.0
    assert df["pago"].tolist() == [True, False]


def test_remover_gasto(tmp_path):
    caminho = tmp_path / "gastos.csv"
    adicionar_gasto(GastoObra(data="2026-01-10", categoria="Material", descricao="Cimento", valor=250.0), caminho)
    gasto2 = adicionar_gasto(GastoObra(data="2026-01-15", categoria="Mão de obra", descricao="Pedreiro", valor=800.0), caminho)

    remover_gasto(gasto2.id, caminho)

    df = carregar_gastos(caminho)
    assert len(df) == 1
    assert df.iloc[0]["descricao"] == "Cimento"


def test_dados_obra_ida_e_volta(tmp_path):
    caminho = tmp_path / "dados_obra.json"
    assert carregar_dados_obra(caminho) is None

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
    salvar_dados_obra(dados, caminho)

    carregado = carregar_dados_obra(caminho)
    assert carregado == dados
