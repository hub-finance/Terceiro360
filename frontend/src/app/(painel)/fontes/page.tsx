import Link from "next/link";

import { Aviso, Cartao, Etiqueta, Metrica, SeloSemaforo } from "@/componentes/base";
import { ListaAtualizacoes, ListaImpactos } from "@/componentes/curadoria";
import { ListaVigilias } from "@/componentes/vigilias";
import { chamarApi } from "@/lib/api";
import { dataBr } from "@/lib/formato";
import type {
  AtualizacaoNormativa,
  FonteResumo,
  ImpactoNormativo,
  Usuario,
  Vigilia,
  VinculoNormativo,
} from "@/lib/tipos";

export const metadata = { title: "Central de Fontes" };

export default async function PaginaFontes() {
  const [usuario, fontes, vigilias, atualizacoes, impactos, vinculos] = await Promise.all([
    chamarApi<Usuario>("/auth/eu"),
    chamarApi<FonteResumo[]>("/normativo/fontes"),
    chamarApi<Vigilia[]>("/normativo/monitoramentos/vencidos"),
    chamarApi<AtualizacaoNormativa[]>("/normativo/atualizacoes"),
    chamarApi<ImpactoNormativo[]>("/normativo/impactos"),
    chamarApi<VinculoNormativo[]>("/normativo/vinculos"),
  ]);

  const podeCurar = Boolean(usuario.registro_profissional);
  const naoCuradas = fontes.filter((f) => !f.curada);
  const pendentes = atualizacoes.filter(
    (a) => a.situacao === "DETECTADA" || a.situacao === "EM_ANALISE",
  );

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">Central de Fontes Jurídicas</h1>
        <p className="mt-1 max-w-3xl text-[0.875rem] leading-relaxed text-[var(--color-tinta-3)]">
          A base legal do sistema é dado versionado, não código. Cada norma guarda a
          redação que valia em cada data, cada conclusão do motor cita a versão que
          usou, e nenhuma redação entra em vigor sem conferência de um responsável
          habilitado.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Cartao>
          <Metrica rotulo="Normas" valor={fontes.length} detalhe="na base de trabalho" />
        </Cartao>
        <Cartao>
          <Metrica
            rotulo="Sem curadoria"
            valor={naoCuradas.length}
            tom={naoCuradas.length ? "var(--color-pendencia)" : undefined}
            detalhe="redações não conferidas"
          />
        </Cartao>
        <Cartao>
          <Metrica
            rotulo="Vigílias vencidas"
            valor={vigilias.length}
            tom={vigilias.length ? "var(--color-pendencia)" : undefined}
            detalhe="fontes a reconferir"
          />
        </Cartao>
        <Cartao>
          <Metrica
            rotulo="Impactos abertos"
            valor={impactos.length}
            tom={impactos.length ? "var(--color-bloqueado)" : undefined}
            detalhe="regras a revisar"
          />
        </Cartao>
      </div>

      <div className="mt-4 space-y-4">
        {naoCuradas.length > 0 && (
          <Aviso tom="atencao" titulo="Base de trabalho pendente de conferência">
            {naoCuradas.length} de {fontes.length} redações ainda não foram conferidas por
            um responsável habilitado. O motor cita essas normas assinalando
            &ldquo;não conferida&rdquo; em cada achado, para que ninguém confunda base de
            partida com base auditada.
          </Aviso>
        )}

        {impactos.length > 0 && (
          <Cartao
            titulo="Impactos de mudança normativa"
            descricao="O que se apoiava em redação que mudou"
          >
            <ListaImpactos impactos={impactos} />
          </Cartao>
        )}

        <Cartao
          titulo="Mudanças normativas"
          descricao={
            pendentes.length > 0
              ? `${pendentes.length} aguardando triagem`
              : "Detecção, triagem e publicação"
          }
        >
          <ListaAtualizacoes atualizacoes={atualizacoes} podeCurar={podeCurar} />
        </Cartao>

        <Cartao
          titulo="Vigílias"
          descricao="Fontes fora do prazo de reconferência"
          acao={<Etiqueta>{vigilias.length} de fora do prazo</Etiqueta>}
        >
          <ListaVigilias vigilias={vigilias} />
        </Cartao>

        <Cartao titulo="Normas" descricao="Cada uma com sua redação vigente">
          <ul className="divide-y">
            {fontes.map((f) => (
              <li key={f.chave}>
                <Link
                  href={`/fontes/${f.chave}`}
                  className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1 py-3 first:pt-0 hover:text-[var(--color-marca)]"
                >
                  <span className="min-w-0">
                    <span className="text-[0.875rem] font-medium">
                      {f.apelido ?? f.identificacao}
                    </span>
                    <span className="mt-0.5 block text-[0.75rem] text-[var(--color-tinta-3)]">
                      {f.identificacao}
                      {f.vigente_desde && ` · vigente desde ${dataBr(f.vigente_desde)}`}
                      {f.total_versoes > 1 && ` · ${f.total_versoes} versões`}
                    </span>
                  </span>
                  <SeloSemaforo
                    estado={f.curada ? "APTO" : "PENDENCIA"}
                    texto={f.curada ? "Conferida" : "Não conferida"}
                  />
                </Link>
              </li>
            ))}
          </ul>
        </Cartao>

        <Cartao
          titulo="Vínculos normativos"
          descricao="O mapa que responde: se esta lei mudar, o que para de valer?"
        >
          <ul className="divide-y text-[0.8125rem]">
            {vinculos.map((v) => (
              <li key={v.id} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 py-2 first:pt-0 last:pb-0">
                <span className="font-medium">{v.alvo_ref}</span>
                <span className="text-[var(--color-tinta-3)]">
                  {v.fonte_chave}
                  {v.dispositivo && `, ${v.dispositivo}`}
                </span>
              </li>
            ))}
          </ul>
        </Cartao>
      </div>
    </div>
  );
}
