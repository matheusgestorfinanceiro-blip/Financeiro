import io
import zipfile

import pandas as pd

from src.obra.armazenamento import adicionar_foto, carregar_fotos
from src.obra.backup import gerar_backup_zip


def test_gerar_backup_zip_sem_fotos_nem_notas_fiscais():
    zip_bytes = gerar_backup_zip(
        pd.DataFrame(columns=["id", "data", "nome_arquivo", "legenda"]),
        pd.DataFrame(columns=["id", "data", "nome_arquivo", "legenda"]),
    )

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_arquivo:
        assert zip_arquivo.namelist() == []


def test_gerar_backup_zip_com_fotos_e_notas_fiscais(tmp_path, monkeypatch):
    caminho_csv = tmp_path / "fotos.csv"
    dir_fotos = tmp_path / "fotos"
    foto = adicionar_foto(b"conteudo-foto", "obra.jpg", "2026-02-01", "Fundação pronta", caminho_csv, dir_fotos)
    df_fotos = carregar_fotos(caminho_csv)

    # substitui a leitura do repositorio pelos arquivos locais de teste (sem
    # depender do diretorio real data/obra/)
    import src.obra.repositorio as repositorio

    monkeypatch.setattr(repositorio, "obter_bytes_foto", lambda ref: (dir_fotos / ref).read_bytes())
    monkeypatch.setattr(repositorio, "obter_bytes_nota_fiscal", lambda ref: b"conteudo-nota")

    df_notas_fiscais = pd.DataFrame(
        [
            {"id": 1, "data": "2026-01-10", "nome_arquivo": "nota.pdf", "legenda": ""},
        ]
    )

    zip_bytes = gerar_backup_zip(df_fotos, df_notas_fiscais)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_arquivo:
        nomes = zip_arquivo.namelist()
        assert f"fotos/{foto.data}_{foto.nome_arquivo}" in nomes
        assert "notas_fiscais/2026-01-10_nota.pdf" in nomes
        assert len(nomes) == 2
