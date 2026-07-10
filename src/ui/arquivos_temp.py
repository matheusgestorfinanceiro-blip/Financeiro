"""Salva um arquivo enviado pelo usuário (st.file_uploader) num caminho
temporário local, para os parsers (que recebem um caminho, não o objeto de
upload do Streamlit) poderem lê-lo."""
import tempfile
from pathlib import Path


def salvar_temp(arquivo_enviado) -> str:
    sufixo = Path(arquivo_enviado.name).suffix
    with tempfile.NamedTemporaryFile(suffix=sufixo, delete=False) as tmp:
        tmp.write(arquivo_enviado.getvalue())
        return tmp.name
