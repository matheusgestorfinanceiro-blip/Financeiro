import pytest

from src.obra import repositorio


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


class FakeDrive:
    """Simula o Drive guardando os arquivos em memória, sem nenhuma rede."""

    def __init__(self):
        self.arquivos = {}
        self._proximo_id = 1

    def disponivel(self):
        return True

    def enviar_arquivo(self, conteudo, nome_arquivo):
        id_arquivo = f"fake{self._proximo_id}"
        self._proximo_id += 1
        self.arquivos[id_arquivo] = conteudo
        return id_arquivo

    def baixar_arquivo(self, id_arquivo):
        return self.arquivos[id_arquivo]

    def remover_arquivo(self, id_arquivo):
        self.arquivos.pop(id_arquivo, None)


def test_usa_local_quando_planilha_nao_configurada():
    assert repositorio.usando_planilha() is False


def test_usa_local_quando_drive_nao_configurado():
    assert repositorio.usando_drive() is False


def test_obter_conexao_retorna_none_para_backend_local():
    assert repositorio.obter_conexao() is None


def test_armazenar_obter_remover_arquivo_local(tmp_path):
    referencia = repositorio.armazenar_arquivo(b"conteudo-foto", "foto.jpg", tmp_path)

    assert repositorio.obter_arquivo(referencia, tmp_path) == b"conteudo-foto"

    repositorio.remover_arquivo(referencia, tmp_path)
    with pytest.raises(FileNotFoundError):
        repositorio.obter_arquivo(referencia, tmp_path)


def test_armazenar_arquivo_usa_drive_quando_configurado(monkeypatch, tmp_path):
    fake_drive = FakeDrive()
    monkeypatch.setattr("src.obra.armazenamento_drive.disponivel", fake_drive.disponivel)
    monkeypatch.setattr("src.obra.armazenamento_drive.enviar_arquivo", fake_drive.enviar_arquivo)
    monkeypatch.setattr("src.obra.armazenamento_drive.baixar_arquivo", fake_drive.baixar_arquivo)
    monkeypatch.setattr("src.obra.armazenamento_drive.remover_arquivo", fake_drive.remover_arquivo)

    referencia = repositorio.armazenar_arquivo(b"conteudo-drive", "comprovante.pdf", tmp_path)

    assert referencia.endswith(".pdf")
    assert repositorio.obter_arquivo(referencia, tmp_path) == b"conteudo-drive"
    assert not list(tmp_path.iterdir())  # nada foi escrito localmente

    repositorio.remover_arquivo(referencia, tmp_path)
    assert fake_drive.arquivos == {}


def test_fotos_e_anexos_com_planilha_e_drive_configurados(monkeypatch, tmp_path):
    fake_drive = FakeDrive()
    monkeypatch.setattr("src.obra.armazenamento_drive.disponivel", fake_drive.disponivel)
    monkeypatch.setattr("src.obra.armazenamento_drive.enviar_arquivo", fake_drive.enviar_arquivo)
    monkeypatch.setattr("src.obra.armazenamento_drive.baixar_arquivo", fake_drive.baixar_arquivo)
    monkeypatch.setattr("src.obra.armazenamento_drive.remover_arquivo", fake_drive.remover_arquivo)
    monkeypatch.setattr("src.obra.armazenamento_sheets.disponivel", lambda: True)

    conexao = FakeConexao()

    foto = repositorio.adicionar_foto(conexao, b"foto-bytes", "obra.jpg", "2026-01-05", "Início da obra")
    assert foto.id == 1
    assert repositorio.obter_bytes_foto(foto.nome_arquivo) == b"foto-bytes"

    df_fotos = repositorio.carregar_fotos(conexao)
    assert len(df_fotos) == 1

    referencia_anexo = repositorio.armazenar_anexo(b"comprovante-bytes", "nota.pdf")
    assert repositorio.obter_bytes_anexo(referencia_anexo) == b"comprovante-bytes"

    repositorio.remover_foto(conexao, foto.id)
    assert repositorio.carregar_fotos(conexao).empty
    # o arquivo da foto foi removido do Drive, mas o do anexo (independente) continua
    assert referencia_anexo.split(".")[0] in fake_drive.arquivos
