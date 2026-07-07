import os

import pytest

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures")


@pytest.fixture
def caminho_inadimplentes():
    return os.path.join(FIXTURES_DIR, "exemplo_inadimplentes.pdf")


@pytest.fixture
def caminho_demonstrativo():
    return os.path.join(FIXTURES_DIR, "exemplo_demonstrativo.pdf")
