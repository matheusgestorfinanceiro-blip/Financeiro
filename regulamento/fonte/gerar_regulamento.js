// Regulamento Interno TGA - v2: capa (pág.1) + conteúdo coluna única (pág.2-4), assinatura na última
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell,
  WidthType, BorderStyle, ShadingType, AlignmentType, PageBreak, SectionType,
  Header, Footer, PageNumber, VerticalAlign, TabStopType,
} = require('docx');

const BLACK='111111', INK='1F1F1F', YELLOW='FFC400', YSOFT='FFF3CC',
      GBG='F3F3F4', GLINE='E4E4E7', GTXT='5A5A63', WHITE='FFFFFF', FONT='Calibri';

const PAGE_W=11906, PAGE_H=16838, ML=1400, MR=1400, MT=1300, MB=1150;
const CONTENT_W = PAGE_W - ML - MR; // 9106

const logoCrop = fs.readFileSync('logo_crop.png'); // preto sobre branco, opaco

const NOB = { style: BorderStyle.NONE, size:0, color:'auto' };
const noBorders=()=>({ top:NOB,bottom:NOB,left:NOB,right:NOB,insideHorizontal:NOB,insideVertical:NOB });

// ---- runs / paragraphs
const R=(text,o={})=>new TextRun({ text, font:FONT, size:o.size||20, bold:o.bold||false, italics:o.italics||false, color:o.color||INK, allCaps:o.caps||false, characterSpacing:o.spacing, break:o.break });
function body(text,o={}){ return new Paragraph({ alignment:o.align||AlignmentType.JUSTIFIED, spacing:{ after:o.after!=null?o.after:82, before:o.before||0, line:o.line||254 }, indent:o.indent, pageBreakBefore:o.pageBreakBefore, children: Array.isArray(text)?text:[R(text,o)] }); }
const bb=(x)=>new TextRun({ text:x, font:FONT, size:20, bold:true, color:BLACK });
const tt=(x)=>new TextRun({ text:x, font:FONT, size:20, color:INK });

// section header - full width black bar with yellow underline
function head(emoji,title,o={}){
  return new Paragraph({
    shading:{ type:ShadingType.CLEAR, fill:BLACK, color:'auto' },
    border:{ bottom:{ style:BorderStyle.SINGLE, size:16, color:YELLOW, space:1 } },
    spacing:{ before:o.before!=null?o.before:160, after:90, line:264 }, keepNext:true,
    pageBreakBefore:o.pageBreakBefore, indent:{ left:120, right:90 },
    children:[
      new TextRun({ text:`${emoji}  `, font:FONT, size:21, color:WHITE }),
      new TextRun({ text:title, font:FONT, size:21, bold:true, color:WHITE, allCaps:true, characterSpacing:6 }),
    ],
  });
}
function bul(text,o={}){ return new Paragraph({ alignment:AlignmentType.JUSTIFIED, spacing:{ after:o.after!=null?o.after:56, line:254 }, indent:{ left:300, hanging:220 },
  children:[ new TextRun({ text:'▸  ', font:FONT, size:20, bold:true, color:YELLOW }), ...(Array.isArray(text)?text:[R(text,{size:20})]) ] }); }

// callout box (full width, single shaded paragraph)
function box(kind,title,lines){
  const c={ info:{f:YSOFT,b:YELLOW,e:'💡'}, warn:{f:'FDE9E9',b:'D64545',e:'⚠️'}, ok:{f:'E9F5EC',b:'3BA55D',e:'✅'}, legal:{f:GBG,b:BLACK,e:'⚖️'}, star:{f:YELLOW,b:BLACK,e:'⭐'} }[kind];
  const kids=[ new TextRun({ text:`${c.e}  `, font:FONT, size:19 }), new TextRun({ text:title, font:FONT, size:19, bold:true, color:BLACK }) ];
  lines.forEach(l=>kids.push(new TextRun({ text:l, font:FONT, size:18, color:INK, break:1 })));
  return new Paragraph({ shading:{ type:ShadingType.CLEAR, fill:c.f, color:'auto' },
    border:{ left:{ style:BorderStyle.SINGLE, size:24, color:c.b, space:8 } },
    spacing:{ before:62, after:90, line:250 }, indent:{ left:190, right:120 }, children:kids });
}
function legal(text){ return new Paragraph({ shading:{ type:ShadingType.CLEAR, fill:GBG, color:'auto' },
  border:{ left:{ style:BorderStyle.SINGLE, size:22, color:BLACK, space:7 } },
  spacing:{ before:56, after:90, line:246 }, indent:{ left:180, right:110 },
  children:[ new TextRun({ text:'⚖️  ', font:FONT, size:17 }), new TextRun({ text:'Base legal — ', font:FONT, size:17, bold:true, color:BLACK }), new TextRun({ text, font:FONT, size:17, color:INK }) ] }); }

// 2-COLUNAS (uso pontual p/ listas curtas) - tabela sem bordas
function twoCol(leftChildren,rightChildren){
  const half=Math.floor(CONTENT_W/2);
  return new Table({ width:{ size:CONTENT_W, type:WidthType.DXA }, columnWidths:[half, CONTENT_W-half], borders:noBorders(),
    rows:[ new TableRow({ children:[
      new TableCell({ width:{ size:half, type:WidthType.DXA }, borders:noBorders(), margins:{ right:260 }, children:leftChildren }),
      new TableCell({ width:{ size:CONTENT_W-half, type:WidthType.DXA }, borders:noBorders(), margins:{ left:60 }, children:rightChildren }),
    ] }) ] });
}
// item simples de lista compacta (para blocos 2 colunas)
function li(text){ return new Paragraph({ spacing:{ after:44, line:248 }, indent:{ left:250, hanging:200 },
  children:[ new TextRun({ text:'▸  ', font:FONT, size:19, bold:true, color:YELLOW }), new TextRun({ text, font:FONT, size:19, color:INK }) ] }); }

// ============================ CAPA (pág. 1) ============================
const capa=[];
capa.push(new Paragraph({ children:[], spacing:{ after:620 } }));
capa.push(new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ after:260 },
  children:[ new ImageRun({ data:logoCrop, type:'png', transformation:{ width:330, height:153 } }) ] }));
// faixa amarela fina central
capa.push(new Table({ width:{ size:1700, type:WidthType.DXA }, alignment:AlignmentType.CENTER, columnWidths:[1700], borders:noBorders(),
  rows:[ new TableRow({ children:[ new TableCell({ width:{ size:1700, type:WidthType.DXA }, shading:{ type:ShadingType.CLEAR, fill:YELLOW, color:'auto' }, children:[ new Paragraph({ spacing:{ before:34, after:34 }, children:[] }) ] }) ] }) ] }));
capa.push(new Paragraph({ children:[], spacing:{ after:420 } }));
capa.push(new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ after:40, line:260 },
  children:[ new TextRun({ text:'REGULAMENTO INTERNO', font:FONT, size:62, bold:true, color:BLACK, characterSpacing:20 }) ] }));
capa.push(new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ after:300, line:260 },
  children:[ new TextRun({ text:'& CÓDIGO DE CONDUTA', font:FONT, size:34, bold:true, color:YELLOW, characterSpacing:34 }) ] }));
capa.push(new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ after:560 },
  children:[ new TextRun({ text:'Guia do Colaborador  ·  TGA Empreendimentos', font:FONT, size:24, color:GTXT }) ] }));
// caixa preta descritiva
capa.push(new Table({ width:{ size:CONTENT_W, type:WidthType.DXA }, columnWidths:[CONTENT_W], borders:noBorders(),
  rows:[ new TableRow({ children:[ new TableCell({ width:{ size:CONTENT_W, type:WidthType.DXA }, shading:{ type:ShadingType.CLEAR, fill:BLACK, color:'auto' }, margins:{ top:280, bottom:280, left:300, right:300 }, verticalAlign:VerticalAlign.CENTER,
    children:[
      new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ after:70, line:276 }, children:[ new TextRun({ text:'Administração Condominial', font:FONT, size:26, bold:true, color:WHITE }) ] }),
      new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ after:0, line:276 }, children:[ new TextRun({ text:'Operações · Serviços Gerais · Gestão · Tecnologia · Inovação', font:FONT, size:19, color:YELLOW }) ] }),
    ] }) ] }) ] }));
capa.push(new Paragraph({ children:[], spacing:{ after:1500 } }));
capa.push(new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ after:16 }, children:[ new TextRun({ text:'Versão 1.0  ·  Julho de 2026', font:FONT, size:19, color:GTXT }) ] }));
capa.push(new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ after:0 }, children:[ new TextRun({ text:'Documento interno — leia, guarde e consulte sempre que precisar 💛', font:FONT, size:18, color:GTXT }) ] }));

// ============================ CONTEÚDO (pág. 2-4) ============================
const C=[]; const A=(x)=>C.push(x);

// boas-vindas
A(new Paragraph({ spacing:{ before:20, after:60, line:264 }, children:[ new TextRun({ text:'Seja bem-vindo(a) ao Grupo TGA! 👋', font:FONT, size:23, bold:true, color:BLACK }) ] }));
A(body('Que bom ter você com a gente! Este guia mostra, de forma simples, como funcionamos, o que esperamos de você e o que você pode esperar de nós. Leia com calma, guarde com carinho e, na dúvida, fale com o seu líder ou com o RH. Ele complementa — e não substitui — o seu contrato de trabalho e a legislação vigente. 💛'));

// QUEM SOMOS
A(head('🏢','Quem somos', { before:120 }));
A(body([ bb('Missão.  '), tt('Prover serviços de facilities com soluções integradas, aumentando o valor das propriedades e a produtividade dos nossos clientes.') ],{after:70}));
A(body([ bb('Visão.  '), tt('Ser a melhor escolha do mercado na nossa área, servindo sempre com segurança, cortesia e eficiência.') ],{after:90}));
// bloco 2 colunas: Valores | Compromissos (listas curtas)
A(new Paragraph({ spacing:{ after:50, line:264 }, children:[ new TextRun({ text:'Nossos valores e compromissos', font:FONT, size:21, bold:true, color:BLACK }) ], border:{ bottom:{ style:BorderStyle.SINGLE, size:10, color:YELLOW, space:2 } } }));
A(twoCol(
  [ li('Trabalho em equipe 🤝'), li('Melhoria contínua 📈'), li('Agilidade no atendimento ⚡'), li('Comprometimento com resultados 🎯'), li('Respeito à diversidade 🌈'), li('Transparência 🔍') ],
  [ li('Respeito à cultura do cliente'), li('Confidencialidade'), li('Qualidade da entrega'), li('Atualização constante'), li('Uso racional de água e energia 🌱') ]
));

// 1 DISPOSICOES INICIAIS
A(head('📌','1 · Disposições iniciais'));
A(body('Este regulamento reúne as normas de conduta, organização e convivência do Grupo TGA. Vale para todos os colaboradores, em todas as unidades e postos de trabalho, e orienta também estagiários, aprendizes e prestadores, onde aplicável.'));
A(legal('CLT (Decreto-Lei 5.452/43) · LGPD (Lei 13.709/18) · Lei 14.457/22 (assédio) · Normas Regulamentadoras NR-1, NR-5 e NR-6 · Convenções e Acordos Coletivos da categoria. Prevalece sempre a norma mais benéfica ao colaborador.'));

// 2 CONDUTA
A(head('🤝','2 · Conduta, ética e patrimônio'));
A(bul('Trate gestores, colegas, clientes e fornecedores com respeito e cordialidade. Um bom ambiente se constrói todos os dias. 😊'));
A(bul('Respeite a estrutura hierárquica e as orientações compatíveis com a lei, com as normas internas e com as suas funções.'));
A(bul([bb('Brindes: '),tt('é proibido receber presentes de fornecedores ou clientes. São aceitos apenas brindes promocionais (agenda, caneca, copo) até R$ 50,00 por fornecedor/ano.')]));
A(bul('Equipamentos, ferramentas e veículos são de uso exclusivo do trabalho — nunca para fins pessoais. Use com cuidado e devolva em boas condições para o próximo colega.'));

// 3 LGPD
A(head('🔒','3 · Confidencialidade e proteção de dados'));
A(bul('Preserve o sigilo de informações, documentos e dados da empresa, dos clientes e dos parceiros.'));
A(bul('Senhas e acessos são pessoais e intransferíveis: nunca os compartilhe.'));
A(box('legal','LGPD — Lei nº 13.709/2018',['Usar, compartilhar ou guardar dados pessoais só é permitido dentro da finalidade do seu trabalho. Na dúvida sobre o que fazer com uma informação, pergunte antes de agir.']));

// 4 JORNADA
A(head('⏰','4 · Jornada de trabalho e ponto'));
A(bul('Registre os quatro marcos do dia: entrada, saída e retorno do almoço e saída. A tolerância máxima é de 10 minutos por dia.'));
A(bul('Errou o registro? Procure o superior e ajuste. O ponto é registrado nas dependências da empresa (exceto atendimento externo autorizado).'));
A(bul('Faltas ou afastamentos: avise o RH e o líder com antecedência sempre que possível.'));
A(bul('Horas extras só com autorização prévia, compensadas via Banco de Horas.'));
A(box('warn','Ponto é coisa séria',['Registrar o ponto por outro colega — ou pedir que registrem por você — é falta gravíssima e pode gerar demissão por justa causa (art. 482 da CLT).']));

// 5 FERIAS + 6 UNIFORME (duas seções curtas lado a lado em 2 colunas)
A(head('🌴','5 · Férias   |   👕 6 · Uniforme, EPIs e materiais'));
A(twoCol(
  [ li('Direito a férias após 12 meses de trabalho (período aquisitivo).'),
    li('A empresa define o mês, conforme a cobertura das equipes; as datas constam no aviso de férias.'),
    li('Agendamento com, no mínimo, 30 dias de antecedência.') ],
  [ li('Uso obrigatório de uniforme, crachá e EPIs a partir da entrega.'),
    li('Sem uniforme ainda? Use vestimenta compatível com o ambiente profissional.'),
    li('Comunique de imediato dano, perda ou furto. Dano proposital pode ser falta grave, com ressarcimento quando aplicável.') ]
));
A(legal('Férias: 30 dias após cada período aquisitivo (art. 130 da CLT), aviso por escrito com 30 dias (art. 135) e pagamento com o acréscimo de 1/3.  ·  EPI (NR-6): fornecer é dever da empresa; usar e conservar é dever do colaborador — a recusa injustificada é ato faltoso.'));

// 7 AMBIENTE
A(head('🧹','7 · Ambiente de trabalho e convivência'));
A(bul('Mantenha o ambiente e os equipamentos limpos e organizados para o próximo colega.'));
A(bul('Celular particular só nos intervalos: ele atrapalha o trabalho e aumenta o risco de acidentes. 📵'));
A(bul('Copa de uso coletivo: descarte o lixo na lixeira (nunca na pia), guarde apenas alimentos na validade e deixe os equipamentos limpos e desligados.'));
A(bul('A internet nos equipamentos é só para o serviço. Não é permitida a entrada de pessoas não autorizadas nas dependências.'));

// 8 SAUDE
A(head('🛡️','8 · Saúde e segurança no trabalho'));
A(bul('Siga os procedimentos, os treinamentos e a sinalização de segurança. Use os EPIs corretamente.'));
A(bul('Comunique de imediato acidentes (mesmo pequenos) e qualquer situação de risco.'));
A(legal('A empresa mantém as medidas das Normas Regulamentadoras, incluindo o gerenciamento de riscos (NR-1) e a CIPA (NR-5), quando aplicável. Participe dos treinamentos e das campanhas de prevenção.'));

// 9 RESPEITO E ASSEDIO
A(head('🌈','9 · Respeito, diversidade e não assédio'));
A(bul('Respeitamos toda pessoa, sem distinção de gênero, raça, religião, orientação, idade, origem ou deficiência. Discriminação não é tolerada. 💛'));
A(bul([bb('Assédio moral ou sexual e violência não são aceitos. '),tt('Fale com o líder, o RH ou o canal da empresa: sigilo garantido e sem retaliação.')]));
A(legal('Lei nº 14.457/2022: a empresa adota medidas de prevenção ao assédio e à violência no trabalho, com canal de denúncias e proteção a quem, de boa-fé, relata.'));

// 10 RECURSOS DIGITAIS
A(head('💻','10 · Recursos, internet e redes sociais'));
A(bul('Equipamentos, sistemas e internet são ferramentas de trabalho: use-os para as suas funções.'));
A(bul('Não fale em nome da empresa sem autorização, nem divulgue informações internas, de clientes ou de condomínios. Represente bem o Grupo TGA também no mundo digital. 🌐'));

// 11 DISCIPLINA
A(head('⚖️','11 · Medidas disciplinares'));
A(body('Nossa primeira escolha é sempre o diálogo. As medidas seguem a gravidade, de forma proporcional e justa:',{after:56}));
A(body([ bb('Orientação  →  Advertência  →  Suspensão  →  Justa causa.  '), tt('A justa causa aplica-se apenas às hipóteses do art. 482 da CLT. A maioria das situações, porém, se resolve com comunicação clara e boa vontade — se algo não estiver certo, fale. 😊') ]));

// 12 DISPOSICOES FINAIS
A(head('📝','12 · Disposições finais'));
A(bul('Este regulamento pode ser revisto a qualquer tempo, com comunicação aos colaboradores. Casos omissos são tratados pela direção.'));
A(bul('O descumprimento pode caracterizar falta disciplinar, conforme a legislação vigente. Para dúvidas, procure o seu líder imediato ou o RH.'));

// CONTATOS
A(head('📞','Contatos importantes'));
A(twoCol(
  [ new Paragraph({ spacing:{ after:56, line:260 }, children:[ new TextRun({ text:'🧑‍💼  Líder imediato', font:FONT, size:20, bold:true, color:BLACK }) ] }),
    new Paragraph({ spacing:{ after:120, line:256 }, indent:{ left:250 }, children:[ new TextRun({ text:'seu primeiro contato no dia a dia.', font:FONT, size:20, color:INK }) ] }),
    new Paragraph({ spacing:{ after:56, line:260 }, children:[ new TextRun({ text:'💛  Recursos Humanos (RH)', font:FONT, size:20, bold:true, color:BLACK }) ] }),
    new Paragraph({ spacing:{ after:0, line:256 }, indent:{ left:250 }, children:[ new TextRun({ text:'dúvidas, documentos, férias, benefícios e acolhimento.', font:FONT, size:20, color:INK }) ] }) ],
  [ new Paragraph({ spacing:{ after:56, line:260 }, children:[ new TextRun({ text:'🚨  Emergências', font:FONT, size:20, bold:true, color:BLACK }) ] }),
    new Paragraph({ spacing:{ after:60, line:256 }, indent:{ left:250 }, children:[ new TextRun({ text:'Azul Administradora:', font:FONT, size:20, color:INK }) ] }),
    new Paragraph({ spacing:{ after:0, line:256 }, indent:{ left:250 }, children:[ new TextRun({ text:'(73) 3268-2508', font:FONT, size:24, bold:true, color:BLACK }) ] }),
    new Paragraph({ spacing:{ before:60, after:0, line:252 }, indent:{ left:250 }, children:[ new TextRun({ text:'Deixe à mão com seus familiares.', font:FONT, size:18, italics:true, color:GTXT }) ] }) ]
));

// ============================ TERMO (sempre na última página) ============================
A(head('✍️','Termo de ciência e compromisso', { before:200 }));
A(body('Declaro que recebi, li e compreendi o Regulamento Interno & Código de Conduta do Grupo TGA (TGA Empreendimentos) e me comprometo a cumpri-lo, contribuindo para um ambiente de trabalho respeitoso, seguro e produtivo. Estou ciente de que este regulamento complementa o meu contrato de trabalho e a legislação vigente, podendo ser atualizado, com a devida comunicação.',{ after:80 }));
A(box('star','Combinado é combinado 🤝',['Este guia é um compromisso de mão dupla: você cuida do seu papel, e a empresa cuida do ambiente, do respeito e das condições para você crescer. Vamos juntos!']));
function field(label,w){ return new Paragraph({ spacing:{ before:420, after:26, line:240 }, border:{ top:{ style:BorderStyle.SINGLE, size:6, color:BLACK, space:2 } }, children:[ new TextRun({ text:label, font:FONT, size:18, color:GTXT }) ] }); }
const w1=Math.floor(CONTENT_W*0.6), w2=CONTENT_W-w1;
A(new Table({ width:{ size:CONTENT_W, type:WidthType.DXA }, columnWidths:[CONTENT_W], borders:noBorders(), rows:[ new TableRow({ children:[ new TableCell({ width:{ size:CONTENT_W, type:WidthType.DXA }, borders:noBorders(), children:[ field('Nome completo do(a) colaborador(a)', CONTENT_W) ] }) ] }) ] }));
A(new Table({ width:{ size:CONTENT_W, type:WidthType.DXA }, columnWidths:[w1,w2], borders:noBorders(), rows:[ new TableRow({ children:[
  new TableCell({ width:{ size:w1, type:WidthType.DXA }, borders:noBorders(), margins:{ right:300 }, children:[ field('Cargo / Setor', w1) ] }),
  new TableCell({ width:{ size:w2, type:WidthType.DXA }, borders:noBorders(), children:[ field('CPF', w2) ] }) ] }) ] }));
A(new Table({ width:{ size:CONTENT_W, type:WidthType.DXA }, columnWidths:[w1,w2], borders:noBorders(), rows:[ new TableRow({ children:[
  new TableCell({ width:{ size:w1, type:WidthType.DXA }, borders:noBorders(), margins:{ right:300 }, children:[ field('Assinatura', w1) ] }),
  new TableCell({ width:{ size:w2, type:WidthType.DXA }, borders:noBorders(), children:[ field('Local e data', w2) ] }) ] }) ] }));
A(new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ before:340, after:40 }, children:[ new ImageRun({ data:logoCrop, type:'png', transformation:{ width:150, height:70 } }) ] }));
A(new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ after:0 }, children:[ new TextRun({ text:'Obrigado por fazer parte do nosso time. Conte com a gente. 💛', font:FONT, size:18, italics:true, color:GTXT }) ] }));

// ============================ FOOTER (só no conteúdo) ============================
const footer=new Footer({ children:[ new Paragraph({ spacing:{ before:0 },
  border:{ top:{ style:BorderStyle.SINGLE, size:8, color:GLINE, space:6 } },
  tabStops:[{ type:TabStopType.CENTER, position:Math.floor(CONTENT_W/2) },{ type:TabStopType.RIGHT, position:CONTENT_W }],
  children:[ new TextRun({ text:'TGA Empreendimentos', font:FONT, size:15, color:GTXT }),
    new TextRun({ text:'\tRegulamento Interno · Versão 1.0 — 2026\t', font:FONT, size:15, color:GTXT }),
    new TextRun({ children:['Página ', PageNumber.CURRENT], font:FONT, size:15, color:GTXT }) ] }) ] });

const commonPage={ size:{ width:PAGE_W, height:PAGE_H } };

const doc=new Document({
  creator:'TGA Empreendimentos', title:'Regulamento Interno & Código de Conduta - TGA Empreendimentos', description:'Guia do Colaborador',
  styles:{ default:{ document:{ run:{ font:FONT, size:21, color:INK } } } },
  sections:[
    // CAPA - pág.1, sem rodapé
    { properties:{ page:{ ...commonPage, margin:{ top:1000, bottom:1000, left:1200, right:1200 } } }, children:capa },
    // CONTEÚDO - inicia na pág.2, rodapé com número reiniciando em 1... (mantemos contínuo simples)
    { properties:{ page:{ ...commonPage, margin:{ top:MT, bottom:MB, left:ML, right:MR, footer:520 }, pageNumbers:{ start:1 } } }, footers:{ default:footer }, children:C },
  ],
});
Packer.toBuffer(doc).then(b=>{ fs.writeFileSync('Regulamento_Interno_TGA.docx', b); console.log('OK', b.length); });
