"use client";

/** Acervo documental: status, assinaturas e download (§19, §20, §28).
 *
 *  O estado de um documento jurídico não é enfeite — é o que diz se ele pode
 *  ir ao cartório. Por isso a trilha aparece inteira, com a etapa atual
 *  marcada, e não como um seletor solto de status.
 */
import Link from "next/link";
import { useState, useTransition } from "react";

import { Aviso, Botao, Campo, Etiqueta, Vazio } from "@/componentes/base";
import {
  adicionarSignatario,
  mudarStatusDocumento,
  registrarAssinatura,
} from "@/lib/acoes";
import { dataBr } from "@/lib/formato";
import type { Assinatura, DocumentoDetalhado, DocumentoResumo } from "@/lib/tipos";

/** §28 — a ordem em que um documento amadurece. */
export const TRILHA = [
  "RASCUNHO", "GERADO", "REVISADO", "APROVADO",
  "ASSINADO", "PROTOCOLADO", "REGISTRADO", "ARQUIVADO",
] as const;

const ROTULO: Record<string, string> = {
  RASCUNHO: "Rascunho",
  GERADO: "Gerado",
  REVISADO: "Revisado",
  APROVADO: "Aprovado",
  ASSINADO: "Assinado",
  PROTOCOLADO: "Protocolado",
  REGISTRADO: "Registrado",
  ARQUIVADO: "Arquivado",
  CANCELADO: "Cancelado",
};

export function EtiquetaStatus({ status }: { status: string }) {
  const registrado = status === "REGISTRADO";
  return (
    <Etiqueta tom={registrado ? "marca" : "neutro"}>{ROTULO[status] ?? status}</Etiqueta>
  );
}

export function ListaDocumentos({
  documentos,
  base,
}: {
  documentos: DocumentoResumo[];
  base: string;
}) {
  if (documentos.length === 0) {
    return <Vazio>Nenhum documento neste filtro.</Vazio>;
  }
  return (
    <ul className="divide-y">
      {documentos.map((d) => (
        <li key={d.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-5 py-3">
          <Link
            href={`${base}/documentos/${d.id}`}
            className="min-w-0 flex-1 text-[0.875rem] font-medium hover:underline"
          >
            {d.titulo}
          </Link>
          <span className="text-[0.75rem] text-[var(--color-tinta-3)]">
            v{d.versao_atual} · {dataBr(d.data)}
          </span>
          {d.assinaturas_pendentes > 0 && (
            <span
              className="text-[0.75rem] font-medium"
              style={{ color: "var(--color-pendencia)" }}
            >
              {d.assinaturas_pendentes} assinatura(s) pendente(s)
            </span>
          )}
          <EtiquetaStatus status={d.status} />
        </li>
      ))}
    </ul>
  );
}

export function TrilhaStatus({
  documento,
  caminho,
}: {
  documento: DocumentoDetalhado;
  caminho: string;
}) {
  const [pendente, iniciar] = useTransition();
  const [erro, definirErro] = useState<string | null>(null);
  const atual = TRILHA.indexOf(documento.status as (typeof TRILHA)[number]);

  function avancar(destino: string) {
    definirErro(null);
    iniciar(async () => {
      const r = await mudarStatusDocumento(documento.id, destino, caminho);
      if (!r.ok) definirErro(r.mensagem ?? "Não foi possível mudar o status.");
    });
  }

  const proximo = atual >= 0 && atual < TRILHA.length - 1 ? TRILHA[atual + 1] : null;

  return (
    <div>
      <ol className="flex flex-wrap items-center gap-x-1 gap-y-2">
        {TRILHA.map((etapa, i) => {
          const passou = atual >= 0 && i <= atual;
          return (
            <li key={etapa} className="flex items-center gap-1">
              <span
                aria-current={i === atual ? "step" : undefined}
                className="rounded px-1.5 py-0.5 text-[0.6875rem] font-medium"
                style={{
                  background: passou ? "var(--color-marca-clara)" : "var(--color-superficie-2)",
                  color: passou ? "var(--color-marca)" : "var(--color-tinta-3)",
                  outline: i === atual ? "1px solid var(--color-marca)" : undefined,
                }}
              >
                {ROTULO[etapa]}
              </span>
              {i < TRILHA.length - 1 && (
                <span aria-hidden className="text-[var(--color-tinta-3)]">›</span>
              )}
            </li>
          );
        })}
      </ol>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {proximo && (
          <Botao variante="secundario" disabled={pendente} onClick={() => avancar(proximo)}>
            Marcar como {ROTULO[proximo].toLowerCase()}
          </Botao>
        )}
        {documento.status !== "CANCELADO" && (
          <Botao variante="silencioso" disabled={pendente} onClick={() => avancar("CANCELADO")}>
            Cancelar documento
          </Botao>
        )}
      </div>
      {erro && (
        <div className="mt-2">
          <Aviso tom="erro">{erro}</Aviso>
        </div>
      )}
      <p className="mt-2 text-[0.75rem] leading-relaxed text-[var(--color-tinta-3)]">
        O documento não retrocede de etapa: para corrigir algo já aprovado, gere uma
        nova versão. O histórico do que foi assinado continua intacto (§20).
      </p>
    </div>
  );
}

export function PainelAssinaturas({
  documento,
  caminho,
}: {
  documento: DocumentoDetalhado;
  caminho: string;
}) {
  const [pendente, iniciar] = useTransition();
  const [erro, definirErro] = useState<string | null>(null);
  const [nome, definirNome] = useState("");
  const [papel, definirPapel] = useState("");
  const [firma, definirFirma] = useState(false);

  function incluir(evento: React.FormEvent) {
    evento.preventDefault();
    if (!nome.trim()) return;
    definirErro(null);
    iniciar(async () => {
      const r = await adicionarSignatario(
        documento.id,
        {
          nome_signatario: nome.trim(),
          papel: papel.trim() || undefined,
          exige_reconhecimento_firma: firma,
        },
        caminho,
      );
      if (r.ok) {
        definirNome("");
        definirPapel("");
        definirFirma(false);
      } else {
        definirErro(r.mensagem ?? "Falha ao incluir.");
      }
    });
  }

  return (
    <div className="space-y-4">
      {documento.assinaturas.length === 0 ? (
        <Vazio>Nenhum signatário cadastrado.</Vazio>
      ) : (
        <ul className="space-y-2">
          {documento.assinaturas.map((a) => (
            <ItemAssinatura key={a.id} assinatura={a} caminho={caminho} />
          ))}
        </ul>
      )}

      <form onSubmit={incluir} className="space-y-3 border-t pt-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <Campo
            rotulo="Signatário"
            name="signatario"
            value={nome}
            onChange={(e) => definirNome(e.target.value)}
            placeholder="Nome completo"
          />
          <Campo
            rotulo="Papel"
            name="papel"
            value={papel}
            onChange={(e) => definirPapel(e.target.value)}
            placeholder="Presidente, Secretário, Testemunha…"
          />
        </div>
        <label className="flex items-center gap-2 text-[0.8125rem] text-[var(--color-tinta-2)]">
          <input
            type="checkbox"
            checked={firma}
            onChange={(e) => definirFirma(e.target.checked)}
          />
          Exige reconhecimento de firma
        </label>
        <Botao tipo="submit" variante="secundario" disabled={pendente || !nome.trim()}>
          Incluir signatário
        </Botao>
      </form>
      {erro && <Aviso tom="erro">{erro}</Aviso>}
    </div>
  );
}

function ItemAssinatura({
  assinatura,
  caminho,
}: {
  assinatura: Assinatura;
  caminho: string;
}) {
  const [pendente, iniciar] = useTransition();
  const [erro, definirErro] = useState<string | null>(null);
  const assinado = assinatura.status === "ASSINADO";

  return (
    <li className="rounded-md border px-3.5 py-3">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="text-[0.875rem] font-medium">{assinatura.signatario}</span>
        {assinatura.papel && <Etiqueta>{assinatura.papel}</Etiqueta>}
        {assinatura.reconhecimento_firma && <Etiqueta>firma reconhecida</Etiqueta>}
        <span
          className="ml-auto text-[0.75rem] font-medium"
          style={{ color: assinado ? "var(--color-apto)" : "var(--color-pendencia)" }}
        >
          {assinado ? `Assinado em ${dataBr(assinatura.data)}` : "Pendente"}
        </span>
      </div>
      {!assinado && (
        <div className="mt-2">
          <Botao
            variante="secundario"
            disabled={pendente}
            onClick={() =>
              iniciar(async () => {
                const r = await registrarAssinatura(assinatura.id, caminho);
                if (!r.ok) definirErro(r.mensagem ?? "Falha ao registrar.");
              })
            }
          >
            Registrar assinatura
          </Botao>
          <p className="mt-1.5 text-[0.6875rem] leading-snug text-[var(--color-tinta-3)]">
            Registra que a assinatura aconteceu. O sistema não assina por ninguém
            nem fabrica evidência: ela vem de fora (§46).
          </p>
        </div>
      )}
      {erro && (
        <div className="mt-2">
          <Aviso tom="erro">{erro}</Aviso>
        </div>
      )}
    </li>
  );
}

export function BotoesDownload({ documentoId }: { documentoId: string }) {
  return (
    <div className="flex flex-wrap gap-2">
      {(["docx", "pdf"] as const).map((formato) => (
        <a
          key={formato}
          href={`/api/documentos/${documentoId}/baixar?formato=${formato}`}
          className="inline-flex items-center justify-center gap-2 rounded-md border border-[var(--color-borda-forte)] bg-[var(--color-superficie)] px-3.5 py-2 text-[0.8125rem] font-semibold text-[var(--color-tinta)] transition-colors hover:bg-[var(--color-superficie-2)]"
        >
          Baixar {formato.toUpperCase()}
        </a>
      ))}
    </div>
  );
}
