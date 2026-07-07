# Financeiro

Página dedicada ao financeiro da Azul Administradora para automações dos processos.

## Sistema de Previsão Orçamentária Condominial

Gera a previsão orçamentária de um condomínio a partir de 2 PDFs (o relatório
de **Inadimplentes** e o **Demonstrativo de Receitas e Despesas**, ambos no
formato já usado hoje pela Azul), mais alguns dados que você preenche, e
entrega **5 páginas finais** (resumo executivo, despesas por categoria,
receitas e rateio por unidade, fundo de reserva/taxa de administração, e
gráficos comparativos), exportáveis em um único PDF pronto para assembleia.

### Como rodar

1. Instale as dependências (só precisa fazer isso uma vez):
   ```
   pip install -r requirements.txt
   ```
2. Inicie o sistema:
   ```
   streamlit run app.py
   ```
3. Uma aba vai abrir no navegador (normalmente em `http://localhost:8501`).
   Siga as 3 etapas na tela: (1) envie os 2 PDFs, (2) preencha os dados da
   previsão, (3) veja e baixe o relatório final em PDF.

### Como rodar os testes automáticos

Sempre que algo for alterado no código, é possível conferir que nada quebrou
rodando:
```
pytest
```
Os testes usam 2 PDFs de exemplo (anonimizados) que ficam em
`data/fixtures/` e conferem se os valores extraídos e calculados batem com o
que se espera.

### Estrutura do projeto

- `app.py` — tela principal (Streamlit).
- `src/parsers/` — leitura dos 2 PDFs de entrada.
- `src/models/` — formatos de dados usados no sistema.
- `src/calculo/` — a matemática da previsão orçamentária (reajuste, fundo de
  reserva, taxa de administração, rateio, ajuste por inadimplência).
- `src/relatorio/` — gráficos e geração do PDF final.
- `src/ui/` — as 3 telas do Streamlit.
- `data/fixtures/` — PDFs de exemplo (anonimizados) usados nos testes.
- `tests/` — testes automáticos.

### Limitações conhecidas (v1)

- O parser do Demonstrativo de Receitas e Despesas espera o mesmo layout que
  o sistema de gestão condominial já gera hoje. Se o layout mudar, os testes
  em `tests/test_demonstrativo_parser.py` vão indicar o problema.
- Em raras categorias cujo nome quebra em duas linhas no PDF, a categoria
  "pai" exibida pode ficar levemente diferente do original — os **totais**
  continuam corretos (isso é conferido automaticamente pelos testes).
