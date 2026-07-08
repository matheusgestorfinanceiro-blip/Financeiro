"""Sistema de Gestão Financeira Pessoal — uso compartilhado do casal.

Para rodar: streamlit run app_financas_pessoais.py
"""
import streamlit as st

st.set_page_config(page_title="Finanças da Família", layout="wide", page_icon="💰")

paginas = [
    st.Page("pages_financeiro/1_lancamentos.py", title="Lançamentos", icon="📝", default=True),
    st.Page("pages_financeiro/2_dashboard.py", title="Dashboard do mês", icon="📊"),
    st.Page("pages_financeiro/3_historico.py", title="Histórico", icon="📅"),
    st.Page("pages_financeiro/4_previsao.py", title="Previsão futura", icon="🔮"),
    st.Page("pages_financeiro/5_backup.py", title="Backup (exportar/importar)", icon="💾"),
]
navegacao = st.navigation(paginas)
navegacao.run()
