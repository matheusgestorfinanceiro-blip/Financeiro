"""Armazenamento permanente de fotos e anexos (comprovantes) da obra no
Google Drive, usando a mesma credencial de conta de serviço já configurada
para a Planilha do Google (em `[connections.gsheets]`, mais o ID de uma
pasta do Drive). Evita depender de arquivos locais, que são apagados sempre
que o servidor gratuito da Streamlit Cloud reinicia.

Não usa a biblioteca `google-api-python-client` para não adicionar mais uma
dependência pesada: fala direto com a API REST do Drive v3 usando
`google-auth` (já necessário para a Planilha) e `requests`."""
import json
import mimetypes

import streamlit as st
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials

ESCOPOS = ["https://www.googleapis.com/auth/drive"]
URL_UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
URL_ARQUIVOS = "https://www.googleapis.com/drive/v3/files"

_CHAVES_NAO_CREDENCIAL = ("spreadsheet", "worksheet", "drive_folder_id")


def disponivel() -> bool:
    """True se a pasta do Drive e a credencial estiverem configuradas nos secrets."""
    try:
        config = dict(st.secrets["connections"]["gsheets"])
        return bool(config.get("drive_folder_id")) and bool(config.get("client_email"))
    except Exception:
        return False


def _config() -> dict:
    return dict(st.secrets["connections"]["gsheets"])


def _pasta_id() -> str:
    return _config()["drive_folder_id"]


def _sessao() -> AuthorizedSession:
    dados_credencial = _config()
    for chave in _CHAVES_NAO_CREDENCIAL:
        dados_credencial.pop(chave, None)
    credenciais = Credentials.from_service_account_info(dados_credencial, scopes=ESCOPOS)
    return AuthorizedSession(credenciais)


def _montar_corpo_multipart(metadados: dict, conteudo: bytes, tipo_mime: str, limite: str) -> bytes:
    """Monta o corpo multipart/related exigido pelo upload do Drive: uma parte
    JSON com os metadados do arquivo, seguida de uma parte binária com o
    conteúdo. Separado numa função à parte para poder ser testado sem rede."""
    cabecalho = (
        f"--{limite}\r\n"
        "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadados)}\r\n"
        f"--{limite}\r\n"
        f"Content-Type: {tipo_mime}\r\n\r\n"
    ).encode("utf-8")
    rodape = f"\r\n--{limite}--".encode("utf-8")
    return cabecalho + conteudo + rodape


def enviar_arquivo(conteudo: bytes, nome_arquivo: str) -> str:
    """Envia um arquivo para a pasta configurada do Drive e retorna o ID do
    arquivo criado (usado depois para baixar ou remover)."""
    tipo_mime = mimetypes.guess_type(nome_arquivo)[0] or "application/octet-stream"
    limite = "obra_boundary"
    corpo = _montar_corpo_multipart(
        {"name": nome_arquivo, "parents": [_pasta_id()]}, conteudo, tipo_mime, limite
    )

    resposta = _sessao().post(
        URL_UPLOAD,
        params={"uploadType": "multipart", "fields": "id"},
        headers={"Content-Type": f"multipart/related; boundary={limite}"},
        data=corpo,
        timeout=60,
    )
    resposta.raise_for_status()
    return resposta.json()["id"]


def baixar_arquivo(id_arquivo: str) -> bytes:
    resposta = _sessao().get(f"{URL_ARQUIVOS}/{id_arquivo}", params={"alt": "media"}, timeout=60)
    resposta.raise_for_status()
    return resposta.content


def remover_arquivo(id_arquivo: str) -> None:
    resposta = _sessao().delete(f"{URL_ARQUIVOS}/{id_arquivo}", timeout=30)
    if resposta.status_code not in (200, 204, 404):
        resposta.raise_for_status()
