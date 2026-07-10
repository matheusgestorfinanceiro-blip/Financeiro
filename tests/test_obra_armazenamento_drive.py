from src.obra.armazenamento_drive import _montar_corpo_multipart, disponivel


def test_disponivel_e_falso_sem_secrets():
    assert disponivel() is False


def test_montar_corpo_multipart_contem_metadados_e_conteudo():
    corpo = _montar_corpo_multipart(
        {"name": "foto.jpg", "parents": ["pasta123"]}, b"BINARIODAFOTO", "image/jpeg", "limite123"
    )

    assert b"--limite123" in corpo
    assert b'"name": "foto.jpg"' in corpo
    assert b'"pasta123"' in corpo
    assert b"Content-Type: image/jpeg" in corpo
    assert b"BINARIODAFOTO" in corpo
    assert corpo.endswith(b"--limite123--")
