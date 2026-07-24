// Regulamento Interno TGA - cartilha compacta 2 colunas, max 4 paginas
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell,
  WidthType, BorderStyle, ShadingType, AlignmentType, PageBreak, SectionType,
  Header, Footer, PageNumber, VerticalAlign, TabStopType,
} = require('docx');

// paleta
const BLACK='111111', INK='1F1F1F', YELLOW='FFC400', YSOFT='FFF3CC',
      GBG='F3F3F4', GLINE='E4E4E7', GTXT='5A5A63', WHITE='FFFFFF', FONT='Calibri';

const PAGE_W=11906, PAGE_H=16838, ML=680, MR=680;
const CONTENT_W = PAGE_W - ML - MR; // 10546

const logoCrop = fs.readFileSync('logo_crop.png'); // opaco: preto sobre branco

const NOBORDER = { style: BorderStyle.NONE, size:0, color:'auto' };
function noBorders(){ return { top:NOBORDER,bottom:NOBORDER,left:NOBORDER,right:NOBORDER,insideHorizontal:NOBORDER,insideVertical:NOBORDER }; }

// ---- runs
const R = (text,o={}) => new TextRun({ text, font:FONT, size:o.size||19, bold:o.bold||false, italics:o.italics||false, color:o.color||INK, allCaps:o.caps||false, characterSpacing:o.spacing, break:o.break });

// ---- body paragraph
function body(text,o={}){ return new Paragraph({ alignment:o.align||AlignmentType.JUSTIFIED, spacing:{ after:o.after!=null?o.after:80, before:o.before||0, line:o.line||248 }, indent:o.indent, children: Array.isArray(text)?text:[R(text,o)] }); }

// ---- section header bar (shaded paragraph, flows in columns)
function head(emoji,title){
  return new Paragraph({
    shading:{ type:ShadingType.CLEAR, fill:BLACK, color:'auto' },
    border:{ bottom:{ style:BorderStyle.SINGLE, size:16, color:YELLOW, space:1 } },
    spacing:{ before:190, after:84, line:250 }, keepNext:true,
    indent:{ left:100, right:70 },
    children:[
      new TextRun({ text:`${emoji} `, font:FONT, size:19, color:WHITE }),
      new TextRun({ text:title, font:FONT, size:19, bold:true, color:WHITE, allCaps:true, characterSpacing:4 }),
    ],
  });
}
// small yellow-underlined subhead
function sub(text){ return new Paragraph({ spacing:{ before:90, after:40, line:244 }, keepNext:true,
  border:{ bottom:{ style:BorderStyle.SINGLE, size:8, color:YELLOW, space:2 } },
  children:[ new TextRun({ text, font:FONT, size:18, bold:true, color:BLACK }) ] }); }

// ---- bullet
function bul(text,o={}){ return new Paragraph({ alignment:AlignmentType.JUSTIFIED, spacing:{ after:o.after!=null?o.after:54, line:246 }, indent:{ left:230, hanging:170 },
  children:[ new TextRun({ text:'▸ ', font:FONT, size:18, bold:true, color:YELLOW }), ...(Array.isArray(text)?text:[R(text,{size:18})]) ] }); }
const bb=(x)=>new TextRun({ text:x, font:FONT, size:18, bold:true, color:BLACK });
const tt=(x)=>new TextRun({ text:x, font:FONT, size:18, color:INK });

// ---- callout as single shaded paragraph with line breaks
function box(kind,title,lines){
  const c={ info:{f:YSOFT,b:YELLOW,e:'💡'}, warn:{f:'FDE9E9',b:'D64545',e:'⚠️'}, ok:{f:'E9F5EC',b:'3BA55D',e:'✅'}, legal:{f:GBG,b:BLACK,e:'⚖️'}, star:{f:YELLOW,b:BLACK,e:'⭐'} }[kind];
  const kids=[ new TextRun({ text:`${c.e} `, font:FONT, size:17 }), new TextRun({ text:title, font:FONT, size:17, bold:true, color:BLACK }) ];
  lines.forEach(l=>{ kids.push(new TextRun({ text:l, font:FONT, size:16, color:INK, break:1 })); });
  return new Paragraph({ shading:{ type:ShadingType.CLEAR, fill:c.f, color:'auto' },
    border:{ left:{ style:BorderStyle.SINGLE, size:24, color:c.b, space:6 } },
    spacing:{ before:64, after:82, line:242 }, indent:{ left:160, right:90 }, children:kids });
}
// tiny inline legal note (one line)
function legal(text){ return new Paragraph({ shading:{ type:ShadingType.CLEAR, fill:GBG, color:'auto' },
  border:{ left:{ style:BorderStyle.SINGLE, size:22, color:BLACK, space:5 } },
  spacing:{ before:52, after:76, line:238 }, indent:{ left:150, right:80 },
  children:[ new TextRun({ text:'⚖️ ', font:FONT, size:15 }), new TextRun({ text:'Base legal: ', font:FONT, size:15, bold:true, color:BLACK }), new TextRun({ text, font:FONT, size:15, color:INK }) ] }); }

const spc=(h=60)=>new Paragraph({ children:[], spacing:{ after:h } });

// ===================== MASTHEAD (1 coluna) =====================
const masthead=[];
// logo opaco (preto sobre branco) na área branca do topo
masthead.push(new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ before:40, after:100, line:240 },
  children:[ new ImageRun({ data:logoCrop, type:'png', transformation:{ width:205, height:95 } }) ] }));
// faixa preta com o título
masthead.push(new Paragraph({ shading:{ type:ShadingType.CLEAR, fill:BLACK, color:'auto' },
  alignment:AlignmentType.CENTER, spacing:{ before:120, after:0, line:270 },
  children:[ new TextRun({ text:'REGULAMENTO INTERNO', font:FONT, size:32, bold:true, color:WHITE, characterSpacing:18 }) ] }));
masthead.push(new Paragraph({ shading:{ type:ShadingType.CLEAR, fill:BLACK, color:'auto' },
  alignment:AlignmentType.CENTER, spacing:{ before:0, after:120, line:250 },
  border:{ bottom:{ style:BorderStyle.SINGLE, size:22, color:YELLOW, space:2 } },
  children:[ new TextRun({ text:'& CÓDIGO DE CONDUTA', font:FONT, size:18, bold:true, color:YELLOW, characterSpacing:22 }) ] }));
// subtítulo em cinza sobre o branco
masthead.push(new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ before:70, after:40, line:230 },
  children:[ new TextRun({ text:'Guia do Colaborador  ·  TGA Empreendimentos  ·  Administração Condominial', font:FONT, size:16, color:GTXT }) ] }));

// ===================== CONTEUDO (2 colunas) =====================
const C=[]; const A=(x)=>C.push(x);

// intro boas-vindas
A(new Paragraph({ spacing:{ before:60, after:36, line:224 }, children:[ new TextRun({ text:'Seja bem-vindo(a) ao Grupo TGA! 👋', font:FONT, size:18, bold:true, color:BLACK }) ] }));
A(body('Que bom ter você com a gente! Este guia mostra, de forma simples, como funcionamos, o que esperamos de você e o que você pode esperar de nós. Leia com calma, guarde com carinho e, na dúvida, fale com seu líder ou com o RH. Ele complementa — e não substitui — o seu contrato de trabalho e a legislação vigente. 💛', { after:60 }));

// QUEM SOMOS
A(head('🏢','Quem somos'));
A(body([ bb('Missão. '), tt('Prover serviços de facilities com soluções integradas, aumentando o valor das propriedades e a produtividade dos nossos clientes.') ],{after:34}));
A(body([ bb('Visão. '), tt('Ser a melhor escolha do mercado na nossa área, servindo sempre com segurança, cortesia e eficiência.') ],{after:34}));
A(body([ bb('Valores. '), tt('Trabalho em equipe 🤝 · Melhoria contínua 📈 · Agilidade ⚡ · Comprometimento com resultados 🎯 · Respeito à diversidade 🌈 · Transparência 🔍') ],{after:34}));
A(body([ bb('Compromissos. '), tt('Respeito à cultura do cliente · Confidencialidade · Qualidade da entrega · Atualização constante · Uso racional de água e energia 🌱') ],{after:20}));

// 1 DISPOSICOES INICIAIS
A(head('📌','1 · Disposições iniciais'));
A(body('Este regulamento reúne as normas de conduta, organização e convivência do Grupo TGA. Vale para todos os colaboradores, em todas as unidades e postos de trabalho, e orienta também estagiários, aprendizes e prestadores, onde aplicável.',{after:44}));
A(legal('CLT (DL 5.452/43) · LGPD (Lei 13.709/18) · Lei 14.457/22 (assédio) · NRs 1, 5 e 6 · Convenções e Acordos Coletivos da categoria. Prevalece sempre a norma mais benéfica ao colaborador.'));

// 2 CONDUTA
A(head('🤝','2 · Conduta, ética e patrimônio'));
A(bul('Trate gestores, colegas, clientes e fornecedores com respeito e cordialidade. Um bom ambiente se constrói todos os dias. 😊'));
A(bul('Respeite a estrutura hierárquica e as orientações compatíveis com a lei, as normas internas e as suas funções.'));
A(bul([bb('Brindes: '),tt('proibido receber presentes de fornecedores/clientes. Só brindes promocionais (agenda, caneca, copo) até R$ 50,00 por fornecedor/ano.')]));
A(bul('Equipamentos, ferramentas e veículos são de uso exclusivo do trabalho — nunca para fins pessoais. Use com cuidado e devolva em boas condições.',{after:20}));

// 3 LGPD
A(head('🔒','3 · Confidencialidade e dados (LGPD)'));
A(bul('Preserve o sigilo de informações, documentos e dados da empresa, dos clientes e dos parceiros.'));
A(bul('Senhas e acessos são pessoais e intransferíveis: nunca os compartilhe.',{after:44}));
A(box('legal','LGPD (Lei nº 13.709/2018)',['Usar, compartilhar ou guardar dados pessoais só é permitido dentro da finalidade do seu trabalho. Na dúvida sobre uma informação, pergunte antes de agir.']));

// 4 JORNADA
A(head('⏰','4 · Jornada de trabalho e ponto'));
A(bul('Registre os quatro marcos do dia: entrada, saída e retorno do almoço e saída. Tolerância máxima de 10 minutos por dia.'));
A(bul('Errou? Procure o superior e ajuste. O registro é feito nas dependências (exceto atendimento externo autorizado).'));
A(bul('Faltas ou afastamentos: avise o RH e o líder com antecedência sempre que possível.'));
A(bul('Horas extras só com autorização prévia, compensadas via Banco de Horas.',{after:44}));
A(box('warn','Ponto é coisa séria',['Registrar o ponto por outro colega é falta gravíssima e pode gerar demissão por justa causa (art. 482 da CLT).']));

// 5 FERIAS
A(head('🌴','5 · Férias'));
A(bul('Direito a férias após 12 meses de trabalho (período aquisitivo).'));
A(bul('A empresa define o mês, conforme a cobertura das equipes; as datas constam no aviso de férias.'));
A(bul('Agendamento com, no mínimo, 30 dias de antecedência.',{after:44}));
A(legal('CLT: 30 dias de férias após cada período aquisitivo (art. 130), aviso por escrito com 30 dias (art. 135) e pagamento com o acréscimo de 1/3 constitucional.'));

// 6 UNIFORME
A(head('👕','6 · Uniforme, EPIs e materiais'));
A(bul('Uso obrigatório de uniforme, crachá e EPIs a partir da entrega, sempre que exigidos.'));
A(bul('Sem uniforme ainda? Use vestimenta compatível com o ambiente profissional.'));
A(bul('Comunique de imediato qualquer dano, perda, furto ou defeito. Dano proposital pode ser falta grave, com ressarcimento quando aplicável.',{after:44}));
A(legal('NR-6: fornecer o EPI é dever da empresa; usá-lo e conservá-lo é dever do colaborador. A recusa injustificada é ato faltoso.'));

// 7 AMBIENTE
A(head('🧹','7 · Ambiente e convivência'));
A(bul('Mantenha o ambiente e os equipamentos limpos e organizados para o próximo colega.'));
A(bul('Celular particular só nos intervalos: ele atrapalha o trabalho e aumenta o risco de acidentes. 📵'));
A(bul('Copa de uso coletivo: descarte o lixo na lixeira (nunca na pia), guarde só alimentos na validade e deixe os equipamentos limpos e desligados.'));
A(bul('Internet nos equipamentos só para o serviço. Não é permitida a entrada de pessoas não autorizadas nas dependências.',{after:20}));

// 8 SAUDE
A(head('🛡️','8 · Saúde e segurança'));
A(bul('Siga os procedimentos, treinamentos e a sinalização de segurança. Use os EPIs corretamente.'));
A(bul('Comunique de imediato acidentes (mesmo pequenos) e qualquer situação de risco.',{after:44}));
A(legal('A empresa mantém as medidas das NRs, incluindo o gerenciamento de riscos (NR-1) e a CIPA (NR-5), quando aplicável. Participe dos treinamentos.'));

// 9 RESPEITO E ASSEDIO
A(head('🌈','9 · Respeito, diversidade e não assédio'));
A(bul('Respeitamos toda pessoa, sem distinção de gênero, raça, religião, orientação, idade, origem ou deficiência. Discriminação não é tolerada. 💛'));
A(bul([bb('Assédio moral ou sexual e violência não são aceitos. '),tt('Fale com o líder, o RH ou o canal da empresa: sigilo garantido e sem retaliação.')]),{after:44});
A(legal('Lei nº 14.457/2022: a empresa adota medidas de prevenção ao assédio e à violência, com canal de denúncias e proteção a quem, de boa-fé, relata.'));

// 10 RECURSOS DIGITAIS
A(head('💻','10 · Recursos, internet e redes sociais'));
A(bul('Equipamentos, sistemas e internet são ferramentas de trabalho: use-os para as suas funções.'));
A(bul('Não fale em nome da empresa sem autorização nem divulgue informações internas, de clientes ou de condomínios. Represente bem o Grupo TGA também no mundo digital. 🌐',{after:20}));

// 11 DISCIPLINA
A(head('⚖️','11 · Medidas disciplinares'));
A(body('Nossa primeira escolha é sempre o diálogo. As medidas seguem a gravidade, de forma proporcional e justa:',{after:36}));
A(bul([bb('Orientação → Advertência → Suspensão → Justa causa. '),tt('A justa causa aplica-se só às hipóteses do art. 482 da CLT.')],{after:44}));
A(box('info','O importante é combinar',['A maioria das situações se resolve com comunicação clara e boa vontade. Se algo não estiver certo, fale — é assim que melhoramos juntos.']));

// 12 DISPOSICOES FINAIS
A(head('📝','12 · Disposições finais'));
A(bul('Este regulamento pode ser revisto a qualquer tempo, com comunicação aos colaboradores. Casos omissos são tratados pela direção.'));
A(bul('O descumprimento pode caracterizar falta disciplinar, conforme a legislação vigente. Dúvidas: procure seu líder ou o RH.',{after:44}));

// CONTATOS
A(head('📞','Contatos importantes'));
A(bul([bb('Líder imediato '),tt('— seu primeiro contato no dia a dia.')]));
A(bul([bb('RH 💛 '),tt('— dúvidas, documentos, férias, benefícios e acolhimento.')]));
A(bul([bb('Emergências — Azul Administradora: '),tt('(73) 3268-2508 (deixe à mão com seus familiares). 🚨')],{after:20}));

// ===================== TERMO (1 coluna) =====================
const termo=[];
termo.push(head('✍️','Termo de ciência e compromisso'));
termo.push(body('Declaro que recebi, li e compreendi o Regulamento Interno & Código de Conduta do Grupo TGA e me comprometo a cumpri-lo, contribuindo para um ambiente de trabalho respeitoso, seguro e produtivo. Estou ciente de que ele complementa o meu contrato de trabalho e a legislação vigente, podendo ser atualizado com a devida comunicação.',{ after:150 }));
function field(label,w){ return new TableCell({ width:{ size:w, type:WidthType.DXA }, borders:noBorders(), margins:{ right:200 },
  children:[ new Paragraph({ spacing:{ before:260, after:20, line:220 }, border:{ top:{ style:BorderStyle.SINGLE, size:6, color:BLACK, space:2 } }, children:[ new TextRun({ text:label, font:FONT, size:14, color:GTXT }) ] }) ] }); }
const w1=Math.floor(CONTENT_W*0.62), w2=CONTENT_W-w1;
termo.push(new Table({ width:{ size:CONTENT_W, type:WidthType.DXA }, columnWidths:[CONTENT_W], borders:noBorders(),
  rows:[ new TableRow({ children:[ field('Nome completo do(a) colaborador(a)', CONTENT_W) ] }) ] }));
termo.push(new Table({ width:{ size:CONTENT_W, type:WidthType.DXA }, columnWidths:[w1,w2], borders:noBorders(),
  rows:[ new TableRow({ children:[ field('Cargo / Setor', w1), field('CPF', w2) ] }) ] }));
termo.push(new Table({ width:{ size:CONTENT_W, type:WidthType.DXA }, columnWidths:[w1,w2], borders:noBorders(),
  rows:[ new TableRow({ children:[ field('Assinatura', w1), field('Local e data', w2) ] }) ] }));
termo.push(new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ before:220, after:40 }, children:[ new ImageRun({ data:logoCrop, type:"png", transformation:{ width:150, height:70 } }) ] }));
termo.push(new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ after:0 }, children:[ new TextRun({ text:'Obrigado por fazer parte do nosso time. Conte com a gente. 💛', font:FONT, size:14, italics:true, color:GTXT }) ] }));

// ===================== FOOTER =====================
const footer=new Footer({ children:[ new Paragraph({ spacing:{ before:0 },
  border:{ top:{ style:BorderStyle.SINGLE, size:8, color:GLINE, space:5 } },
  tabStops:[{ type:TabStopType.CENTER, position:Math.floor(CONTENT_W/2) },{ type:TabStopType.RIGHT, position:CONTENT_W }],
  children:[ new TextRun({ text:'TGA Empreendimentos', font:FONT, size:13, color:GTXT }),
    new TextRun({ text:'\tDocumento interno · Versão 1.0 — 2026\t', font:FONT, size:13, color:GTXT }),
    new TextRun({ children:['Pág. ', PageNumber.CURRENT, '/', PageNumber.TOTAL_PAGES], font:FONT, size:13, color:GTXT }) ] }) ] });

const pageProps={ page:{ size:{ width:PAGE_W, height:PAGE_H }, margin:{ top:620, bottom:560, left:ML, right:MR, footer:340 } } };

const doc=new Document({
  creator:'TGA Empreendimentos', title:'Regulamento Interno & Código de Conduta - TGA Empreendimentos', description:'Guia do Colaborador',
  styles:{ default:{ document:{ run:{ font:FONT, size:17, color:INK } } } },
  sections:[
    { properties:{ ...pageProps, column:{ count:1 } }, footers:{ default:footer }, children:masthead },
    { properties:{ ...pageProps, type:SectionType.CONTINUOUS, column:{ count:2, space:420, equalWidth:true } }, footers:{ default:footer }, children:C },
    { properties:{ ...pageProps, type:SectionType.CONTINUOUS, column:{ count:1 } }, footers:{ default:footer }, children:termo },
  ],
});
Packer.toBuffer(doc).then(b=>{ fs.writeFileSync('Regulamento_Interno_TGA.docx', b); console.log('OK', b.length); });
