from src.obra import repositorio


def test_usa_local_quando_planilha_nao_configurada():
    assert repositorio.usando_planilha() is False


def test_obter_conexao_retorna_none_para_backend_local():
    assert repositorio.obter_conexao() is None
