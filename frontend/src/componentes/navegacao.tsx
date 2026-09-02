"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Marca } from "@/componentes/marca";

/** Menu principal (§50). Os itens ainda não construídos ficam visíveis mas
 *  desabilitados: esconder o roteiro do produto confunde mais do que ajuda. */
/** `absoluto` marca o item que não pertence a uma entidade: a base normativa é
 *  compartilhada por todas elas. */
const SECOES: {
  titulo: string;
  itens: { rotulo: string; href: string; pronto: boolean; absoluto?: boolean }[];
}[] = [
  {
    titulo: "Visão geral",
    itens: [
      { rotulo: "Painel", href: "", pronto: true },
      { rotulo: "Pendências", href: "/pendencias", pronto: true, absoluto: true },
      { rotulo: "Prazos", href: "/prazos", pronto: true },
    ],
  },
  {
    titulo: "Jurídico",
    itens: [
      { rotulo: "Estatuto", href: "/estatuto", pronto: true },
      { rotulo: "Atos", href: "/atos", pronto: true },
      { rotulo: "Diretoria", href: "/diretoria", pronto: true },
      { rotulo: "Associados", href: "/associados", pronto: true },
    ],
  },
  {
    titulo: "Documentos",
    itens: [
      { rotulo: "Acervo", href: "/documentos", pronto: true },
      { rotulo: "Protocolos", href: "/protocolos", pronto: true },
      { rotulo: "Modelos", href: "/modelos", pronto: false },
    ],
  },
  {
    titulo: "Conformidade",
    itens: [
      { rotulo: "Governança", href: "/governanca", pronto: false },
      { rotulo: "Central de Fontes", href: "/fontes", pronto: true, absoluto: true },
      { rotulo: "IA jurídica", href: "/ia", pronto: false },
    ],
  },
];

export function MenuLateral({
  entidades,
  usuario,
}: {
  entidades: { id: string; razao_social: string }[];
  usuario: { nome: string; email: string; registro_profissional: string | null };
}) {
  const caminho = usePathname();
  const [aberto, definirAberto] = useState(false);
  const entidadeId = caminho.match(/^\/entidades\/([0-9a-f-]{36})/)?.[1] ?? null;
  // Fora de uma entidade — na conta, nas pendências, na Central de Fontes —
  // os atalhos apontam para a primeira entidade em vez de aparecerem como
  // "em breve". Chamar de inacabado o que está pronto é pior do que esconder.
  const entidadeAtiva = entidadeId ?? entidades[0]?.id ?? null;
  const base = entidadeAtiva ? `/entidades/${entidadeAtiva}` : "";

  return (
    <>
      <button
        type="button"
        onClick={() => definirAberto((v) => !v)}
        aria-expanded={aberto}
        className="fixed left-4 top-3.5 z-50 rounded-md border bg-[var(--color-superficie)] px-2.5 py-1.5 text-[0.75rem] font-semibold shadow-[var(--shadow-cartao)] lg:hidden"
      >
        {aberto ? "Fechar" : "Menu"}
      </button>

      <nav
        aria-label="Navegação principal"
        className={`fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col border-r bg-[var(--color-superficie)] transition-transform lg:static lg:translate-x-0 ${
          aberto ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="border-b px-5 py-4 pl-16 lg:pl-5">
          <Link href="/">
            <Marca />
          </Link>
        </div>

        {/* Sem nenhuma entidade cadastrada não há o que selecionar — mas é
            justamente aí que o atalho para cadastrar mais importa. */}
        {entidades.length > 0 ? (
          <SeletorEntidade entidades={entidades} atual={entidadeAtiva} caminho={caminho} />
        ) : (
          <div className="border-b px-3 py-3">
            <p className="mb-2 text-[0.75rem] text-[var(--color-tinta-3)]">
              Nenhuma entidade cadastrada.
            </p>
            <Link
              href="/entidades/nova"
              onClick={() => definirAberto(false)}
              className="text-[0.75rem] font-medium text-[var(--color-marca)] underline-offset-2 hover:underline"
            >
              + Cadastrar entidade
            </Link>
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-3 py-4">
          {SECOES.map((secao) => (
            <div key={secao.titulo} className="mb-5">
              <h3 className="px-2.5 pb-1.5 text-[0.6875rem] font-semibold uppercase tracking-wider text-[var(--color-tinta-3)]">
                {secao.titulo}
              </h3>
              <ul className="space-y-0.5">
                {secao.itens.map((item) => {
                  const destino = item.absoluto ? item.href : `${base}${item.href}`;
                  const ativo = caminho === destino;
                  if (!item.pronto || (!entidadeAtiva && !item.absoluto)) {
                    return (
                      <li key={item.rotulo}>
                        <span
                          className="flex cursor-not-allowed items-center justify-between rounded-md px-2.5 py-1.5 text-[0.8125rem] text-[var(--color-tinta-3)] opacity-60"
                          title="Ainda em construção"
                        >
                          {item.rotulo}
                          <span className="text-[0.625rem] uppercase tracking-wide">em breve</span>
                        </span>
                      </li>
                    );
                  }
                  return (
                    <li key={item.rotulo}>
                      <Link
                        href={destino}
                        onClick={() => definirAberto(false)}
                        aria-current={ativo ? "page" : undefined}
                        className={`block rounded-md px-2.5 py-1.5 text-[0.8125rem] transition-colors ${
                          ativo
                            ? "bg-[var(--color-marca-clara)] font-semibold text-[var(--color-marca)]"
                            : "text-[var(--color-tinta-2)] hover:bg-[var(--color-superficie-2)]"
                        }`}
                      >
                        {item.rotulo}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        <Rodape usuario={usuario} />
      </nav>

      {aberto && (
        <button
          type="button"
          aria-label="Fechar menu"
          onClick={() => definirAberto(false)}
          className="fixed inset-0 z-30 bg-black/30 lg:hidden"
        />
      )}
    </>
  );
}

function SeletorEntidade({
  entidades,
  atual,
  caminho,
}: {
  entidades: { id: string; razao_social: string }[];
  atual: string | null;
  caminho: string;
}) {
  const router = useRouter();
  return (
    <div className="border-b px-3 py-3">
      <label htmlFor="seletor-entidade" className="sr-only">
        Entidade
      </label>
      <select
        id="seletor-entidade"
        value={atual ?? ""}
        onChange={(e) => {
          // Mantém a mesma seção ao trocar de entidade: quem estava vendo o
          // estatuto quer ver o estatuto da outra, não voltar ao painel.
          const secao = atual ? caminho.replace(`/entidades/${atual}`, "") : "";
          router.push(`/entidades/${e.target.value}${secao}`);
        }}
        className="w-full rounded-md border bg-[var(--color-superficie-2)] px-2.5 py-2 text-[0.8125rem] font-medium text-[var(--color-tinta)]"
      >
        {entidades.map((e) => (
          <option key={e.id} value={e.id}>
            {e.razao_social}
          </option>
        ))}
      </select>
      <Link
        href="/entidades/nova"
        className="mt-2 inline-block text-[0.75rem] font-medium text-[var(--color-marca)] underline-offset-2 hover:underline"
      >
        + Cadastrar entidade
      </Link>
    </div>
  );
}

function Rodape({
  usuario,
}: {
  usuario: { nome: string; email: string; registro_profissional: string | null };
}) {
  const router = useRouter();
  return (
    <div className="border-t px-4 py-3.5">
      <p className="truncate text-[0.8125rem] font-medium text-[var(--color-tinta)]">
        {usuario.nome}
      </p>
      <p className="truncate text-[0.75rem] text-[var(--color-tinta-3)]">
        {usuario.registro_profissional ?? usuario.email}
      </p>
      <Link
        href="/conta"
        className="mt-2 mr-3 inline-block text-[0.75rem] font-medium text-[var(--color-tinta-2)] underline-offset-2 hover:underline"
      >
        Minha conta
      </Link>
      <Link
        href="/ajuda"
        className="mt-2 mr-3 inline-block text-[0.75rem] font-medium text-[var(--color-tinta-2)] underline-offset-2 hover:underline"
      >
        Ajuda
      </Link>
      <button
        type="button"
        onClick={async () => {
          await fetch("/api/sessao", { method: "DELETE" });
          router.replace("/entrar");
          router.refresh();
        }}
        className="mt-2 text-[0.75rem] font-medium text-[var(--color-tinta-2)] underline-offset-2 hover:underline"
      >
        Sair
      </button>
    </div>
  );
}
