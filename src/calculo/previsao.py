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
    ConfiguracaoArrecadacao,
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


def _resolver_configuracao(
    config: ConfiguracaoArrecadacao | None,
    numero_unidades_padrao: int,
    unidades_referencia: list[str] | None = None,
) -> pd.DataFrame:
    """Transforma uma ConfiguracaoArrecadacao num valor mensal por unidade
    (colunas unidade/valor), qualquer que seja o modo escolhido:
    - "tipos": uma linha por unidade de cada tipo, com o valor mensal daquele tipo.
    - "fracao_ideal"/"indexador": valor de cada unidade = fração dela vezes o
      valor total mensal a arrecadar.
    - "igual" (ou configuração ausente): `numero_unidades_padrao` unidades
      pagando o mesmo valor mensal - reaproveitando os nomes de unidade de
      `unidades_referencia` quando fornecido (ex: os mesmos nomes já
      definidos pelo rateio principal), para o fundo de reserva e as outras
      arrecadações combinarem com a mesma unidade nas tabelas finais.
    """
    if config is None:
        return pd.DataFrame(columns=["unidade", "valor"])

    if config.modo == "tipos" and config.tipos:
        linhas = [
            {"unidade": f"{tipo.nome} {i + 1}", "valor": tipo.valor}
            for tipo in config.tipos
            for i in range(tipo.quantidade)
        ]
        return pd.DataFrame(linhas, columns=["unidade", "valor"])

    if config.modo in ("fracao_ideal", "indexador") and config.fracoes is not None and not config.fracoes.empty:
        df = config.fracoes.copy()
        soma_fracoes = df["fracao"].sum()
        df["valor"] = df["fracao"] / soma_fracoes * config.valor_total_mensal if soma_fracoes else 0.0
        return df[["unidade", "valor"]]

    if unidades_referencia is not None:
        unidades = list(unidades_referencia)
    else:
        unidades = [f"Unidade {i + 1}" for i in range(numero_unidades_padrao or 0)]
    return pd.DataFrame({"unidade": unidades, "valor": [config.valor_unico] * len(unidades)})


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

    despesas_previstas = _calcular_despesas_previstas(demonstrativo, formulario, percentual_reajuste_automatico)
    total_despesas_historico = sum(l.valor_historico for l in despesas_previstas)
    total_despesas_previsto = sum(l.valor_previsto for l in despesas_previstas)

    total_outras_receitas_previsto = _calcular_outras_receitas_previstas(
        receitas_classificadas, percentual_reajuste_automatico
    )

    rateio_df = _resolver_configuracao(formulario.configuracao_rateio, formulario.numero_unidades)
    rateio_df = rateio_df.rename(columns={"valor": "rateio"})
    numero_unidades = len(rateio_df)

    desconto_pontualidade_total_mensal = 0.0
    if formulario.possui_desconto_pontualidade and not rateio_df.empty:
        if formulario.desconto_pontualidade_modo == "valor_fixo":
            # Nunca deduz mais do que a propria taxa da unidade (evita rateio negativo).
            desconto_por_unidade = rateio_df["rateio"].clip(upper=formulario.desconto_pontualidade_valor)
        else:  # "percentual"
            desconto_por_unidade = rateio_df["rateio"] * formulario.desconto_pontualidade_valor
        desconto_pontualidade_total_mensal = float(desconto_por_unidade.sum())
        rateio_df["rateio"] = rateio_df["rateio"] - desconto_por_unidade

    valores_por_unidade = rateio_df

    unidades_referencia = rateio_df["unidade"].tolist()

    fundo_reserva_valor = 0.0
    if formulario.possui_fundo_reserva and formulario.configuracao_fundo_reserva is not None:
        fundo_df = _resolver_configuracao(formulario.configuracao_fundo_reserva, numero_unidades, unidades_referencia)
        fundo_df = fundo_df.rename(columns={"valor": "fundo_reserva"})
        fundo_reserva_valor = float(fundo_df["fundo_reserva"].sum())
        valores_por_unidade = valores_por_unidade.merge(fundo_df, on="unidade", how="outer")
    else:
        valores_por_unidade["fundo_reserva"] = 0.0

    total_outras_arrecadacoes_previsto = 0.0
    outras_arrecadacoes_detalhe: list[tuple[str, float]] = []
    for nome, config in formulario.outras_arrecadacoes:
        outra_df = _resolver_configuracao(config, numero_unidades, unidades_referencia).rename(columns={"valor": nome})
        total_outra = float(outra_df[nome].sum())
        total_outras_arrecadacoes_previsto += total_outra
        outras_arrecadacoes_detalhe.append((nome, total_outra))
        valores_por_unidade = valores_por_unidade.merge(outra_df, on="unidade", how="outer")

    colunas_valor = [c for c in valores_por_unidade.columns if c != "unidade"]
    valores_por_unidade[colunas_valor] = valores_por_unidade[colunas_valor].fillna(0.0)

    percentual_inadimplencia = inadimplencia.percentual_inadimplencia if inadimplencia else 0.0
    fator_cobertura = 1 - percentual_inadimplencia

    valores_por_unidade["total"] = valores_por_unidade[colunas_valor].sum(axis=1)
    if fator_cobertura > 0:
        valores_por_unidade["total"] = valores_por_unidade["total"] / fator_cobertura

    receita_rateio_necessaria = float(rateio_df["rateio"].sum())
    arrecadacao_prevista_mensal = receita_rateio_necessaria

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
        possui_fundo_reserva=formulario.possui_fundo_reserva,
        receita_rateio_necessaria=receita_rateio_necessaria,
        numero_unidades=numero_unidades,
        percentual_inadimplencia=percentual_inadimplencia,
        total_outras_arrecadacoes_previsto=total_outras_arrecadacoes_previsto,
        outras_arrecadacoes_detalhe=outras_arrecadacoes_detalhe,
        valores_por_unidade=valores_por_unidade,
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
        possui_desconto_pontualidade=formulario.possui_desconto_pontualidade,
        desconto_pontualidade_modo=formulario.desconto_pontualidade_modo,
        desconto_pontualidade_valor=formulario.desconto_pontualidade_valor,
        desconto_pontualidade_total_mensal=desconto_pontualidade_total_mensal,
    )
