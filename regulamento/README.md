# Regulamento Interno & Código de Conduta — TGA Empreendimentos

Documento no formato **cartilha** (2 colunas, no máximo 4 páginas), moderno e humanizado,
com identidade visual da TGA (branco, preto e amarelo) e o logo oficial.

## Arquivo entregue

- **`Regulamento_Interno_TGA.docx`** — versão final, editável no Word / Google Docs.

## O que contém

Boas-vindas, Quem somos (missão, visão, valores e compromissos) e 12 seções:

1. Disposições iniciais e base legal
2. Conduta, ética e patrimônio
3. Confidencialidade e proteção de dados (LGPD)
4. Jornada de trabalho e ponto
5. Férias
6. Uniforme, EPIs e materiais
7. Ambiente e convivência
8. Saúde e segurança
9. Respeito, diversidade e não assédio
10. Recursos, internet e redes sociais
11. Medidas disciplinares
12. Disposições finais

Encerra com **Contatos importantes** e o **Termo de Ciência e Compromisso** (para assinatura).

## Bases legais citadas

CLT (Decreto-Lei 5.452/43), LGPD (Lei 13.709/2018), Lei 14.457/2022 (prevenção ao
assédio), Normas Regulamentadoras (NR-1, NR-5/CIPA e NR-6/EPI) e as Convenções/Acordos
Coletivos da categoria. O texto complementa — e não substitui — o contrato de trabalho e a
legislação vigente.

## Como regenerar o `.docx`

Dentro de `fonte/`:

```bash
npm install docx
node gerar_regulamento.js   # gera Regulamento_Interno_TGA.docx (usa logo_crop.png)
```

O arquivo `logo_crop.png` é o logo oficial recortado (preto sobre fundo branco, opaco),
usado no cabeçalho e no rodapé de assinatura.
