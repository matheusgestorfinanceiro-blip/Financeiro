"""Escolhe automaticamente onde os gastos, os dados da obra, as fotos e os
anexos (comprovantes) são salvos.

Duas configurações independentes, ambas opcionais nos secrets do Streamlit:

- `[connections.gsheets]`: se presente, os gastos e os dados da obra (texto/
  números) são salvos numa Google Sheets em vez de arquivo local.
- `drive_folder_id` (dentro do mesmo `[connections.gsheets]`): se presente,
  os arquivos binários (fotos e comprovantes anexados) são enviados para uma
  pasta do Google Drive em vez de salvos localmente.

Sem nenhuma das duas, tudo continua funcionando com arquivos locais
(CSV/JSON), exatamente como antes. Configurando as duas, absolutamente nada
se perde quando o servidor gratuito da Streamlit Cloud dorme ou reinicia."""
import uuid
from pathlib import Path

from src.obra import armazenamento as _local
from src.obra.armazenamento import DIR_ANEXOS, DIR_FOTOS
from src.obra.schema import DadosObra, FotoObra, GastoObra


def usando_planilha() -> bool:
    from src.obra import armazenamento_sheets as _sheets

    return _sheets.disponivel()


def usando_drive() -> bool:
    from src.obra import armazenamento_drive as _drive

    return _drive.disponivel()


def _backend():
    if usando_planilha():
        from src.obra import armazenamento_sheets as _sheets

        return _sheets
    return _local


def obter_conexao():
    """Abre uma conexão nova a cada execução da tela (é barata). Retorna None
    quando o backend é local, já que nesse caso não há conexão nenhuma."""
    if usando_planilha():
        from src.obra import armazenamento_sheets as _sheets

        return _sheets.conectar()
    return None


# --- Gastos --------------------------------------------------------------


def carregar_gastos(conexao=None):
    if usando_planilha():
        return _backend().carregar_gastos(conexao)
    return _local.carregar_gastos()


def adicionar_gasto(conexao, gasto: GastoObra) -> GastoObra:
    if usando_planilha():
        return _backend().adicionar_gasto(conexao, gasto)
    return _local.adicionar_gasto(gasto)


def remover_gasto(conexao, id_gasto) -> None:
    if usando_planilha():
        _backend().remover_gasto(conexao, id_gasto)
    else:
        _local.remover_gasto(id_gasto)


def atualizar_gasto(conexao, gasto: GastoObra) -> None:
    if usando_planilha():
        _backend().atualizar_gasto(conexao, gasto)
    else:
        _local.atualizar_gasto(gasto)


# --- Dados da obra ---------------------------------------------------------


def carregar_dados_obra(conexao=None) -> DadosObra | None:
    if usando_planilha():
        return _backend().carregar_dados_obra(conexao)
    return _local.carregar_dados_obra()


def salvar_dados_obra(conexao, dados: DadosObra) -> None:
    if usando_planilha():
        _backend().salvar_dados_obra(conexao, dados)
    else:
        _local.salvar_dados_obra(dados)


# --- Arquivos binários (fotos e anexos) ------------------------------------


def _id_e_extensao_drive(referencia: str) -> tuple[str, str]:
    """As referências de arquivos no Drive são salvas como "IDdoArquivo.ext"
    (o ID do Drive nunca contém ponto), para o relatório saber se é uma
    imagem ou um PDF sem precisar baixar o arquivo primeiro."""
    if "." in referencia:
        id_arquivo, _, extensao = referencia.partition(".")
        return id_arquivo, f".{extensao}"
    return referencia, ""


def armazenar_arquivo(conteudo: bytes, nome_original: str, diretorio_local: Path) -> str:
    """Salva um arquivo binário de forma permanente (Drive) se configurado,
    senão localmente. Retorna uma referência (ID do Drive + extensão, ou nome
    do arquivo local) para poder ler ou remover depois.

    Se o envio ao Drive falhar (ex: conta do Google sem cota de armazenamento
    para contas de serviço), o arquivo é salvo localmente em vez de travar o
    app - mais vale salvar localmente do que perder o lançamento inteiro."""
    extensao = Path(nome_original).suffix or ""
    if usando_drive():
        from src.obra import armazenamento_drive as _drive

        try:
            nome_unico = f"{uuid.uuid4().hex}{extensao}"
            id_arquivo = _drive.enviar_arquivo(conteudo, nome_unico)
            return f"{id_arquivo}{extensao}"
        except Exception:
            pass
    return _local.salvar_arquivo_local(conteudo, nome_original, diretorio_local)


def obter_arquivo(referencia: str, diretorio_local: Path) -> bytes:
    if not referencia:
        raise ValueError("Nenhum arquivo associado.")
    if usando_drive():
        from src.obra import armazenamento_drive as _drive

        id_arquivo, _ = _id_e_extensao_drive(referencia)
        return _drive.baixar_arquivo(id_arquivo)
    return _local.ler_arquivo_local(referencia, diretorio_local)


def remover_arquivo(referencia: str, diretorio_local: Path) -> None:
    if not referencia:
        return
    if usando_drive():
        from src.obra import armazenamento_drive as _drive

        id_arquivo, _ = _id_e_extensao_drive(referencia)
        _drive.remover_arquivo(id_arquivo)
    else:
        _local.remover_arquivo_local(referencia, diretorio_local)


# --- Fotos (arquivo + metadados) -------------------------------------------


def carregar_fotos(conexao=None):
    if usando_planilha():
        return _backend().carregar_fotos(conexao)
    return _local.carregar_fotos()


def adicionar_foto(conexao, conteudo: bytes, nome_original: str, data: str, legenda: str = "") -> FotoObra:
    nome_arquivo = armazenar_arquivo(conteudo, nome_original, DIR_FOTOS)
    foto = FotoObra(data=data, nome_arquivo=nome_arquivo, legenda=legenda)
    if usando_planilha():
        return _backend().adicionar_foto_registro(conexao, foto)
    return _local.registrar_foto(foto)


def remover_foto(conexao, id_foto) -> None:
    fotos = carregar_fotos(conexao)
    linha = fotos[fotos["id"] == id_foto]
    if not linha.empty:
        remover_arquivo(linha.iloc[0]["nome_arquivo"], DIR_FOTOS)
    if usando_planilha():
        _backend().remover_foto_registro(conexao, id_foto)
    else:
        _local.desregistrar_foto(id_foto)


def obter_bytes_foto(referencia: str) -> bytes:
    return obter_arquivo(referencia, DIR_FOTOS)


# --- Anexos (comprovantes dos gastos) --------------------------------------


def armazenar_anexo(conteudo: bytes, nome_original: str) -> str:
    """Salva o comprovante enviado para gerar um ou mais lançamentos, e
    retorna a referência a ser usada em `GastoObra.anexo`."""
    return armazenar_arquivo(conteudo, nome_original, DIR_ANEXOS)


def obter_bytes_anexo(referencia: str) -> bytes:
    return obter_arquivo(referencia, DIR_ANEXOS)
