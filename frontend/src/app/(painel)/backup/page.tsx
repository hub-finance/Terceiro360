import { Aviso, Cartao } from "@/componentes/base";
import { ErroApi, chamarApi } from "@/lib/api";

export const metadata = { title: "Cópia de segurança" };

interface Exportacao {
  quando: string;
  ip: string | null;
  por: string;
}

function dataHora(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    timeZone: "America/Sao_Paulo",
    dateStyle: "short",
    timeStyle: "short",
  });
}

export default async function PaginaBackup() {
  let historico: Exportacao[] = [];
  let semPermissao: string | null = null;
  try {
    historico = await chamarApi<Exportacao[]>("/backup/historico");
  } catch (erro) {
    if (erro instanceof ErroApi && erro.status === 403) semPermissao = erro.message;
    else throw erro;
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">Cópia de segurança</h1>
        <p className="mt-1 text-[0.875rem] leading-relaxed text-[var(--color-tinta-3)]">
          Os dados já ficam guardados no banco do sistema, em São Paulo. Esta é a
          outra cópia: um arquivo que fica com você, fora do sistema, e que vale
          mesmo se a conta ou o provedor deixarem de existir.
        </p>
      </header>

      {semPermissao ? (
        <Aviso tom="atencao" titulo="Somente administradores do escritório">
          {semPermissao}
        </Aviso>
      ) : (
        <>
          <Cartao>
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-[0.9375rem] font-semibold">Baixar cópia agora</p>
                <p className="mt-0.5 text-[0.8125rem] text-[var(--color-tinta-3)]">
                  Um arquivo ZIP com todos os dados do escritório.
                </p>
              </div>
              {/* Link comum, não botão com script: é o que funciona igual em
                  qualquer navegador, inclusive no tablet, e o próprio
                  navegador cuida do download. */}
              <a
                href="/api/backup"
                download
                className="inline-flex items-center rounded-md bg-[var(--color-marca)] px-4 py-2 text-[0.8125rem] font-semibold text-white hover:bg-[var(--color-marca-forte)]"
              >
                Baixar cópia
              </a>
            </div>
          </Cartao>

          <div className="mt-5">
            <Aviso tom="atencao" titulo="O arquivo contém dados pessoais sem cifra">
              CPF, RG e endereços de dirigentes e associados ficam legíveis no
              arquivo. Isso é de propósito: a cópia precisa servir mesmo se a chave
              de cifra do sistema se perder. Guarde-a como guardaria o próprio
              cadastro: em local com senha, nunca em grupo de mensagens ou e-mail
              aberto. Cada cópia baixada fica registrada abaixo.
            </Aviso>
          </div>
        </>
      )}

      <section className="mt-8 grid gap-4 sm:grid-cols-2">
        <Cartao titulo="O que vai na cópia">
          <ul className="ml-4 list-disc space-y-1 text-[0.8125rem] leading-relaxed text-[var(--color-tinta-2)]">
            <li>Entidades, estatutos e as regras extraídas deles</li>
            <li>Diretorias, mandatos e associados</li>
            <li>Atos e todos os documentos gerados, em todas as versões</li>
            <li>Protocolos, prazos e pendências</li>
            <li>Usuários do escritório e o histórico de alterações</li>
          </ul>
        </Cartao>
        <Cartao titulo="O que não vai">
          <ul className="ml-4 list-disc space-y-1 text-[0.8125rem] leading-relaxed text-[var(--color-tinta-2)]">
            <li>Senhas e códigos do segundo fator, por segurança</li>
            <li>A base de leis, que é do sistema e igual para todos</li>
            <li>Dados de qualquer outro escritório</li>
          </ul>
        </Cartao>
      </section>

      <p className="mt-4 text-[0.8125rem] leading-relaxed text-[var(--color-tinta-3)]">
        Recomendação: baixe uma cópia por semana, e sempre antes de uma alteração
        grande. Dentro do ZIP, o arquivo LEIA-ME explica cada parte, e o
        manifesto traz uma impressão digital de cada arquivo, que prova que nada
        foi alterado depois.
      </p>

      {!semPermissao && (
        <Cartao titulo="Últimas cópias baixadas" className="mt-6">
          {historico.length === 0 ? (
            <p className="text-[0.8125rem] text-[var(--color-tinta-3)]">
              Nenhuma cópia baixada ainda.
            </p>
          ) : (
            <ul className="divide-y">
              {historico.map((h) => (
                <li
                  key={h.quando}
                  className="flex flex-wrap justify-between gap-2 py-2 text-[0.8125rem]"
                >
                  <span className="font-medium text-[var(--color-tinta)]">{h.por}</span>
                  <span className="text-[var(--color-tinta-3)]">
                    {dataHora(h.quando)}
                    {h.ip ? ` · ${h.ip}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Cartao>
      )}
    </div>
  );
}
