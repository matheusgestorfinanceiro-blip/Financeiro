"""Motor de cálculo da previsão orçamentária. Não depende do Streamlit, então
pode ser testado isoladamente com números simples (veja tests/test_previsao.py)."""
import pandas as pd

from src.models.schema import (
    AjusteManual,
    DadosDemonstrativo,
    DadosFormulario,
    DadosInadimplencia,
    LinhaDespesaPrevista,
    ResultadoPrevisao,
)


def _percentual_para_subcategoria(ajustes: list[AjusteManual], subcategoria: str, padrao: float) -> tuple[float, bool]:
    for ajuste in ajustes:
        if ajuste.subcategoria == subcategoria:
            return ajuste.percentual_reajuste, True
    return padrao, False


def _receita_ordinaria(demonstrativo: DadosDemonstrativo) -> float:
    """Receita ordinária = a linha de rateio mensal (taxa de condomínio) do histórico."""
    df = demonstrativo.df_receitas
    if df.empty:
        return 0.0
    mascara_rateio = df["categoria"].str.contains("rateio", case=False, na=False)
    return float(df[mascara_rateio]["total"].sum())


def _calcular_reajuste_automatico(demonstrativo: DadosDemonstrativo) -> float:
    """Se a receita ordinária histórica já cobre a despesa ordinária, não há
    necessidade de reajuste. Caso contrário, calcula o percentual necessário
    para equacionar receita e despesa."""
    receita_ordinaria = _receita_ordinaria(demonstrativo)
    despesa_ordinaria = demonstrativo.total_despesas
    if receita_ordinaria <= 0:
        return 0.0
    if receita_ordinaria >= despesa_ordinaria:
        return 0.0
    return (despesa_ordinaria - receita_ordinaria) / receita_ordinaria


def _calcular_fundo_reserva_automatico(demonstrativo: DadosDemonstrativo) -> tuple[float, bool]:
    """Procura uma linha de receita de 'fundo de reserva' no histórico e calcula
    o percentual dela sobre a receita ordinária. Retorna (percentual, encontrou_linha)."""
    df = demonstrativo.df_receitas
    if df.empty:
        return 0.0, False
    mascara = df["categoria"].str.contains("fundo de reserva", case=False, na=False)
    if not mascara.any():
        return 0.0, False
    valor_fundo_reserva = float(df[mascara]["total"].sum())
    receita_ordinaria = _receita_ordinaria(demonstrativo)
    if receita_ordinaria <= 0:
        return 0.0, True
    return valor_fundo_reserva / receita_ordinaria, True


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
    demonstrativo: DadosDemonstrativo, percentual_reajuste: float
) -> float:
    """Todas as receitas do histórico, exceto o rateio mensal e o fundo de reserva
    (que já são tratados separadamente no cálculo)."""
    df = demonstrativo.df_receitas
    if df.empty:
        return 0.0
    mascara_rateio = df["categoria"].str.contains("rateio", case=False, na=False)
    mascara_fundo_reserva = df["categoria"].str.contains("fundo de reserva", case=False, na=False)
    outras = df[~mascara_rateio & ~mascara_fundo_reserva]["total"].sum()
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
    percentual_reajuste_automatico = _calcular_reajuste_automatico(demonstrativo)
    fundo_reserva_percentual, fundo_reserva_linha_encontrada = _calcular_fundo_reserva_automatico(demonstrativo)

    TETO_FUNDO_RESERVA = 0.5
    fundo_reserva_percentual_limitado = fundo_reserva_percentual >= TETO_FUNDO_RESERVA
    if fundo_reserva_percentual_limitado:
        fundo_reserva_percentual = TETO_FUNDO_RESERVA

    despesas_previstas = _calcular_despesas_previstas(demonstrativo, formulario, percentual_reajuste_automatico)
    total_despesas_historico = sum(l.valor_historico for l in despesas_previstas)
    total_despesas_previsto = sum(l.valor_previsto for l in despesas_previstas)

    total_outras_receitas_previsto = _calcular_outras_receitas_previstas(demonstrativo, percentual_reajuste_automatico)

    # receita_rateio = despesas + fundo_reserva(receita_rateio) - outras_receitas
    # Se fundo_reserva = pct * receita_rateio, então:
    #   receita_rateio * (1 - pct) = despesas - outras_receitas
    numerador = total_despesas_previsto - total_outras_receitas_previsto
    receita_rateio_calculada = numerador / (1 - fundo_reserva_percentual)

    numero_unidades = formulario.numero_unidades
    valor_por_unidade_sugerido = receita_rateio_calculada / numero_unidades if numero_unidades else 0.0

    usa_valor_unico = formulario.valor_unico_por_unidade is not None and formulario.rateio_tipo == "igualitario"
    if usa_valor_unico:
        valor_por_unidade_sem_ajuste = formulario.valor_unico_por_unidade
        receita_rateio_necessaria = valor_por_unidade_sem_ajuste * numero_unidades if numero_unidades else 0.0
    else:
        valor_por_unidade_sem_ajuste = valor_por_unidade_sugerido
        receita_rateio_necessaria = receita_rateio_calculada

    fundo_reserva_valor = receita_rateio_necessaria * fundo_reserva_percentual

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

    return ResultadoPrevisao(
        nome_condominio=formulario.nome_condominio,
        periodo_inicio=formulario.periodo_inicio,
        periodo_fim=formulario.periodo_fim,
        observacoes=formulario.observacoes,
        despesas_previstas=despesas_previstas,
        total_despesas_historico=total_despesas_historico,
        total_despesas_previsto=total_despesas_previsto,
        total_outras_receitas_previsto=total_outras_receitas_previsto,
        percentual_reajuste_automatico=percentual_reajuste_automatico,
        fundo_reserva_valor=fundo_reserva_valor,
        fundo_reserva_percentual_automatico=fundo_reserva_percentual,
        fundo_reserva_linha_encontrada=fundo_reserva_linha_encontrada,
        fundo_reserva_percentual_limitado=fundo_reserva_percentual_limitado,
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
    )
