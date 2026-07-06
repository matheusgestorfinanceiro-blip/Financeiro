"""Identidade visual da Azul Administradora (navy/ciano) aplicada ao Streamlit."""
import streamlit as st

NAVY = "#0A1628"
NAVY2 = "#102447"
CARD = "#0F1F3D"
CYAN = "#00B4D8"
CYAN2 = "#38BDF8"
GRAY = "#94A3B8"


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
