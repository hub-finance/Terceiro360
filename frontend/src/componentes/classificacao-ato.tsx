/** O que a lei e o estatuto dizem sobre este ato (§39).
 *
 *  Fica visível antes de o usuário preencher qualquer campo. A pergunta que
 *  esta caixa responde é a que trava o operador na hora de agir: "isto aqui é
 *  reforma estatutária? é ordinária ou extraordinária? que quórum vale?"
 */
import { Aviso, Etiqueta } from "@/componentes/base";
import type { Ato } from "@/lib/tipos";

const REFORMA: Record<Ato["exige_reforma_estatutaria"], { rotulo: string; tom: string }> = {
  SEMPRE: { rotulo: "É reforma estatutária", tom: "var(--color-pendencia)" },
  NUNCA: { rotulo: "Não é reforma estatutária", tom: "var(--color-tinta-2)" },
  DEPENDE_DO_ESTATUTO: { rotulo: "Depende do estatuto", tom: "var(--color-pendencia)" },
  NAO_APLICAVEL: { rotulo: "Não se aplica", tom: "var(--color-tinta-3)" },
};

const ESPECIE: Record<Ato["especie_assembleia"], string> = {
  ORDINARIA: "Assembleia ordinária",
  EXTRAORDINARIA: "Assembleia extraordinária",
  CONFORME_ESTATUTO: "Conforme o estatuto",
  NAO_ASSEMBLEAR: "Não é ato de assembleia",
};

const REGISTRAL: Record<Ato["efeito_registral"], string> = {
  REGISTRO: "Vai a registro",
  AVERBACAO: "Vai a averbação",
  INTERNO: "Não vai a registro",
};

const NOME_FONTE: Record<string, string> = {
  CC_2002: "Código Civil",
  LRP_1973: "Lei de Registros Públicos",
  CF_1988: "Constituição Federal",
  MROSC_2014: "Lei nº 13.019/2014",
  OSCIP_1999: "Lei nº 9.790/1999",
  EOAB_1994: "Estatuto da Advocacia",
  LGPD_2018: "LGPD",
};

export function ClassificacaoAto({ ato }: { ato: Ato }) {
  const reforma = REFORMA[ato.exige_reforma_estatutaria];

  return (
    <div className="space-y-4">
      <p className="text-[0.875rem] leading-relaxed text-[var(--color-tinta-2)]">
        {ato.descricao}
      </p>

      <dl className="space-y-2.5 text-[0.8125rem]">
        <Item rotulo="Natureza" valor={reforma.rotulo} tom={reforma.tom} />
        <Item rotulo="Onde se delibera" valor={ESPECIE[ato.especie_assembleia]} />
        <Item
          rotulo="Órgão competente"
          valor={ato.orgao_competente.replaceAll("_", " ").toLowerCase()}
        />
        <Item rotulo="Efeito registral" valor={REGISTRAL[ato.efeito_registral]} />
      </dl>

      {ato.exige_convocacao_especifica && (
        <Aviso tom="atencao" titulo="Convocação específica">
          A matéria precisa constar expressamente da ordem do dia, em assembleia
          especialmente convocada para esse fim. Deliberar sobre assunto ausente do
          edital é vício recorrente de anulação.
        </Aviso>
      )}

      {ato.nota && (
        <p className="text-[0.8125rem] leading-relaxed text-[var(--color-tinta-2)]">{ato.nota}</p>
      )}

      {ato.alertas.length > 0 && (
        <ul className="space-y-1.5">
          {ato.alertas.map((a) => (
            <li key={a} className="flex gap-2 text-[0.8125rem] leading-snug text-[var(--color-tinta-2)]">
              <span className="mt-[0.4rem] h-1 w-1 shrink-0 rounded-full bg-[var(--color-pendencia)]" />
              {a}
            </li>
          ))}
        </ul>
      )}

      {ato.fundamentos.length > 0 && (
        <div>
          <h3 className="mb-1.5 text-[0.6875rem] font-semibold uppercase tracking-wider text-[var(--color-tinta-3)]">
            Base normativa
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {ato.fundamentos.map((f) => (
              <Etiqueta key={`${f.fonte}${f.dispositivo}`}>
                {NOME_FONTE[f.fonte] ?? f.fonte}, {f.dispositivo}
              </Etiqueta>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Item({ rotulo, valor, tom }: { rotulo: string; valor: string; tom?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-[var(--color-tinta-3)]">{rotulo}</dt>
      <dd className="text-right font-medium first-letter:uppercase" style={{ color: tom }}>
        {valor}
      </dd>
    </div>
  );
}
