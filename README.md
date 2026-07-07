# Financeiro

Página dedicada ao financeiro da Azul Administradora para automações dos processos.

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
