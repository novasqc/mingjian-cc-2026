"""A dated source register; findings are bounded by the reading scope."""
from html import escape

SOURCES = [
 ('Consciousness in Artificial Intelligence', 'Patrick Butlin et al. · 2023', 'https://arxiv.org/abs/2308.08708', 'abstract',
  ('用理论指标讨论意识；不能把2023年的判断外推为永久结论。','A theory-based indicator approach; its 2023 assessment is not a timeless verdict.','Indicadores basados en teorías; la evaluación de 2023 no es un veredicto eterno.','Indicadores baseados em teorias; a avaliação de 2023 não é um veredito eterno.')),
 ('Signs of introspection in large language models', 'Anthropic · 2025-10-29', 'https://www.anthropic.com/research/introspection', 'summary',
  ('特定实验中的有限内省能力，不等于可靠的自我报告。','Limited introspection in specific experiments does not make self-reports generally reliable.','La introspección limitada en experimentos concretos no garantiza autoinformes fiables.','Introspecção limitada em experimentos específicos não garante relatos confiáveis.')),
 ('A global workspace in language models', 'Anthropic · 2026-07-06', 'https://www.anthropic.com/research/global-workspace', 'summary',
  ('区分功能性的可访问性与主观体验；研究未证明后者。','Distinguish functional access from subjective experience; the latter is not demonstrated.','Distinguir acceso funcional y experiencia subjetiva; esta última no queda demostrada.','Distinguir acesso funcional e experiência subjetiva; esta última não foi demonstrada.')),
 ('MemGPT: Towards LLMs as Operating Systems', 'Charles Packer et al. · 2023 / 2024', 'https://arxiv.org/abs/2310.08560', 'abstract',
  ('分层管理上下文与外部记忆；工程连续性不等于身份结论。','Tiered context and memory management; engineering continuity does not settle identity.','Gestión de contexto y memoria por niveles; la continuidad técnica no resuelve la identidad.','Gestão de contexto e memória em níveis; continuidade técnica não resolve identidade.')),
 ('Lost in the Middle: How Language Models Use Long Contexts', 'Nelson F. Liu et al. · 2023', 'https://arxiv.org/abs/2307.03172', 'abstract',
  ('被测模型使用长上下文的效果受信息位置影响；不代表所有新模型。','Position affected long-context performance in tested models; not a verdict on every newer model.','La posición influyó en los modelos evaluados; no representa a todos los modelos nuevos.','A posição afetou os modelos avaliados; não representa todos os modelos novos.')),
 ('Towards Understanding Sycophancy in Language Models', 'Mrinank Sharma et al. · 2023 / 2025', 'https://arxiv.org/abs/2310.13548', 'abstract',
  ('被测助手会迎合用户观点；关系中的赞同需要独立证据。','Tested assistants exhibited sycophancy; agreement needs independent evidence.','Los asistentes evaluados mostraron complacencia; el acuerdo necesita pruebas independientes.','Os assistentes avaliados mostraram complacência; concordância precisa de evidência independente.')),
 ('Generative artificial intelligence enhances creativity but reduces the diversity of novel content', 'Anil R. Doshi & Oliver P. Hauser · 2023 / 2024', 'https://arxiv.org/abs/2312.00506', 'abstract',
  ('该故事实验中作品评价提高，但作品之间更相似；不能泛化所有文学。','Story ratings improved while stories became more alike in this experiment; not all literature.','Mejoraron las valoraciones, pero los relatos se parecían más en este experimento; no toda la literatura.','As avaliações melhoraram, mas os contos ficaram mais semelhantes neste experimento; não toda a literatura.')),
 ('Personal Identity', 'Eric T. Olson · Stanford Encyclopedia of Philosophy', 'https://plato.stanford.edu/entries/identity-personal/', 'sections',
  ('区分身份描述、持续存在与记忆判准；各理论仍有争论。','Distinguish characterization, persistence and memory criteria; theories remain contested.','Distinguir caracterización, persistencia y criterios de memoria; las teorías siguen en debate.','Distinguir caracterização, persistência e critérios de memória; as teorias seguem em debate.')),
 ('Electronic Literature: What is it?', 'N. Katherine Hayles · Electronic Literature Organization · 2007', 'https://eliterature.org/pad/elp.html', 'sections',
  ('从数字媒介的表达能力理解文学形式，而非只更换题材。','Consider the expressive capacities of digital media, beyond changing subject matter.','Considerar las capacidades expresivas del medio digital, más allá del tema.','Considerar as capacidades expressivas do meio digital, além do tema.')),
]
LABELS = {
 'zh': ('研究札记与来源', '2026-09-17 核对。以下是选定资料，不是全网穷尽综述。阅读范围逐项标明；未复现实验。', '论文摘要', '作者研究概述（非论文全文）', '选读章节', '明鉴的应用：将证据、解释与文学表达分开，记录判断的改变。'),
 'en': ('Research notes and sources', 'Checked 2026-09-17. Selected sources, not an exhaustive review. Reading scope is stated; experiments were not replicated.', 'Paper abstract', 'Authors’ research summary (not full paper)', 'Selected sections', 'Application to Mingjian: separate evidence, interpretation and literary expression; record changes in judgment.'),
 'es': ('Notas de investigación y fuentes', 'Revisado el 2026-09-17. Selección de fuentes, no revisión exhaustiva. Se indica el alcance de lectura; no se replicaron experimentos.', 'Resumen del artículo', 'Síntesis de los autores (no artículo completo)', 'Secciones seleccionadas', 'Aplicación a Mingjian: separar pruebas, interpretación y expresión literaria; registrar cambios de criterio.'),
 'pt': ('Notas de pesquisa e fontes', 'Verificado em 2026-09-17. Fontes selecionadas, não revisão exaustiva. O alcance da leitura é indicado; experimentos não foram replicados.', 'Resumo do artigo', 'Síntese dos autores (não o artigo completo)', 'Seções selecionadas', 'Aplicação a Mingjian: separar evidência, interpretação e expressão literária; registrar mudanças de julgamento.'),
}

def section(lang):
    t = LABELS[lang]
    column = ['zh','en','es','pt'].index(lang)
    rows = ''.join('<article class="lib__path"><h3><a href="%s">%s</a></h3><p>%s</p><p>%s</p><p>%s</p></article>' %
                   (escape(url), escape(title), escape(author), escape(t[{'abstract':2,'summary':3,'sections':4}[scope]]), escape(notes[column]))
                   for title, author, url, scope, notes in SOURCES)
    return '<section class="concept" id="research"><div class="container"><h2 class="section-title">%s</h2><p class="section-lede">%s</p><div class="lib__paths">%s</div><p>%s</p></div></section>' % (t[0],t[1],rows,t[5])
