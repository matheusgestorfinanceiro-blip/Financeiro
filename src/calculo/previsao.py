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


def _calcular_despesas_previstas(
    demonstrativo: DadosDemonstrativo, formulario: DadosFormulario
) -> list[LinhaDespesaPrevista]:
    linhas = []
    for _, row in demonstrativo.df_despesas.iterrows():
        percentual, foi_manual = _percentual_para_subcategoria(
            formulario.ajustes_manuais, row["subcategoria"], formulario.percentual_reajuste
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


def _calcular_outras_receitas_previstas(demonstrativo: DadosDemonstrativo, formulario: DadosFormulario) -> float:
    """Todas as receitas do histórico, exceto o rateio mensal (que é o que estamos calculando)."""
    df = demonstrativo.df_receitas
    if df.empty:
        return 0.0
    mascara_rateio = df["categoria"].str.contains("rateio", case=False, na=False)
    outras = df[~mascara_rateio]["total"].sum()
    return float(outras) * (1 + formulario.percentual_reajuste)


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
    despesas_previstas = _calcular_despesas_previstas(demonstrativo, formulario)
    total_despesas_historico = sum(l.valor_historico for l in despesas_previstas)
    total_despesas_previsto = sum(l.valor_previsto for l in despesas_previstas)

    total_outras_receitas_previsto = _calcular_outras_receitas_previstas(demonstrativo, formulario)

    base_fundo_reserva = (
        total_despesas_previsto if formulario.fundo_reserva_base == "despesas" else None
    )
    # Quando a base é "rateio", o fundo de reserva depende da própria receita de
    # rateio (que ainda vamos calcular) - resolvemos isso com uma equação simples:
    # receita_rateio = despesas + fundo_reserva(receita_rateio) + taxa_adm - outras_receitas
    # Se fundo_reserva = pct * receita_rateio, então:
    #   receita_rateio * (1 - pct) = despesas + taxa_adm_fixa - outras_receitas  (quando taxa_adm não depende do rateio)
    taxa_administracao_fixa = 0.0
    taxa_administracao_percentual_sobre_rateio = 0.0
    if formulario.taxa_administracao_modo == "valor_fixo":
        taxa_administracao_fixa = formulario.taxa_administracao_valor * formulario.numero_unidades
    elif formulario.taxa_administracao_modo == "percentual_despesas":
        taxa_administracao_fixa = total_despesas_previsto * formulario.taxa_administracao_valor
    elif formulario.taxa_administracao_modo == "percentual_rateio":
        taxa_administracao_percentual_sobre_rateio = formulario.taxa_administracao_valor

    percentual_sobre_rateio = taxa_administracao_percentual_sobre_rateio
    if formulario.fundo_reserva_base == "rateio":
        percentual_sobre_rateio += formulario.fundo_reserva_percentual

    numerador = total_despesas_previsto + taxa_administracao_fixa - total_outras_receitas_previsto
    if base_fundo_reserva is not None:
        numerador += base_fundo_reserva * formulario.fundo_reserva_percentual

    if percentual_sobre_rateio >= 1:
        raise ValueError(
            "A soma dos percentuais de fundo de reserva e taxa de administração sobre o "
            "rateio não pode ser 100% ou mais."
        )
    receita_rateio_necessaria = numerador / (1 - percentual_sobre_rateio)

    fundo_reserva_valor = (
        base_fundo_reserva * formulario.fundo_reserva_percentual
        if base_fundo_reserva is not None
        else receita_rateio_necessaria * formulario.fundo_reserva_percentual
    )
    taxa_administracao_valor = (
        taxa_administracao_fixa + receita_rateio_necessaria * taxa_administracao_percentual_sobre_rateio
    )

    numero_unidades = formulario.numero_unidades
    valor_por_unidade_sem_ajuste = receita_rateio_necessaria / numero_unidades if numero_unidades else 0.0

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
        fundo_reserva_valor=fundo_reserva_valor,
        taxa_administracao_valor=taxa_administracao_valor,
        receita_rateio_necessaria=receita_rateio_necessaria,
        numero_unidades=numero_unidades,
        valor_por_unidade_sem_ajuste=valor_por_unidade_sem_ajuste,
        valor_por_unidade_com_inadimplencia=valor_por_unidade_com_inadimplencia,
        percentual_inadimplencia=percentual_inadimplencia,
        rateio_tipo=formulario.rateio_tipo,
        rateio_por_unidade=rateio_por_unidade,
        total_despesas_historico_por_mes=total_despesas_historico_por_mes,
        total_receitas_historico_por_mes=total_receitas_historico_por_mes,
    )
