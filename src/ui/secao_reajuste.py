"""Tela intermediária: só aparece quando o Balanço aponta déficit (há reajuste
a propor). Pergunta se o reajuste deve valer também para o fundo de reserva e
se o percentual sugerido deve ser usado ou substituído por um valor
informado pelo usuário, antes de gerar o relatório final."""
import streamlit as st

from src.ui.formatacao import fmt_pct


def renderizar_secao_reajuste(resultado_draft):
    """Recebe o resultado "rascunho" (já calculado, mas ainda sem as taxas
    reajustadas resolvidas) e devolve (percentual_reajuste, aplicar_ao_fundo_reserva)
    depois que o usuário confirmar, ou None enquanto aguarda a confirmação."""
    st.header("A previsão indica necessidade de reajuste")
    st.info(
        f"Com base na receita e despesa ordinárias apuradas, o percentual de reajuste sugerido é "
        f"**{fmt_pct(resultado_draft.percentual_reajuste_automatico)}**. Responda as perguntas abaixo antes de "
        "gerar o relatório final."
    )

    aplicar_ao_fundo_reserva = False
    if resultado_draft.possui_fundo_reserva:
        aplicar_ao_fundo_label = st.radio(
            "O reajuste será aplicado também ao fundo de reserva?",
            ["Não, só no rateio mensal", "Sim, no rateio e no fundo de reserva"],
            horizontal=True, key="reajuste_aplicar_fundo",
        )
        aplicar_ao_fundo_reserva = aplicar_ao_fundo_label.startswith("Sim")

    percentual_label = st.radio(
        "Qual percentual de reajuste deve ser considerado na análise?",
        ["Usar o percentual sugerido", "Informar outro percentual"],
        horizontal=True, key="reajuste_qual_percentual",
    )
    if percentual_label == "Informar outro percentual":
        percentual_informado = st.number_input(
            "Percentual de reajuste a ser aplicado (%)",
            min_value=0.0, max_value=200.0,
            value=round(resultado_draft.percentual_reajuste_automatico * 100, 2), step=0.5,
            key="reajuste_percentual_manual",
        )
        percentual_reajuste = percentual_informado / 100
    else:
        percentual_reajuste = resultado_draft.percentual_reajuste_automatico

    confirmado = st.button("Confirmar e gerar relatório", type="primary")
    if confirmado:
        st.session_state["reajuste_confirmado"] = (percentual_reajuste, aplicar_ao_fundo_reserva)

    return st.session_state.get("reajuste_confirmado")
