import os

import pytest

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures")


@pytest.fixture
def caminho_inadimplentes():
    return os.path.join(FIXTURES_DIR, "exemplo_inadimplentes.pdf")


@pytest.fixture
def caminho_inadimplentes_horizontal():
    return os.path.join(FIXTURES_DIR, "exemplo_inadimplentes_horizontal.pdf")


@pytest.fixture
def caminho_inadimplentes_singular():
    return os.path.join(FIXTURES_DIR, "exemplo_inadimplentes_singular.pdf")


@pytest.fixture
def caminho_inadimplentes_lote():
    return os.path.join(FIXTURES_DIR, "exemplo_inadimplentes_lote.pdf")


@pytest.fixture
def caminho_inadimplentes_sigla():
    return os.path.join(FIXTURES_DIR, "exemplo_inadimplentes_sigla.pdf")


@pytest.fixture
def caminho_demonstrativo():
    return os.path.join(FIXTURES_DIR, "exemplo_demonstrativo.pdf")


@pytest.fixture
def caminho_fracoes_pdf():
    return os.path.join(FIXTURES_DIR, "exemplo_fracoes.pdf")


@pytest.fixture
def caminho_fracoes_excel():
    return os.path.join(FIXTURES_DIR, "exemplo_fracoes.xlsx")
