import { Cartao, Etiqueta } from "@/componentes/base";
import { SegundoFator, TrocaDeSenha } from "@/componentes/conta";
import { chamarApi } from "@/lib/api";
import { dataBr } from "@/lib/formato";
import type { Usuario } from "@/lib/tipos";

export const metadata = { title: "Minha conta" };

interface SituacaoMfa {
  habilitado: boolean;
  confirmado_em: string | null;
  codigos_recuperacao_restantes: number;
}

export default async function PaginaConta() {
  const [usuario, mfa] = await Promise.all([
    chamarApi<Usuario>("/auth/eu"),
    chamarApi<SituacaoMfa>("/auth/mfa"),
  ]);

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">Minha conta</h1>
        <p className="mt-1 text-[0.875rem] leading-relaxed text-[var(--color-tinta-3)]">
          Este sistema guarda CPF, endereço e documento de dirigentes e associados
          de terceiros. Proteger o acesso a ele não é zelo com a sua conta — é
          obrigação com essas pessoas.
        </p>
      </header>

      <div className="space-y-4">
        <Cartao titulo="Identificação">
          <dl className="grid gap-3 text-[0.875rem] sm:grid-cols-2">
            <div>
              <dt className="text-[0.75rem] uppercase tracking-wide text-[var(--color-tinta-3)]">
                Nome
              </dt>
              <dd className="mt-0.5">{usuario.nome}</dd>
            </div>
            <div>
              <dt className="text-[0.75rem] uppercase tracking-wide text-[var(--color-tinta-3)]">
                E-mail
              </dt>
              <dd className="mt-0.5">{usuario.email}</dd>
            </div>
            <div>
              <dt className="text-[0.75rem] uppercase tracking-wide text-[var(--color-tinta-3)]">
                Registro profissional
              </dt>
              <dd className="mt-0.5">
                {usuario.registro_profissional ?? (
                  <span className="text-[var(--color-tinta-3)]">
                    não cadastrado — sem ele não é possível publicar norma na Central
                    de Fontes
                  </span>
                )}
              </dd>
            </div>
            <div>
              <dt className="text-[0.75rem] uppercase tracking-wide text-[var(--color-tinta-3)]">
                Permissões
              </dt>
              <dd className="mt-1 flex flex-wrap gap-1">
                {usuario.permissoes.map((p) => (
                  <Etiqueta key={p}>{p}</Etiqueta>
                ))}
              </dd>
            </div>
          </dl>
        </Cartao>

        <Cartao
          titulo="Verificação em duas etapas"
          descricao="A proteção que impede uma senha vazada de virar acesso"
          acao={
            mfa.habilitado ? (
              <span
                className="text-[0.8125rem] font-medium"
                style={{ color: "var(--color-apto)" }}
              >
                ativa desde {dataBr(mfa.confirmado_em)}
              </span>
            ) : (
              <span
                className="text-[0.8125rem] font-medium"
                style={{ color: "var(--color-pendencia)" }}
              >
                desativada
              </span>
            )
          }
        >
          <SegundoFator
            habilitado={mfa.habilitado}
            codigosRestantes={mfa.codigos_recuperacao_restantes}
          />
        </Cartao>

        <Cartao titulo="Senha" descricao="Comprimento protege mais do que símbolo no meio">
          <TrocaDeSenha email={usuario.email} />
        </Cartao>
      </div>
    </div>
  );
}
