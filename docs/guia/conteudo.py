import sys
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")
from layout import (Guia, capa, titulo, paragrafo, subtitulo, caixa,
                  ferramenta, lista, TINTA_3)

p = Guia()
capa(p)

# ─────────────────────────────────────────────────────── 1
p.add_page()
p.start_section("1. O que o sistema faz", 0)
titulo(p, "Parte 1", "O que o sistema faz, em um parágrafo")
paragrafo(p,
    "O TERCEIRO360 cuida da vida jurídica de associações, igrejas, fundações e ONGs. "
    "Ele lê o estatuto da entidade, guarda o que está escrito ali (mandato da diretoria, "
    "quórum das assembleias, prazo de convocação) e usa isso para conferir se um ato pode "
    "acontecer. Quando pode, redige o documento pronto para o cartório. Quando não pode, "
    "diz exatamente o que impede e em qual artigo da lei ou do estatuto se apoia.")
caixa(p, "A diferença que importa",
    "Existem muitos geradores de documento: você preenche um formulário e sai um texto. "
    "Este confere antes de gerar. E quando falta uma informação, ele escreve DADO NÃO "
    "INFORMADO em vermelho no lugar — nunca inventa um nome, uma data ou um número. "
    "Um dado plausível e errado num documento que vai a cartório passa despercebido "
    "na revisão; um espaço vermelho, não.")

# ─────────────────────────────────────────────────────── 2
p.start_section("2. As seis camadas", 0)
titulo(p, "Parte 2", "As seis camadas, explicadas como uma casa")
paragrafo(p,
    "Todo sistema desse porte é feito de camadas, cada uma com uma função. A comparação "
    "com uma casa funciona bem:")
lista(p, [
    "A FACHADA E OS CÔMODOS — as telas que você vê e clica. É o que a maioria das "
    "pessoas chama de \"o sistema\".",
    "A ESTRUTURA — vigas e pilares que ninguém vê, mas que sustentam tudo. É onde moram "
    "as regras: quórum, prazo, mandato, o que a lei exige.",
    "O ARQUIVO — onde os documentos e cadastros ficam guardados de forma organizada e "
    "permanente.",
    "A PORTARIA — quem entra, com que senha, e o que cada pessoa pode ver. Ninguém de "
    "um escritório enxerga a entidade de outro.",
    "O ZELADOR — roda sozinho, de tempos em tempos, conferindo prazos que vencem e leis "
    "que mudaram.",
    "O TERRENO — os computadores, na internet, onde tudo isso funciona 24 horas por dia.",
])
paragrafo(p,
    "A parte mais valiosa é a estrutura, e é a menos visível. As regras jurídicas foram "
    "escritas separadas de tudo o mais, sem depender de banco de dados nem de tela. "
    "Isso permite testá-las isoladamente: dá para perguntar ao sistema \"esta assembleia "
    "tinha quórum?\" milhares de vezes, com combinações diferentes, sem precisar abrir "
    "o navegador uma única vez.")

# ─────────────────────────────────────────────────────── 3
p.add_page()
p.start_section("3. As ferramentas", 0)
titulo(p, "Parte 3", "As ferramentas, uma a uma")
paragrafo(p,
    "Nenhuma delas foi escolhida por moda. Cada uma resolve um problema concreto, e "
    "abaixo está qual.")

p.start_section("3.1 Python e FastAPI", 1)
subtitulo(p, "O que sustenta as regras")
ferramenta(p, "Python", "linguagem",
    "A linguagem em que as regras jurídicas foram escritas. Python é conhecido por ser "
    "legível: quem sabe programar minimamente consegue ler e conferir a regra.",
    "As regras aqui são o produto. Elas precisam ser auditáveis por alguém que não "
    "escreveu o código — inclusive por um advogado acompanhado de um técnico.",
    "Gratuito, código aberto.")
ferramenta(p, "FastAPI", "porta de entrada",
    "O programa que recebe os pedidos das telas, aplica as regras e devolve a resposta. "
    "É o balcão entre a fachada e a estrutura.",
    "Gera sozinho a documentação de tudo o que o sistema aceita receber, e confere cada "
    "dado que chega antes de deixá-lo entrar.",
    "Gratuito, código aberto.")

p.start_section("3.2 Next.js e React", 1)
subtitulo(p, "O que você vê")
ferramenta(p, "React", "telas",
    "A biblioteca que monta as telas: botões, formulários, listas, tudo que reage ao seu "
    "clique.",
    "É o padrão de mercado. Encontrar profissional que trabalhe com isso é fácil e "
    "barato — o que importa quando o sistema precisar crescer sem depender de uma "
    "pessoa só.",
    "Gratuito, código aberto.")
ferramenta(p, "Next.js", "servidor das telas",
    "Um andar a mais sobre o React: monta as páginas no servidor antes de mandar para o "
    "navegador. A página chega pronta, em vez de se montar na frente do usuário.",
    "Aqui a razão é de segurança, não de velocidade. O navegador NUNCA fala com o banco "
    "nem com a API diretamente: ele fala com o Next, e o Next fala com o resto. A senha "
    "de acesso ao sistema nunca chega ao navegador de ninguém.",
    "Gratuito, código aberto.")
ferramenta(p, "Tailwind CSS", "aparência",
    "O conjunto de regras visuais: cores, espaçamentos, tamanhos de letra.",
    "Mantém a aparência consistente entre telas feitas em momentos diferentes, sem que "
    "alguém precise lembrar qual era o tom exato do azul.",
    "Gratuito, código aberto.")

p.add_page()
p.start_section("3.3 PostgreSQL", 1)
subtitulo(p, "Onde os dados ficam")
ferramenta(p, "PostgreSQL", "banco de dados",
    "O arquivo onde tudo é guardado: entidades, atos, documentos, prazos, histórico.",
    "É o banco de dados livre mais respeitado do mundo para dados que não podem se "
    "perder nem se contradizer. Bancos, cartórios e órgãos públicos usam. Não é o mais "
    "moderno; é o mais confiável, e aqui isso vale mais.",
    "Gratuito, código aberto. Paga-se pela hospedagem, não pelo programa.")

p.start_section("3.4 Supabase", 1)
subtitulo(p, "Quem cuida do banco")
ferramenta(p, "Supabase", "hospedagem do banco",
    "Uma empresa que mantém o PostgreSQL rodando por você: liga, mantém ligado, faz "
    "cópia de segurança e avisa se algo der errado.",
    "Sem isso, alguém teria que administrar um servidor de banco de dados — tarefa "
    "especializada, de tempo integral. O banco foi criado em SÃO PAULO, e essa escolha "
    "é jurídica: os dados de brasileiros ficam em território brasileiro, o que simplifica "
    "muito a conversa sobre a LGPD.",
    "Plano gratuito hoje. Cerca de US$ 25/mês quando o uso crescer.")

p.start_section("3.5 Render", 1)
subtitulo(p, "Onde o sistema roda")
ferramenta(p, "Render", "hospedagem do sistema",
    "Os computadores, na internet, que mantêm o sistema no ar. Você não compra máquina "
    "nem instala nada: manda o código e ele passa a funcionar num endereço.",
    "Faz tudo sozinho a cada mudança: pega a versão nova, monta, testa se subiu e "
    "substitui a anterior. Se a nova versão não subir, a antiga continua no ar.",
    "Plano gratuito hoje — com a limitação de que o sistema \"dorme\" sem uso e demora "
    "até 50 segundos para acordar. Cerca de US$ 7/mês por serviço para resolver isso.")

p.start_section("3.6 Git e GitHub", 1)
subtitulo(p, "A memória do projeto")
ferramenta(p, "Git e GitHub", "histórico e cópia",
    "O Git registra cada alteração feita no código, com data, autor e motivo. O GitHub "
    "guarda esse histórico na internet.",
    "Duas coisas: dá para voltar a qualquer versão anterior se algo quebrar, e o código "
    "não vive só no computador de uma pessoa. Se a máquina se perder, o projeto não "
    "se perde junto.",
    "Gratuito para repositório privado.")

p.add_page()
p.start_section("3.7 As bibliotecas de apoio", 1)
subtitulo(p, "As peças menores, mas necessárias")
paragrafo(p,
    "Além das principais, o sistema usa peças especializadas. Nenhuma exige decisão sua, "
    "mas vale saber que existem:")
lista(p, [
    "ALEMBIC — controla a evolução do banco de dados. Quando o sistema ganha um campo "
    "novo, é ele que aplica a mudança sem perder o que já estava gravado.",
    "PYTHON-DOCX e FPDF2 — geram os arquivos Word e PDF dos documentos, na formatação "
    "que os cartórios costumam aceitar: A4, margens 3-2-3-2, Times 12, entrelinha 1,5.",
    "JINJA2 — o motor dos modelos de documento. É ele que, ao encontrar um dado ausente, "
    "escreve DADO NÃO INFORMADO em vez de deixar em branco.",
    "BCRYPT — transforma senhas em algo que não pode ser revertido. Nem quem tem acesso "
    "ao banco consegue descobrir a senha de alguém.",
    "PYOTP — o segundo fator de autenticação, aquele código de seis dígitos que muda a "
    "cada trinta segundos.",
])

# ─────────────────────────────────────────────────────── 4
p.start_section("4. Onde o sistema mora", 0)
titulo(p, "Parte 4", "Onde o sistema mora, hoje")
paragrafo(p, "São três lugares, cada um com uma função distinta:")
lista(p, [
    "GITHUB — guarda o código-fonte e o histórico de tudo que já foi alterado.",
    "RENDER (Oregon, Estados Unidos) — executa o sistema. São dois serviços: a API, que "
    "aplica as regras, e o painel, que desenha as telas.",
    "SUPABASE (São Paulo, Brasil) — guarda os dados. Entidades, atos, documentos, "
    "usuários.",
])
caixa(p, "Sobre os dados ficarem no Brasil",
    "O sistema roda nos Estados Unidos, mas os DADOS ficam em São Paulo. Essa separação "
    "é intencional. Onde o programa é executado tem pouca relevância jurídica; onde os "
    "dados pessoais residem tem muita. Se um dia for necessário trazer também a execução "
    "para o Brasil, é uma mudança de configuração, não de código.")

# ─────────────────────────────────────────────────────── 5
p.add_page()
p.start_section("5. Quanto custa", 0)
titulo(p, "Parte 5", "Quanto custa")
paragrafo(p,
    "Hoje o sistema inteiro está em planos gratuitos — custo zero, com duas limitações "
    "reais: os serviços dormem quando ninguém usa (a primeira abertura do dia demora "
    "até 50 segundos) e o banco gratuito tem espaço e cópias de segurança limitados. "
    "Serve para testar e demonstrar. Não serve para atender cliente pagante.")
subtitulo(p, "O que muda ao começar a vender")
lista(p, [
    "RENDER, dois serviços pagos — cerca de US$ 14/mês. Acaba a espera de 50 segundos.",
    "SUPABASE, plano Pro — cerca de US$ 25/mês. Cópias de segurança diárias e a "
    "possibilidade de voltar o banco a um momento no passado.",
    "DOMÍNIO PRÓPRIO — cerca de R$ 40/ano. Trocar o endereço atual por algo como "
    "app.terceiro360.com.br.",
])
paragrafo(p,
    "Total aproximado: US$ 40/mês, algo em torno de R$ 220. Esse valor atende bem os "
    "primeiros clientes. Ele só cresce de verdade quando o volume de dados ou de acessos "
    "crescer — e aí já haverá receita para acompanhar.")
caixa(p, "O que não está nessa conta",
    "Inteligência artificial. O módulo de IA jurídica ainda não foi construído, e quando "
    "for, o custo é por uso: cada consulta é cobrada. É a única despesa do sistema que "
    "varia com o movimento, e por isso precisa ser medida antes de entrar no preço "
    "cobrado do cliente.")

# ─────────────────────────────────────────────────────── 6
p.add_page()
p.start_section("6. Segurança, sem jargão", 0)
titulo(p, "Parte 6", "Segurança, sem jargão")
paragrafo(p, "O que foi feito para o sistema não ser invadido, em linguagem direta:")
lista(p, [
    "SENHAS NÃO SÃO GUARDADAS. O que fica no banco é um resultado matemático que não "
    "pode ser revertido. Nem quem tiver o banco inteiro nas mãos descobre a senha "
    "de alguém.",
    "CPF E RG SÃO CIFRADOS. Quem olhasse a tabela veria texto embaralhado. A chave que "
    "decifra não está no banco.",
    "SEGUNDO FATOR. Além da senha, um código de seis dígitos que muda a cada trinta "
    "segundos. Senha vazada, sozinha, não abre nada.",
    "CINCO ERROS TRAVAM A CONTA por quinze minutos. Sem isso, um programa testaria "
    "milhões de senhas por hora.",
    "O NAVEGADOR NÃO FALA COM O BANCO. Nunca. Ele fala com o servidor das telas, e só "
    "esse servidor fala com o resto. Não há como \"espiar\" a conexão pelo navegador.",
    "CADA ESCRITÓRIO SÓ ENXERGA O QUE É SEU. A separação não é uma tela que esconde: "
    "é uma regra aplicada em cada consulta ao banco.",
    "TUDO FICA REGISTRADO. Quem entrou, quando, de onde, e o que alterou.",
])
caixa(p, "Uma ressalva honesta",
    "Nada disso significa que o sistema é inviolável — nenhum é. Significa que as falhas "
    "mais comuns e mais exploradas foram fechadas por desenho, não por remendo. Antes de "
    "atender cliente pagante, vale contratar um teste de invasão independente: alguém "
    "pago para tentar entrar e relatar por onde conseguiu.")

# ─────────────────────────────────────────────────────── 7
p.add_page()
p.start_section("7. Vocabulário de bolso", 0)
titulo(p, "Parte 7", "Vocabulário de bolso")
paragrafo(p, "Sete palavras que vão aparecer em qualquer conversa técnica sobre o sistema:")
termos = [
    ("Backend", "a parte que ninguém vê: regras, cálculos, acesso ao banco."),
    ("Frontend", "a parte visível: as telas."),
    ("API", "o balcão entre os dois. Recebe pedido, devolve resposta."),
    ("Deploy", "publicar uma versão nova. Aqui é automático a cada alteração."),
    ("Repositório", "a pasta com o código e todo o histórico dele."),
    ("Migração", "mudança na estrutura do banco sem perder o que está gravado."),
    ("Multi-tenant", "vários clientes no mesmo sistema, sem um ver o do outro."),
]
p.set_font("Sans", "", 10)
for termo, definicao in termos:
    if p.get_y() > 258:
        p.add_page()
    y = p.get_y()
    p.set_font("Sans", "B", 10)
    p.set_text_color(28, 74, 94)
    p.set_xy(22, y)
    p.cell(32, 5.6, termo)
    p.set_font("Sans", "", 10)
    p.set_text_color(74, 80, 88)
    p.set_xy(54, y)
    p.multi_cell(136, 5.6, definicao)
    p.ln(2)

p.ln(6)
caixa(p, "Em uma frase",
    "O sistema foi construído com ferramentas gratuitas e maduras, escolhidas por serem "
    "confiáveis e por terem muitos profissionais no mercado; os dados moram no Brasil; "
    "e o custo para começar a vender é da ordem de R$ 220 por mês.")

p.set_font("Sans", "I", 8.5)
p.set_text_color(*TINTA_3)
p.multi_cell(170, 5,
    "TERCEIRO360 — Inteligência e automação para o Terceiro Setor. A automação auxilia "
    "na preparação e validação dos documentos, mas não substitui a análise profissional "
    "quando esta for necessária.")

p.output(sys.argv[2])
print("gerado:", sys.argv[2], "-", p.page_no(), "páginas")
