"""Estado compartilhado entre as páginas do app de Finanças Pessoais."""
import streamlit as st

from src.pessoal.armazenamento import conectar
from src.pessoal.modelos import USUARIOS_PADRAO


def obter_conexao():
    """Abre uma conexão nova a cada execução da página (SQLite é local e a
    abertura é barata; evita problemas de conexão compartilhada entre threads
    quando o Streamlit executa páginas diferentes em threads diferentes)."""
    return conectar()


def selecionar_usuario() -> str:
    """Mostra na barra lateral quem está lançando (Matheus ou Walkiria) e devolve o nome."""
    if "usuario_atual" not in st.session_state:
        st.session_state.usuario_atual = USUARIOS_PADRAO[0]
    st.session_state.usuario_atual = st.sidebar.selectbox(
        "Quem está usando agora?",
        USUARIOS_PADRAO,
        index=USUARIOS_PADRAO.index(st.session_state.usuario_atual),
    )
    return st.session_state.usuario_atual
