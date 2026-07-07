"""Motor de cálculo da previsão orçamentária. Não depende do Streamlit, então
pode ser testado isoladamente com números simples (veja tests/test_previsao.py)."""
from datetime import date

import pandas as pd

from src.calculo.analise import (
    classificar_despesas,
    classificar_receitas,
    concentracao_inadimplencia_por_competencia,
    mes_pico_inadimplencia as calcular_mes_pico_inadimplencia,
)
from src.models.schema import (
    AjusteManual,
    DadosDemonstrativo,
    DadosFormulario,
    DadosInadimplencia,
    LinhaDespesaPrevista,
    ResultadoPrevisao,
)

TETO_PERCENTUAL_FUNDO_RESERVA = 0.95


def _percentual_para_subcategoria(ajustes: list[AjusteManual], subcategoria: str, padrao: float) -> tuple[float, bool]:
    for ajuste in ajustes:
        if ajuste.subcategoria == subcategoria:
            return ajuste.percentual_reajuste, True
    return padrao, False


def _receita_ordinaria(receitas_classificadas: pd.DataFrame) -> float:
    """Receita ordinária = soma das linhas de receita classificadas como
    recorrentes (regulares mês a mês, veja src/calculo/analise.py), qualquer
    que seja o nome usado na categoria (ex: 'Rateio Mensal', 'Taxa
    Condominial', 'Cota Condominial'). Exclui uma eventual linha de 'fundo de
    reserva' histórico, tratado separadamente e de forma manual."""
    if receitas_classificadas.empty:
        return 0.0
    mascara_fundo_reserva = receitas_classificadas["categoria"].str.contains(
        "fundo de reserva", case=False, na=False
    )
    mascara_ordinaria = receitas_classificadas["classificacao"] == "ordinaria"
    return float(receitas_classificadas[mascara_ordinaria & ~mascara_fundo_reserva]["total"].sum())


def _despesa_ordinaria(despesas_classificadas: pd.DataFrame) -> float:
    """Despesa ordinária = soma das linhas de despesa classificadas como
    recorrentes (exclui despesas extraordinárias/eventuais do histórico)."""
    if despesas_classificadas.empty:
        return 0.0
    mascara_ordinaria = despesas_classificadas["classificacao"] == "ordinaria"
    return float(despesas_classificadas[mascara_ordinaria]["total"].sum())


def _calcular_reajuste_automatico(receita_ordinaria: float, despesa_ordinaria: float) -> float:
    """Se a receita ordinária histórica já cobre a despesa ordinária, não há
    necessidade de reajuste. Caso contrário, calcula o percentual necessário
    para equacionar receita e despesa."""
    if receita_ordinaria <= 0:
        return 0.0
    if receita_ordinaria >= despesa_ordinaria:
        return 0.0
    return (despesa_ordinaria - receita_ordinaria) / receita_ordinaria


def _calcular_despesas_previstas(
    demonstrativo: DadosDemonstrativo, formulario: DadosFormulario, percentual_reajuste: float
) -> list[LinhaDespesaPrevista]:
    linhas = []
    for _, row in demonstrativo.df_despesas.iterrows():
        percentual, foi_manual = _percentual_para_subcategoria(
            formulario.ajustes_manuais, row["subcategoria"], percentual_reajuste
        )
        valor_historico = float(row["total"])
        valor_previsto = valor_historico * (1 + percentual)
        linhas.append(
            LinhaDespesaPrevista(
                categoria_pai=row["categoria_pai"],
                subcategoria=row["subcategoria"],
                valor_historico=valor_historico,
                percentual_reajuste_aplicado=percentual,
                valor_previsto=valor_previsto,
                ajuste_manual=foi_manual,
            )
        )
    return linhas


def _calcular_outras_receitas_previstas(
    receitas_classificadas: pd.DataFrame, percentual_reajuste: float
) -> float:
    """Todas as receitas do histórico classificadas como extraordinárias/eventuais,
    exceto uma eventual linha histórica de 'fundo de reserva' (o fundo de reserva
    da previsão é definido manualmente pelo usuário, não a partir do histórico)."""
    if receitas_classificadas.empty:
        return 0.0
    mascara_fundo_reserva = receitas_classificadas["categoria"].str.contains(
        "fundo de reserva", case=False, na=False
    )
    mascara_ordinaria = receitas_classificadas["classificacao"] == "ordinaria"
    outras = receitas_classificadas[~mascara_ordinaria & ~mascara_fundo_reserva]["total"].sum()
    return float(outras) * (1 + percentual_reajuste)


def _calcular_rateio_por_unidade(formulario: DadosFormulario, receita_necessaria: float) -> pd.DataFrame:
    if formulario.rateio_tipo == "fracao_ideal" and formulario.fracoes_ideais is not None:
        df = formulario.fracoes_ideais.copy()
        soma_fracoes = df["fracao"].sum()
        df["valor"] = df["fracao"] / soma_fracoes * receita_necessaria
        return df[["unidade", "fracao", "valor"]]

    valor_igual = receita_necessaria / formulario.numero_unidades if formulario.numero_unidades else 0.0
    return pd.DataFrame(
        {
            "unidade": [f"Unidade {i+1}" for i in range(formulario.numero_unidades)],
            "fracao": [1 / formulario.numero_unidades] * formulario.numero_unidades if formulario.numero_unidades else [],
            "valor": [valor_igual] * formulario.numero_unidades,
        }
    )


def gerar_previsao(
    demonstrativo: DadosDemonstrativo,
    inadimplencia: DadosInadimplencia | None,
    formulario: DadosFormulario,
) -> ResultadoPrevisao:
    receitas_classificadas = classificar_receitas(demonstrativo)
    despesas_classificadas = classificar_despesas(demonstrativo)

    receita_ordinaria = _receita_ordinaria(receitas_classificadas)
    despesa_ordinaria = _despesa_ordinaria(despesas_classificadas)
    percentual_reajuste_automatico = _calcular_reajuste_automatico(receita_ordinaria, despesa_ordinaria)

    numero_unidades = formulario.numero_unidades

    fundo_reserva_percentual = 0.0
    fundo_reserva_fixo_total = 0.0
    if formulario.possui_fundo_reserva:
        if formulario.fundo_reserva_modo == "valor_fixo":
            fundo_reserva_fixo_total = formulario.fundo_reserva_valor_input * numero_unidades
        else:
            fundo_reserva_percentual = min(formulario.fundo_reserva_valor_input, TETO_PERCENTUAL_FUNDO_RESERVA)

    despesas_previstas = _calcular_despesas_previstas(demonstrativo, formulario, percentual_reajuste_automatico)
    total_despesas_historico = sum(l.valor_historico for l in despesas_previstas)
    total_despesas_previsto = sum(l.valor_previsto for l in despesas_previstas)

    total_outras_receitas_previsto = _calcular_outras_receitas_previstas(
        receitas_classificadas, percentual_reajuste_automatico
    )

    # receita_rateio = despesas + fundo_fixo + fundo_reserva(receita_rateio) - outras_receitas
    # Se fundo_reserva = pct * receita_rateio, então:
    #   receita_rateio * (1 - pct) = despesas + fundo_fixo - outras_receitas
    numerador = total_despesas_previsto + fundo_reserva_fixo_total - total_outras_receitas_previsto
    receita_rateio_calculada = numerador / (1 - fundo_reserva_percentual)

    valor_por_unidade_sugerido = receita_rateio_calculada / numero_unidades if numero_unidades else 0.0

    usa_valor_unico = formulario.valor_unico_por_unidade is not None and formulario.rateio_tipo == "igualitario"
    if usa_valor_unico:
        valor_por_unidade_sem_ajuste = formulario.valor_unico_por_unidade
        receita_rateio_necessaria = valor_por_unidade_sem_ajuste * numero_unidades if numero_unidades else 0.0
        # O valor informado pelo usuário já é uma mensalidade (ex: R$ 150/mês).
        arrecadacao_prevista_mensal = receita_rateio_necessaria
    else:
        valor_por_unidade_sem_ajuste = valor_por_unidade_sugerido
        receita_rateio_necessaria = receita_rateio_calculada
        # receita_rateio_calculada é o total do período de 12 meses; a
        # arrecadação mensal prevista é esse total dividido por 12.
        arrecadacao_prevista_mensal = receita_rateio_calculada / 12

    fundo_reserva_valor = receita_rateio_necessaria * fundo_reserva_percentual + fundo_reserva_fixo_total

    percentual_inadimplencia = inadimplencia.percentual_inadimplencia if inadimplencia else 0.0
    fator_cobertura = 1 - percentual_inadimplencia
    valor_por_unidade_com_inadimplencia = (
        valor_por_unidade_sem_ajuste / fator_cobertura if fator_cobertura > 0 else valor_por_unidade_sem_ajuste
    )

    receita_rateio_ajustada = valor_por_unidade_com_inadimplencia * numero_unidades if numero_unidades else 0.0
    rateio_por_unidade = _calcular_rateio_por_unidade(formulario, receita_rateio_ajustada)

    total_despesas_historico_por_mes = {
        mes: float(demonstrativo.df_despesas[mes].sum()) for mes in demonstrativo.meses
    }
    total_receitas_historico_por_mes = {
        mes: float(demonstrativo.df_receitas[mes].sum()) for mes in demonstrativo.meses
    }

    concentracao_inadimplencia = concentracao_inadimplencia_por_competencia(inadimplencia)
    mes_pico = calcular_mes_pico_inadimplencia(concentracao_inadimplencia)

    inadimplencia_valor_total = inadimplencia.total_geral if inadimplencia else 0.0
    inadimplencia_unidades = (
        sorted(inadimplencia.unidades["unidade"].unique().tolist())
        if inadimplencia is not None and not inadimplencia.unidades.empty
        else []
    )

    return ResultadoPrevisao(
        nome_condominio=formulario.nome_condominio,
        periodo=formulario.periodo,
        observacoes=formulario.observacoes,
        despesas_previstas=despesas_previstas,
        total_despesas_historico=total_despesas_historico,
        total_despesas_previsto=total_despesas_previsto,
        total_outras_receitas_previsto=total_outras_receitas_previsto,
        percentual_reajuste_automatico=percentual_reajuste_automatico,
        fundo_reserva_valor=fundo_reserva_valor,
        fundo_reserva_percentual=fundo_reserva_percentual,
        possui_fundo_reserva=formulario.possui_fundo_reserva,
        fundo_reserva_modo=formulario.fundo_reserva_modo,
        receita_rateio_necessaria=receita_rateio_necessaria,
        numero_unidades=numero_unidades,
        valor_por_unidade_sem_ajuste=valor_por_unidade_sem_ajuste,
        valor_por_unidade_com_inadimplencia=valor_por_unidade_com_inadimplencia,
        percentual_inadimplencia=percentual_inadimplencia,
        valor_por_unidade_sugerido_pelo_sistema=valor_por_unidade_sugerido if usa_valor_unico else None,
        rateio_tipo=formulario.rateio_tipo,
        rateio_por_unidade=rateio_por_unidade,
        total_despesas_historico_por_mes=total_despesas_historico_por_mes,
        total_receitas_historico_por_mes=total_receitas_historico_por_mes,
        receitas_classificadas=receitas_classificadas,
        despesas_classificadas=despesas_classificadas,
        concentracao_inadimplencia=concentracao_inadimplencia,
        mes_pico_inadimplencia=mes_pico,
        data_geracao=date.today().strftime("%d/%m/%Y"),
        arrecadacao_prevista_mensal=arrecadacao_prevista_mensal,
        inadimplencia_valor_total=inadimplencia_valor_total,
        inadimplencia_unidades=inadimplencia_unidades,
    )
