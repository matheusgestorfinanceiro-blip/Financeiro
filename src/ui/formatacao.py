"""Formatação de texto para exibição no Streamlit."""


def fmt_moeda(valor: float) -> str:
    """Formata um valor como 'R$ 1.234,56'."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(valor: float) -> str:
    """Formata uma fração (0.175) como '17,50%'."""
    return f"{valor * 100:.2f}".replace(".", ",") + "%"


def escapar_markdown(texto: str) -> str:
    """Escapa caracteres que o Streamlit interpretaria como markdown/LaTeX (ex: '$')."""
    return texto.replace("$", r"\$")
