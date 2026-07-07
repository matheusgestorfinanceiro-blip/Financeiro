"""Sistema de Previsão Orçamentária Condominial — Azul Administradora.

Para rodar: streamlit run app.py
"""
import streamlit as st

from src.calculo.previsao import gerar_previsao
from src.ui.estilo import aplicar_estilo_azul
from src.ui.secao_formulario import renderizar_secao_formulario
from src.ui.secao_resultado import renderizar_secao_resultado
from src.ui.secao_upload import renderizar_secao_upload

st.set_page_config(page_title="Previsão Orçamentária Condominial", layout="wide")
aplicar_estilo_azul()

st.title("Previsão Orçamentária Condominial")
st.caption("Azul Administradora de Condomínios")

dados_inadimplencia, dados_demonstrativo = renderizar_secao_upload()

if dados_demonstrativo is None:
    st.info("Envie ao menos o Demonstrativo de Receitas e Despesas para continuar.")
    st.stop()

st.divider()
formulario = renderizar_secao_formulario(dados_demonstrativo)

if formulario is None:
    st.info("Preencha o formulário acima e clique em 'Confirmar dados' para gerar a previsão.")
    st.stop()

st.divider()
try:
    resultado = gerar_previsao(dados_demonstrativo, dados_inadimplencia, formulario)
except ValueError as e:
    st.error(str(e))
    st.stop()

renderizar_secao_resultado(resultado)
