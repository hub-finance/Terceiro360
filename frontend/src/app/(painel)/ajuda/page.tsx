/** Ajuda do TERCEIRO360.
 *
 * Escrita para quem abriu o sistema pela primeira vez e não vai ler manual.
 * Não consulta a API de propósito: é a página que precisa abrir justamente
 * quando alguma outra coisa não abriu.
 */
import Link from "next/link";

import { Cartao } from "@/componentes/base";

export const metadata = { title: "Ajuda" };

const SUMARIO = [
  { id: "comecar", rotulo: "Por onde começar" },
  { id: "lacunas", rotulo: "As lacunas em vermelho" },
  { id: "semaforo", rotulo: "O semáforo: apto, pendente, bloqueado" },
  { id: "atos", rotulo: "Gerar um ato" },
  { id: "protocolos", rotulo: "Levar ao cartório" },
  { id: "prazos", rotulo: "Prazos e pendências" },
  { id: "fontes", rotulo: "Central de Fontes" },
  { id: "conta", rotulo: "Senha e segundo fator" },
  { id: "limites", rotulo: "O que o sistema não faz" },
];

export default function PaginaAjuda() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">Ajuda</h1>
        <p className="mt-1 text-[0.875rem] leading-relaxed text-[var(--color-tinta-3)]">
          O essencial para usar o sistema com segurança. Dez minutos de leitura,
          e você não precisa ler tudo de uma vez.
        </p>
      </header>

      <nav aria-label="Nesta página" className="mb-8">
        <Cartao>
          <ul className="grid gap-x-6 gap-y-1.5 sm:grid-cols-2">
            {SUMARIO.map((item) => (
              <li key={item.id}>
                <a
                  href={`#${item.id}`}
                  className="text-[0.8125rem] text-[var(--color-marca)] underline-offset-2 hover:underline"
                >
                  {item.rotulo}
                </a>
              </li>
            ))}
          </ul>
        </Cartao>
      </nav>

      <Secao id="comecar" titulo="Por onde começar">
        <p>
          Tudo no sistema gira em torno de uma <strong>entidade</strong> — a associação,
          a fundação ou a igreja com que você está trabalhando. Escolha a entidade no
          seletor no alto do menu à esquerda; o menu inteiro passa a se referir a ela.
        </p>
        <p>
          O primeiro passo com uma entidade nova é sempre o <strong>Estatuto</strong>.
          É dali que o sistema extrai mandato, quórum, prazo de convocação e forma de
          eleição. Sem estatuto lido, ele não tem como conferir nada — e vai dizer isso,
          em vez de supor.
        </p>
        <Passos
          itens={[
            "Selecione a entidade no menu.",
            "Abra Estatuto e confira o que foi extraído.",
            "Corrija o que estiver errado — o que você corrige vale a partir dali.",
            "Só então gere atos.",
          ]}
        />
      </Secao>

      <Secao id="lacunas" titulo="As lacunas em vermelho">
        <p>
          Quando falta uma informação, o documento sai com{" "}
          <span className="font-semibold text-[var(--color-bloqueado)]">
            DADO NÃO INFORMADO
          </span>{" "}
          em vermelho e negrito, no lugar exato onde a informação deveria estar.
        </p>
        <p>
          Isso é proposital e é o comportamento mais importante do sistema:{" "}
          <strong>ele nunca preenche por conta própria</strong>. Um nome plausível,
          uma data provável ou um número arredondado num documento que vai a cartório
          é pior do que um espaço em branco, porque passa despercebido na revisão.
        </p>
        <p>
          Vermelho no documento não é erro do sistema. É o sistema te mostrando o que
          falta antes que o cartório mostre.
        </p>
      </Secao>

      <Secao id="semaforo" titulo="O semáforo: apto, pendente, bloqueado">
        <p>
          Atos e entidades aparecem com um sinal de três cores. Ele resume, num relance,
          se aquilo pode seguir adiante:
        </p>
        <ul className="space-y-2.5">
          <ItemFarol cor="var(--color-apto)" titulo="Apto">
            Nada impede. Os requisitos de lei e de estatuto foram conferidos e batem.
          </ItemFarol>
          <ItemFarol cor="var(--color-pendencia)" titulo="Pendente">
            Falta informação ou uma conferência humana. Dá para continuar trabalhando,
            mas não para dar por concluído.
          </ItemFarol>
          <ItemFarol cor="var(--color-bloqueado)" titulo="Bloqueado">
            Há um impedimento concreto — quórum insuficiente, prazo de convocação não
            cumprido, mandato vencido. O sistema diz qual é e em que norma se apoia.
          </ItemFarol>
        </ul>
        <p>
          Clicar no sinal abre o motivo por extenso, com o dispositivo legal ou o artigo
          do estatuto em que ele se baseia. Nenhum bloqueio é uma opinião sem fonte.
        </p>
      </Secao>

      <Secao id="atos" titulo="Gerar um ato">
        <p>
          Em <strong>Atos → Novo</strong> você escolhe o tipo do ato — eleição e posse,
          alteração de denominação, alteração estatutária, prestação de contas do
          exercício, entre outros. Cada tipo tem suas próprias exigências, e o sistema
          já as conhece.
        </p>
        <Passos
          itens={[
            "Escolha o tipo do ato e a data da assembleia.",
            "Informe se a assembleia foi ordinária ou extraordinária — isso muda quórum e prazo.",
            "Preencha o que ele pedir; o que faltar vira lacuna vermelha, não invenção.",
            "Confira o semáforo antes de exportar.",
            "Exporte em DOCX para editar, ou em PDF para arquivar.",
          ]}
        />
        <p>
          O DOCX sai formatado em A4, margens 3-2-3-2, Times 12, entrelinha 1,5 — o
          padrão que os cartórios de registro civil de pessoas jurídicas costumam
          aceitar sem devolver.
        </p>
      </Secao>

      <Secao id="protocolos" titulo="Levar ao cartório">
        <p>
          Em <strong>Protocolos</strong> você registra a entrada do documento no RCPJ e
          acompanha o que acontece depois. Se o cartório devolver com exigência, você
          lança a exigência no protocolo e ela fica ali, aberta, até ser cumprida.
        </p>
        <p>
          Enquanto houver exigência em aberto, o protocolo não avança — por desenho.
          Para cumprir uma, abra o protocolo, encontre a exigência na lista e use{" "}
          <strong>Cumprir</strong>, descrevendo o que foi feito. O histórico fica
          registrado: daqui a dois anos ainda dá para saber o que o cartório pediu e o
          que foi respondido.
        </p>
      </Secao>

      <Secao id="prazos" titulo="Prazos e pendências">
        <p>
          <strong>Prazos</strong> mostra o que vence: mandato de diretoria, prestação de
          contas, renovação de certificado. O sistema avisa com antecedência e continua
          avisando até você resolver ou remarcar.
        </p>
        <p>
          <strong>Pendências</strong> é a lista do que o sistema encontrou e não pode
          resolver sozinho — porque depende de um dado que ninguém informou, de uma
          conferência em fonte oficial, ou de uma decisão que é de quem responde
          tecnicamente pelo ato.
        </p>
        <p>
          As duas listas são atualizadas por uma varredura automática. Se remarcar um
          prazo, os alertas já disparados são zerados: eles pertenciam à data antiga.
        </p>
      </Secao>

      <Secao id="fontes" titulo="Central de Fontes">
        <p>
          A base legal do sistema é <strong>versionada</strong>. Cada norma tem uma
          versão registrada, e o sistema vigia as fontes oficiais em busca de alterações.
        </p>
        <p>
          Quando uma norma muda, ele não atualiza sozinho: abre uma pendência, mostra o
          que mudou e lista <strong>quais entidades e quais atos se apoiavam naquele
          dispositivo</strong>. A decisão de acolher a mudança é de um profissional
          habilitado — o sistema traz o fato, não a conclusão.
        </p>
      </Secao>

      <Secao id="conta" titulo="Senha e segundo fator">
        <p>
          Em <strong>Minha conta</strong> você troca a senha e ativa o segundo fator
          (MFA). Ative: é a diferença entre uma senha vazada custar um susto ou custar
          o acervo inteiro.
        </p>
        <p>
          Ao ativar, o sistema mostra um código para o aplicativo autenticador e{" "}
          <strong>oito códigos de recuperação</strong>. Guarde-os fora do celular —
          eles são a única entrada se o aparelho se perder. Cada um serve uma vez só.
        </p>
        <p>
          Cinco senhas erradas em quinze minutos travam a conta. Se isso acontecer, não
          é defeito: espere os quinze minutos.
        </p>
      </Secao>

      <Secao id="limites" titulo="O que o sistema não faz">
        <p>
          Ele confere, aponta e redige. <strong>Ele não decide, e não assina.</strong>
        </p>
        <ul className="ml-4 list-disc space-y-1.5">
          <li>
            Não substitui a análise de profissional habilitado. A automação prepara e
            valida; a responsabilidade técnica continua sendo de quem assina.
          </li>
          <li>
            Não conhece a exigência particular de todo cartório do país. O RCPJ
            cadastrado é ponto de partida — confirme antes do primeiro protocolo numa
            comarca nova.
          </li>
          <li>
            Não inventa dado que falta, e não completa o que o estatuto não diz.
          </li>
          <li>
            Não protocola sozinho, não paga taxa e não fala com o cartório por você.
          </li>
        </ul>
      </Secao>

      <div className="mt-10 rounded-lg border border-[var(--color-marca-contorno)] bg-[var(--color-marca-clara)] px-5 py-4">
        <p className="text-[0.875rem] leading-relaxed text-[var(--color-tinta-2)]">
          <strong>Travou em alguma coisa?</strong> Passe primeiro pela{" "}
          <Link href="/pendencias" className="text-[var(--color-marca)] underline underline-offset-2">
            Central de pendências
          </Link>
          . Boa parte do que parece defeito é o sistema esperando um dado que ninguém
          informou — e ele diz qual é.
        </p>
      </div>
    </div>
  );
}

function Secao({
  id,
  titulo,
  children,
}: {
  id: string;
  titulo: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="mb-9 scroll-mt-6">
      <h2 className="mb-2.5 text-[1rem] font-semibold tracking-tight">{titulo}</h2>
      <div className="space-y-3 text-[0.875rem] leading-relaxed text-[var(--color-tinta-2)]">
        {children}
      </div>
    </section>
  );
}

function Passos({ itens }: { itens: string[] }) {
  return (
    <ol className="ml-4 list-decimal space-y-1.5 marker:text-[var(--color-tinta-3)]">
      {itens.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ol>
  );
}

function ItemFarol({
  cor,
  titulo,
  children,
}: {
  cor: string;
  titulo: string;
  children: React.ReactNode;
}) {
  return (
    <li className="flex gap-3">
      <span
        aria-hidden
        className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full"
        style={{ backgroundColor: cor }}
      />
      <span>
        <strong className="text-[var(--color-tinta)]">{titulo}</strong> — {children}
      </span>
    </li>
  );
}
