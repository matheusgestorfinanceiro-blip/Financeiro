"""Sistema de Previsão Orçamentária Condominial — Azul Administradora.

Para rodar: streamlit run app.py
"""
import streamlit as st

from src.calculo.previsao import calcular_taxas_reajustadas, gerar_previsao
from src.ui.estilo import CAMINHO_LOGO, aplicar_estilo_azul, renderizar_logo
from src.ui.secao_formulario import renderizar_secao_formulario
from src.ui.secao_reajuste import renderizar_secao_reajuste
from src.ui.secao_resultado import renderizar_secao_resultado
from src.ui.secao_upload import renderizar_secao_upload

# page_icon vira o icone da aba do navegador e tambem o icone quando o usuario
# adiciona o sistema a tela inicial do celular ("app"): usa a logo real da
# Azul quando o arquivo existe, senao um emoji de predio como reserva.
_icone_app = str(CAMINHO_LOGO) if CAMINHO_LOGO.exists() else "🏢"
st.set_page_config(
    page_title="Previsão Orçamentária Condominial",
    page_icon=_icone_app,
    layout="wide",
    initial_sidebar_state="collapsed",
)
aplicar_estilo_azul()

renderizar_logo()

dados_inadimplencia, dados_demonstrativo = renderizar_secao_upload()

if dados_demonstrativo is None:
    st.info("Envie ao menos o Demonstrativo de Receitas e Despesas para continuar.", icon="ℹ️")
    st.stop()

st.divider()
formulario = renderizar_secao_formulario(dados_demonstrativo)

if formulario is None:
    st.info("Preencha o formulário acima e clique em 'Confirmar dados' para gerar a previsão.", icon="ℹ️")
    st.stop()

st.divider()
try:
    resultado_draft = gerar_previsao(dados_demonstrativo, dados_inadimplencia, formulario)
except ValueError as e:
    st.error(str(e), icon="⚠️")
    st.stop()

if resultado_draft.percentual_reajuste_automatico > 0:
    resposta_reajuste = renderizar_secao_reajuste(resultado_draft)
    if resposta_reajuste is None:
        st.stop()
    percentual_reajuste, aplicar_ao_fundo_reserva = resposta_reajuste
    resultado = calcular_taxas_reajustadas(resultado_draft, percentual_reajuste, aplicar_ao_fundo_reserva)
else:
    resultado = resultado_draft

st.divider()
renderizar_secao_resultado(resultado)
