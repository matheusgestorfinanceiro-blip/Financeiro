"""Identidade visual da Azul Administradora (navy/azul-céu) aplicada ao Streamlit."""
from pathlib import Path

import streamlit as st

# Paleta baseada na logo da Azul Administradora - estimada visualmente a
# partir da imagem da logo (o arquivo em si ainda não está disponível no
# repositório). Mesma paleta usada em src/relatorio/graficos.py, para a tela
# e o PDF final ficarem visualmente consistentes.
NAVY = "#0B3049"
NAVY2 = "#154A66"
CARD = "#0F3A52"
CYAN = "#3FA9D4"
CYAN2 = "#6FC3E0"
GRAY = "#8FA6B2"

CAMINHO_LOGO = Path(__file__).resolve().parents[2] / "data" / "assets" / "logo_azul.png"


def renderizar_logo():
    """Mostra a logo real (data/assets/logo_azul.png) assim que o arquivo
    existir no repositório; até lá, usa um wordmark estilizado com a mesma
    paleta, no mesmo espírito do texto usado como placeholder no PDF."""
    if CAMINHO_LOGO.exists():
        col1, col2 = st.columns([1, 5])
        with col1:
            st.image(str(CAMINHO_LOGO), width=90)
        with col2:
            st.title("Previsão Orçamentária Condominial")
            st.caption("Azul Administradora de Condomínios")
        return

    st.markdown(
        f"""
        <div style="display:flex; align-items:baseline; gap:14px; margin-bottom:0.5rem;">
            <span style="font-size:2.2rem; font-weight:800; letter-spacing:1px;">
                <span style="color:{CYAN};">AZUL</span>
                <span style="color:#FFFFFF;">ADMINISTRADORA</span>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.title("Previsão Orçamentária Condominial")
    st.caption("Azul Administradora de Condomínios")


def aplicar_estilo_azul():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {NAVY};
            color: #FFFFFF;
        }}
        h1, h2, h3 {{
            color: #FFFFFF !important;
        }}
        h1 {{
            border-bottom: none;
        }}
        [data-testid="stHeader"] {{
            background-color: transparent;
        }}
        p, span, label, .stMarkdown, .stCaption {{
            color: #E2E8F0;
        }}
        [data-testid="stCaptionContainer"] {{
            color: {GRAY} !important;
        }}

        /* Cartões: formulário, expanders e containers com borda */
        div[data-testid="stForm"],
        div[data-testid="stExpander"],
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            background-color: {CARD};
            border: 1px solid #1E3A5F;
            border-radius: 14px;
            padding: 0.5rem 0.25rem;
        }}

        /* Botões */
        .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {{
            background-color: {CYAN};
            color: {NAVY};
            border: none;
            border-radius: 8px;
            font-weight: 600;
        }}
        .stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover {{
            background-color: {CYAN2};
            color: {NAVY};
        }}

        /* Inputs */
        input, textarea, .stNumberInput input, .stTextInput input {{
            background-color: {NAVY2} !important;
            color: #FFFFFF !important;
            border-radius: 8px !important;
        }}
        div[data-baseweb="select"] > div {{
            background-color: {NAVY2} !important;
            border-radius: 8px !important;
        }}

        /* Radio e checkbox: texto legível */
        [data-testid="stRadio"] label, [data-testid="stCheckbox"] label {{
            color: #FFFFFF !important;
        }}

        /* Upload de arquivos */
        [data-testid="stFileUploaderDropzone"] {{
            background-color: {NAVY2} !important;
            border: 1px dashed #2E5077 !important;
            border-radius: 10px !important;
        }}
        [data-testid="stFileUploaderDropzone"] span,
        [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stFileUploaderDropzone"] div {{
            color: #E2E8F0 !important;
        }}
        [data-testid="stFileUploaderDropzone"] button[data-testid="stBaseButton-secondary"] {{
            background-color: {CYAN} !important;
            color: {NAVY} !important;
            border: none !important;
            font-weight: 600;
        }}
        [data-testid="stFileChip"] {{
            background-color: {NAVY2} !important;
            border: 1px solid #2E5077 !important;
            border-radius: 8px !important;
        }}
        [data-testid="stFileChipName"] {{
            color: #FFFFFF !important;
        }}
        [data-testid="stFileChip"] div,
        [data-testid="stFileChip"] small {{
            color: #E2E8F0 !important;
        }}
        [data-testid="stFileChipDeleteBtn"] button {{
            background-color: transparent !important;
            color: #E2E8F0 !important;
        }}

        /* Abas */
        button[data-baseweb="tab"] {{
            color: {GRAY};
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: {CYAN} !important;
            border-bottom-color: {CYAN} !important;
        }}

        /* Métricas */
        [data-testid="stMetricValue"] {{
            color: {CYAN2};
        }}
        [data-testid="stMetricLabel"] {{
            color: {GRAY};
        }}

        /* Mensagens (info/warning/success) mantêm contraste sobre fundo escuro */
        div[data-testid="stNotification"] {{
            border-radius: 10px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
