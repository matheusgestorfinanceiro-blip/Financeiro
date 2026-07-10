"""Backup em ZIP das fotos e dos anexos (comprovantes) da obra.

Importante quando essas fotos/anexos ficam salvos apenas neste servidor (sem
o Google Drive configurado): o backup em ZIP é a forma de você garantir uma
cópia própria, já que os arquivos locais podem ser apagados quando o app
publicado reinicia."""
import io
import zipfile

from src.obra import repositorio


def gerar_backup_zip(df_gastos, df_fotos) -> bytes:
    """Monta um .zip com todas as fotos (pasta `fotos/`) e todos os anexos
    de comprovantes (pasta `anexos/`), lendo de onde quer que estejam
    guardados (local ou Drive)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_arquivo:
        for foto in df_fotos.itertuples():
            try:
                dados = repositorio.obter_bytes_foto(foto.nome_arquivo)
            except Exception:
                continue
            zip_arquivo.writestr(f"fotos/{foto.data}_{foto.nome_arquivo}", dados)

        referencias = df_gastos[df_gastos["anexo"].astype(str).str.strip() != ""]["anexo"].drop_duplicates()
        for referencia in referencias:
            try:
                dados = repositorio.obter_bytes_anexo(referencia)
            except Exception:
                continue
            zip_arquivo.writestr(f"anexos/{referencia}", dados)

    return buffer.getvalue()
