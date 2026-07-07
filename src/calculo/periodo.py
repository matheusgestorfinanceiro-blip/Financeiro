"""Funções puras para limpar o nome do condomínio e sugerir o período da
previsão a partir dos meses do histórico."""
import re

MESES_PT = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}

MES_PT_COMPLETO = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def limpar_nome_condominio(bruto: str) -> str:
    """Remove o código inicial (ex: 'W015A ') e o sufixo entre parênteses (ex: ' (42)')."""
    texto = bruto.strip()
    texto = re.sub(r"^[A-Z0-9]+\s+", "", texto)
    texto = re.sub(r"\s*\(\d+\)\s*$", "", texto)
    return texto.strip()


def _parse_mes_ano(mes_str: str) -> tuple[int, int]:
    abrev, ano_str = mes_str.split("/")
    return MESES_PT[abrev.strip().lower()[:3]], int(ano_str)


def sugerir_periodo(meses: list[str]) -> str:
    """A partir dos meses do histórico (ex: ["Jun/2025", ..., "Mai/2026"]),
    sugere o período de avaliação repetindo o mesmo intervalo do demonstrativo,
    como texto único, ex: 'Junho/2025 a Maio/2026'."""
    if not meses:
        return ""
    inicio_mes, inicio_ano = _parse_mes_ano(meses[0])
    fim_mes, fim_ano = _parse_mes_ano(meses[-1])
    return (
        f"{MES_PT_COMPLETO[inicio_mes]}/{inicio_ano} a {MES_PT_COMPLETO[fim_mes]}/{fim_ano}"
    )
