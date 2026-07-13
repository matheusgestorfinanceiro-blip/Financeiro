"""Backup em ZIP das fotos e das notas fiscais/comprovantes da obra.

Importante quando esses arquivos ficam salvos apenas neste servidor (sem
o Google Drive configurado): o backup em ZIP é a forma de você garantir uma
cópia própria, já que os arquivos locais podem ser apagados quando o app
publicado reinicia."""
import io
import zipfile

from src.obra import repositorio


def gerar_backup_zip(df_fotos, df_notas_fiscais) -> bytes:
    """Monta um .zip com todas as fotos (pasta `fotos/`) e todas as notas
    fiscais/comprovantes (pasta `notas_fiscais/`), lendo de onde quer que
    estejam guardados (local ou Drive)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_arquivo:
        for foto in df_fotos.itertuples():
            try:
                dados = repositorio.obter_bytes_foto(foto.nome_arquivo)
            except Exception:
                continue
            zip_arquivo.writestr(f"fotos/{foto.data}_{foto.nome_arquivo}", dados)

        for nota in df_notas_fiscais.itertuples():
            try:
                dados = repositorio.obter_bytes_nota_fiscal(nota.nome_arquivo)
            except Exception:
                continue
            zip_arquivo.writestr(f"notas_fiscais/{nota.data}_{nota.nome_arquivo}", dados)

    return buffer.getvalue()
