import io
import zipfile

import pandas as pd

from src.obra.armazenamento import adicionar_foto, carregar_fotos
from src.obra.backup import gerar_backup_zip


def _df_gastos_com_anexo():
    return pd.DataFrame(
        [
            {
                "id": 1,
                "data": "2026-01-10",
                "categoria": "Material",
                "descricao": "Cimento",
                "fornecedor": "Loja X",
                "valor": 100.0,
                "pago": True,
                "observacoes": "",
                "anexo": "",
            }
        ]
    )


def test_gerar_backup_zip_sem_fotos_nem_anexos():
    zip_bytes = gerar_backup_zip(_df_gastos_com_anexo(), pd.DataFrame(columns=["id", "data", "nome_arquivo", "legenda"]))

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_arquivo:
        assert zip_arquivo.namelist() == []


def test_gerar_backup_zip_com_fotos_e_anexos(tmp_path, monkeypatch):
    caminho_csv = tmp_path / "fotos.csv"
    dir_fotos = tmp_path / "fotos"
    foto = adicionar_foto(b"conteudo-foto", "obra.jpg", "2026-02-01", "Fundação pronta", caminho_csv, dir_fotos)
    df_fotos = carregar_fotos(caminho_csv)

    # substitui a leitura do repositorio pelos arquivos locais de teste (sem
    # depender do diretorio real data/obra/)
    import src.obra.repositorio as repositorio

    monkeypatch.setattr(repositorio, "obter_bytes_foto", lambda ref: (dir_fotos / ref).read_bytes())
    monkeypatch.setattr(repositorio, "obter_bytes_anexo", lambda ref: b"conteudo-anexo")

    df_gastos = pd.DataFrame(
        [
            {
                "id": 1,
                "data": "2026-01-10",
                "categoria": "Material",
                "descricao": "Cimento",
                "fornecedor": "Loja X",
                "valor": 100.0,
                "pago": True,
                "observacoes": "",
                "anexo": "nota.pdf",
            },
            {
                "id": 2,
                "data": "2026-01-10",
                "categoria": "Material",
                "descricao": "Areia",
                "fornecedor": "Loja X",
                "valor": 50.0,
                "pago": True,
                "observacoes": "",
                "anexo": "nota.pdf",  # mesmo anexo do item acima - nao deve duplicar no zip
            },
        ]
    )

    zip_bytes = gerar_backup_zip(df_gastos, df_fotos)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_arquivo:
        nomes = zip_arquivo.namelist()
        assert f"fotos/{foto.data}_{foto.nome_arquivo}" in nomes
        assert "anexos/nota.pdf" in nomes
        assert len(nomes) == 2  # anexo compartilhado por 2 itens aparece uma unica vez
