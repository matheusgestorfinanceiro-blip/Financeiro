"""Estilo do app de Finanças Pessoais: vermelho p/ despesa, azul p/ receita, verde/vermelho p/ saldo."""
import streamlit as st

AZUL = "#1D4ED8"
VERMELHO = "#DC2626"
VERDE = "#16A34A"
CINZA = "#6B7280"


def aplicar_estilo():
    st.markdown(
        f"""
        <style>
        .cartao-financeiro {{
            border-radius: 12px;
            padding: 1rem 1.25rem;
            border: 1px solid #E5E7EB;
        }}
        .cartao-receita {{ border-left: 6px solid {AZUL}; }}
        .cartao-despesa {{ border-left: 6px solid {VERMELHO}; }}
        .cartao-saldo-positivo {{ border-left: 6px solid {VERDE}; }}
        .cartao-saldo-negativo {{ border-left: 6px solid {VERMELHO}; }}
        .valor-receita {{ color: {AZUL}; font-weight: 700; font-size: 1.6rem; }}
        .valor-despesa {{ color: {VERMELHO}; font-weight: 700; font-size: 1.6rem; }}
        .valor-saldo-positivo {{ color: {VERDE}; font-weight: 700; font-size: 1.6rem; }}
        .valor-saldo-negativo {{ color: {VERMELHO}; font-weight: 700; font-size: 1.6rem; }}
        .rotulo-cartao {{ color: {CINZA}; font-size: 0.85rem; text-transform: uppercase; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def fmt_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def cartao(rotulo: str, valor: float, tipo: str):
    """tipo: 'receita', 'despesa' ou 'saldo'."""
    if tipo == "saldo":
        classe = "saldo-positivo" if valor >= 0 else "saldo-negativo"
    else:
        classe = tipo
    st.markdown(
        f"""
        <div class="cartao-financeiro cartao-{classe}">
            <div class="rotulo-cartao">{rotulo}</div>
            <div class="valor-{classe}">{fmt_moeda(valor)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
