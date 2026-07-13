from src.obra.armazenamento import (
    adicionar_foto,
    adicionar_gasto,
    adicionar_nota_fiscal,
    atualizar_gasto,
    carregar_dados_obra,
    carregar_fotos,
    carregar_gastos,
    carregar_notas_fiscais,
    desregistrar_foto,
    desregistrar_nota_fiscal,
    ler_arquivo_local,
    registrar_foto,
    registrar_nota_fiscal,
    remover_arquivo_local,
    remover_foto,
    remover_gasto,
    remover_nota_fiscal,
    salvar_arquivo_local,
    salvar_dados_obra,
)
from src.obra.schema import DadosObra, FotoObra, GastoObra, NotaFiscalObra


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
        "anexo",
    ]


def test_carregar_gastos_csv_antigo_sem_coluna_anexo(tmp_path):
    caminho = tmp_path / "gastos.csv"
    caminho.write_text(
        "id,data,categoria,descricao,fornecedor,valor,pago,observacoes\n"
        "1,2026-01-10,Material,Cimento,,250.0,True,\n"
    )
    df = carregar_gastos(caminho)
    assert df.iloc[0]["anexo"] == ""


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


def test_atualizar_gasto_substitui_valores_mantendo_id(tmp_path):
    caminho = tmp_path / "gastos.csv"
    gasto1 = adicionar_gasto(
        GastoObra(data="2026-01-10", categoria="Material", descricao="Cimento", valor=250.0, pago=False),
        caminho,
    )
    adicionar_gasto(GastoObra(data="2026-01-15", categoria="Mão de obra", descricao="Pedreiro", valor=800.0), caminho)

    atualizar_gasto(
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
        caminho,
    )

    df = carregar_gastos(caminho)
    assert len(df) == 2
    linha = df[df["id"] == gasto1.id].iloc[0]
    assert linha["descricao"] == "Cimento CP II"
    assert linha["valor"] == 300.0
    assert linha["fornecedor"] == "Loja ABC"
    assert bool(linha["pago"]) is True


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


def test_carregar_fotos_sem_arquivo_retorna_dataframe_vazio(tmp_path):
    df = carregar_fotos(tmp_path / "fotos.csv")
    assert df.empty
    assert list(df.columns) == ["id", "data", "nome_arquivo", "legenda"]


def test_adicionar_foto_salva_arquivo_e_registro(tmp_path):
    caminho_csv = tmp_path / "fotos.csv"
    dir_fotos = tmp_path / "fotos"

    foto1 = adicionar_foto(b"conteudo-fake-1", "obra1.jpg", "2026-02-01", "Fundação pronta", caminho_csv, dir_fotos)
    foto2 = adicionar_foto(b"conteudo-fake-2", "obra2.png", "2026-01-05", "Início da obra", caminho_csv, dir_fotos)

    assert foto1.id == 1
    assert foto2.id == 2
    assert (dir_fotos / foto1.nome_arquivo).read_bytes() == b"conteudo-fake-1"
    assert (dir_fotos / foto1.nome_arquivo).suffix == ".jpg"

    df = carregar_fotos(caminho_csv)
    assert len(df) == 2
    # ordenadas por data (ordem de execução), não por ordem de inserção
    assert df.iloc[0]["legenda"] == "Início da obra"
    assert df.iloc[1]["legenda"] == "Fundação pronta"


def test_remover_foto_apaga_arquivo_e_registro(tmp_path):
    caminho_csv = tmp_path / "fotos.csv"
    dir_fotos = tmp_path / "fotos"
    foto = adicionar_foto(b"conteudo", "obra.jpg", "2026-02-01", "", caminho_csv, dir_fotos)
    caminho_arquivo = dir_fotos / foto.nome_arquivo
    assert caminho_arquivo.exists()

    remover_foto(foto.id, caminho_csv, dir_fotos)

    assert not caminho_arquivo.exists()
    assert carregar_fotos(caminho_csv).empty


def test_gasto_com_anexo_ida_e_volta(tmp_path):
    caminho = tmp_path / "gastos.csv"
    gasto = adicionar_gasto(
        GastoObra(data="2026-01-10", categoria="Material", descricao="Cimento", valor=250.0, anexo="abc123.pdf"),
        caminho,
    )
    assert gasto.anexo == "abc123.pdf"

    df = carregar_gastos(caminho)
    assert df.iloc[0]["anexo"] == "abc123.pdf"


def test_salvar_ler_remover_arquivo_local(tmp_path):
    nome_arquivo = salvar_arquivo_local(b"conteudo-binario", "comprovante.pdf", tmp_path)

    assert nome_arquivo.endswith(".pdf")
    assert ler_arquivo_local(nome_arquivo, tmp_path) == b"conteudo-binario"

    remover_arquivo_local(nome_arquivo, tmp_path)
    assert not (tmp_path / nome_arquivo).exists()


def test_registrar_e_desregistrar_foto_sem_mexer_no_arquivo(tmp_path):
    caminho_csv = tmp_path / "fotos.csv"
    foto = registrar_foto(FotoObra(data="2026-01-05", nome_arquivo="referencia-externa", legenda="Início"), caminho_csv)

    assert foto.id == 1
    df = carregar_fotos(caminho_csv)
    assert len(df) == 1
    assert df.iloc[0]["nome_arquivo"] == "referencia-externa"

    desregistrar_foto(foto.id, caminho_csv)
    assert carregar_fotos(caminho_csv).empty


def test_adicionar_nota_fiscal_salva_arquivo_e_registro(tmp_path):
    caminho_csv = tmp_path / "notas_fiscais.csv"
    dir_notas = tmp_path / "anexos"

    nota1 = adicionar_nota_fiscal(b"conteudo-fake-1", "nota1.pdf", "2026-02-01", "Compra de cimento", caminho_csv, dir_notas)
    nota2 = adicionar_nota_fiscal(b"conteudo-fake-2", "nota2.jpg", "2026-01-05", "Compra de tijolos", caminho_csv, dir_notas)

    assert nota1.id == 1
    assert nota2.id == 2
    assert (dir_notas / nota1.nome_arquivo).read_bytes() == b"conteudo-fake-1"
    assert (dir_notas / nota1.nome_arquivo).suffix == ".pdf"

    df = carregar_notas_fiscais(caminho_csv)
    assert len(df) == 2
    # ordenadas por data, não por ordem de inserção
    assert df.iloc[0]["legenda"] == "Compra de tijolos"
    assert df.iloc[1]["legenda"] == "Compra de cimento"


def test_remover_nota_fiscal_apaga_arquivo_e_registro(tmp_path):
    caminho_csv = tmp_path / "notas_fiscais.csv"
    dir_notas = tmp_path / "anexos"
    nota = adicionar_nota_fiscal(b"conteudo", "nota.pdf", "2026-02-01", "", caminho_csv, dir_notas)
    caminho_arquivo = dir_notas / nota.nome_arquivo
    assert caminho_arquivo.exists()

    remover_nota_fiscal(nota.id, caminho_csv, dir_notas)

    assert not caminho_arquivo.exists()
    assert carregar_notas_fiscais(caminho_csv).empty


def test_registrar_e_desregistrar_nota_fiscal_sem_mexer_no_arquivo(tmp_path):
    caminho_csv = tmp_path / "notas_fiscais.csv"
    nota = registrar_nota_fiscal(
        NotaFiscalObra(data="2026-01-05", nome_arquivo="referencia-externa", legenda="Nota da loja"), caminho_csv
    )

    assert nota.id == 1
    df = carregar_notas_fiscais(caminho_csv)
    assert len(df) == 1
    assert df.iloc[0]["nome_arquivo"] == "referencia-externa"

    desregistrar_nota_fiscal(nota.id, caminho_csv)
    assert carregar_notas_fiscais(caminho_csv).empty
