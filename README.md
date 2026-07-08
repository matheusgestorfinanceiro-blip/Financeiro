# Financeiro

Página dedicada ao financeiro da Azul Administradora para automações dos processos,
e também a sistemas pessoais: **finanças da família** e **registro de gastos de
obra** (veja as seções dedicadas mais abaixo). São três apps independentes no
mesmo repositório — cada um roda e é publicado separadamente.

## Registro de Obra

Controle simples dos gastos de uma reforma/obra residencial, para acompanhar
o andamento e gerar, ao final, um relatório em PDF para apresentar ao
proprietário do imóvel.

### Como rodar

```
pip install -r requirements.txt
streamlit run app_obra.py
```

Uma aba abre no navegador com uma única tela:

- Preencha uma vez os **dados da obra** (nome, proprietário, endereço, início,
  orçamento previsto e status).
- Lance cada gasto com o mínimo de campos: o que foi, quanto custou, a data
  (sempre no formato dia/mês/ano), a categoria e se já foi pago. Fornecedor e
  observação são opcionais, escondidos em "Mais detalhes" para não atrapalhar
  quem só quer lançar rápido.
- Quando quiser, clique em **Gerar relatório em PDF**: capa, resumo executivo,
  gastos por categoria, evolução no tempo, detalhamento de todos os
  lançamentos e considerações finais.

Os dados ficam salvos localmente em `data/obra/` (CSV/JSON) e não são
versionados no Git, por serem dados financeiros pessoais.

### Estrutura

- `app_obra.py` — tela principal.
- `src/obra/schema.py` — estrutura de um gasto e categorias.
- `src/obra/armazenamento.py` — persistência em CSV/JSON.
- `src/obra/calculo.py` — totais, agrupamentos e formatação de datas.
- `src/obra/graficos.py` — gráficos matplotlib.
- `src/obra/relatorio_pdf.py` — geração do relatório final em PDF.

## Sistema de Finanças Pessoais (uso do casal)

Sistema para organizar receitas e despesas do casal, com lançamentos únicos,
fixos (recorrentes todo mês) e parcelados, dashboard do mês, histórico dos
últimos meses e previsão dos próximos meses. Pensado para ser usado pelos dois
(cada um escolhe o próprio nome na barra lateral antes de lançar).

### Como rodar

```
pip install -r requirements.txt
streamlit run app_financas_pessoais.py
```

Uma aba abre no navegador (normalmente `http://localhost:8501`) com 6 telas
no menu lateral:

- **Lançamentos** — cadastra receitas/despesas quase todo por clique (tipo,
  categoria, quando e repetição são botões; só o valor precisa ser digitado).
  Cada lançamento pode ser:
  - *Única*: acontece só uma vez, no mês da data escolhida (ex: uma compra
    avulsa no mercado).
  - *Fixa*: repete todo mês a partir da data escolhida, indefinidamente (ex:
    salário, aluguel, internet). Pode ser "encerrada" depois, sem apagar o
    histórico já gerado.
  - *Parcelada*: repete pela quantidade de parcelas escolhida (clicando em um
    número pronto como 10x, ou digitando outra quantidade). Todas as parcelas
    futuras já aparecem automaticamente no calendário, no dashboard dos
    próximos meses e na previsão futura.
- **Calendário** — mostra só as despesas a vencer, mês a mês (dia/mês/ano),
  com o total do dia e do mês em destaque, mais uma lista das próximas
  despesas a vencer.
- **Dashboard do mês** — receitas, despesas e saldo do mês escolhido, com
  gráficos de pizza por categoria e o total lançado por cada pessoa.
- **Histórico** — evolução dos últimos meses (receita, despesa e saldo) e a
  lista de todos os lançamentos já cadastrados, com filtros e as opções de
  encerrar (lançamentos fixos) ou excluir.
- **Previsão futura** — projeta os próximos meses a partir dos lançamentos
  fixos e das parcelas em andamento, mostrando quando cada parcela termina.
- **Backup** — exporta todos os lançamentos em CSV (e permite reimportar).
  **Importante:** se este app for publicado na Streamlit Community Cloud, o
  banco de dados local (SQLite, em `data/pessoal/financeiro.db`) é apagado a
  cada novo deploy — exporte o CSV com frequência para não perder o
  histórico. Rodando localmente (`streamlit run`), os dados ficam salvos
  normalmente no arquivo, sem esse risco.

Todas as datas exibidas na tela seguem o formato **dia/mês/ano**.

### Cores

Por convenção do sistema: **receitas em azul**, **despesas em vermelho**, e o
**saldo em verde quando positivo ou vermelho quando negativo** — tanto nos
cartões de totais quanto nos gráficos (inclusive as categorias de despesa em
tons de vermelho e as de receita em tons de azul).

### Estrutura

- `app_financas_pessoais.py` — tela principal.
- `pages_financeiro/` — as 6 telas do Streamlit.
- `src/pessoal/calendario.py` — monta a grade do calendário mensal.
- `src/pessoal/modelos.py` — estrutura de um lançamento e suas categorias.
- `src/pessoal/armazenamento.py` — persistência em SQLite.
- `src/pessoal/projecao.py` — calcula em que meses cada lançamento
  (único/fixo/parcelado) efetivamente ocorre.
- `src/pessoal/analise.py` — resumo do mês, histórico e previsão futura.
- `src/pessoal/graficos.py` — gráficos matplotlib com a paleta semântica.
- `src/pessoal/ui/` — estilo visual e estado compartilhado entre as páginas.

## Sistema de Previsão Orçamentária Condominial

Gera a previsão orçamentária de um condomínio a partir de 2 PDFs (o relatório
de **Inadimplentes** e o **Demonstrativo de Receitas e Despesas**, ambos no
formato já usado hoje pela Azul), mais alguns dados que você preenche, e
entrega **5 páginas finais** (capa, arrecadações, despesas, inadimplência e
reajuste, com gráficos e a assinatura do responsável técnico), exportáveis
em um único PDF pronto para assembleia.

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

### Publicar num endereço público (Streamlit Community Cloud)

Para que qualquer pessoa (síndicos, equipe da Azul etc.) possa usar o
sistema pela internet — enviar os 2 PDFs, preencher o formulário e baixar a
previsão orçamentária — sem precisar instalar nada no próprio computador e
sem conseguir alterar o código ou a configuração do sistema, publique o app
na [Streamlit Community Cloud](https://share.streamlit.io), gratuita:

1. Acesse https://share.streamlit.io e entre com sua conta do GitHub (crie
   uma conta gratuita, se ainda não tiver).
2. Clique em **New app** (ou **Create app**).
3. Selecione o repositório `matheusgestorfinanceiro-blip/Financeiro`, a
   branch `main`, e em **Main file path** digite `app.py`.
4. Clique em **Deploy**. Em alguns minutos, a Streamlit Cloud gera um
   endereço público (algo como `https://algum-nome.streamlit.app`).
5. Esse é o link que pode ser compartilhado com qualquer pessoa: quem
   acessar só enxerga as 3 telas normais do sistema (upload, formulário,
   resultado) — não existe nenhuma forma, pelo navegador, de ver ou alterar
   o código-fonte ou as configurações do sistema. O repositório no GitHub
   pode continuar privado; a Streamlit Cloud só precisa de permissão para
   lê-lo, não que ele seja público.
6. Para atualizar o app publicado depois de qualquer correção nova, basta
   dar `git push` na branch `main` — a Streamlit Cloud atualiza o endereço
   público sozinha, sem nenhuma ação manual.

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
