"""Escolhe automaticamente onde os gastos e os dados da obra são salvos.

Se a planilha do Google estiver configurada nos secrets do Streamlit
(`[connections.gsheets]`), os gastos e os dados da obra são salvos lá — o que
sobrevive a reinícios do servidor gratuito da Streamlit Cloud. Sem essa
configuração (rodando localmente, por exemplo), usa arquivos locais CSV/JSON
como antes.

As fotos continuam sempre salvas localmente (são arquivos de imagem, não
cabem numa planilha) — use `src/obra/armazenamento.py` diretamente para elas."""
from src.obra import armazenamento as _local
from src.obra.schema import DadosObra, GastoObra


def usando_planilha() -> bool:
    from src.obra import armazenamento_sheets as _sheets

    return _sheets.disponivel()


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


def carregar_dados_obra(conexao=None) -> DadosObra | None:
    if usando_planilha():
        return _backend().carregar_dados_obra(conexao)
    return _local.carregar_dados_obra()


def salvar_dados_obra(conexao, dados: DadosObra) -> None:
    if usando_planilha():
        _backend().salvar_dados_obra(conexao, dados)
    else:
        _local.salvar_dados_obra(dados)
