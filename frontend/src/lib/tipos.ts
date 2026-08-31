/** Contratos da API do TERCEIRO360, espelhando o backend. */

export type Semaforo = "APTO" | "PENDENCIA" | "BLOQUEADO";
export type Prioridade = "URGENTE" | "ALTA" | "MEDIA" | "BAIXA";

export interface Fundamento {
  origem: string;
  referencia: string;
  dispositivo: string | null;
  trecho: string | null;
  versao_norma: string | null;
  /** §46 — se a redação já foi conferida por um responsável habilitado. */
  curado: boolean | null;
  url: string | null;
}

export interface Achado {
  codigo: string;
  severidade: Semaforo;
  icone: string;
  titulo: string;
  mensagem: string;
  campo: string | null;
  sugestao: string | null;
  fundamentos: Fundamento[];
  dados: Record<string, unknown>;
}

export interface ResultadoValidacao {
  semaforo: Semaforo;
  icone: string;
  pode_gerar_documentos: boolean;
  total_achados: number;
  bloqueios: number;
  pendencias: number;
  avaliado_em: string;
  achados: Achado[];
  campos_faltantes?: string[];
  checklist?: Checklist;
}

export interface ItemChecklist {
  codigo: string;
  descricao: string;
  obrigatorio: boolean;
  origem: string;
  origens: string[];
  fundamento: string | null;
  status: "PENDENTE" | "OK" | "NAO_APLICAVEL";
  observacao: string | null;
}

export interface Checklist {
  tipo_evento: string;
  completo: boolean;
  total: number;
  pendentes: number;
  avisos: string[];
  itens: ItemChecklist[];
}

export interface Usuario {
  id: string;
  nome: string;
  email: string;
  cliente_id: string;
  registro_profissional: string | null;
  permissoes: string[];
}

export interface EntidadeResumo {
  id: string;
  razao_social: string;
  nome_fantasia: string | null;
  cnpj: string | null;
  tipo_entidade: string;
  municipio: string | null;
  uf: string | null;
  ativa: boolean;
}

export interface CriterioScore {
  codigo: string;
  rotulo: string;
  peso: number;
  atingido: number;
  pontos: number;
  justificativa: string;
}

export interface Score {
  pontuacao: number;
  classificacao: "Excelente" | "Regular" | "Atenção" | "Risco elevado";
  cor: string;
  data_referencia: string;
  criterios: CriterioScore[];
}

export interface Pendencia {
  codigo: string;
  severidade: Semaforo;
  icone: string;
  titulo: string;
  descricao: string;
  prioridade: Prioridade;
  referencia: string | null;
  sugestao: string | null;
}

export interface Prazo {
  descricao: string;
  tipo: string;
  data_limite: string;
  dias_restantes: number;
  prioridade: Prioridade;
  origem: string;
  fundamento: string | null;
  vencido?: boolean;
  chave?: string;
}

export interface MembroDiretoria {
  nome: string;
  cargo: string;
}

export interface Dashboard {
  entidade: {
    id: string;
    razao_social: string;
    cnpj: string | null;
    tipo: string;
    municipio: string | null;
    uf: string | null;
    situacao_cadastral: string | null;
  };
  estatuto: {
    versao: number | null;
    data: string | null;
    registro: string | null;
    parametros_confirmados: number;
    parametros_totais: number;
  };
  diretoria: {
    gestao: string | null;
    vigente: boolean;
    inicio: string | null;
    fim: string | null;
    membros: MembroDiretoria[];
    cargos_vagos: string[];
  };
  score: Score;
  pendencias: Pendencia[];
  prazos: Prazo[];
  alertas: { descricao: string; janela_dias: number; data_limite: string }[];
  atos_em_andamento: {
    id: string;
    tipo: string;
    titulo: string | null;
    status: string;
    semaforo: Semaforo | null;
    data: string | null;
  }[];
}

/* ─────────────────────────────────────────── Matriz de atos e questionário */

export interface CampoQuestionario {
  nome: string;
  pergunta: string;
  tipo: "data" | "texto" | "numero" | "opcao" | "lista" | "booleano" | "pessoas";
  obrigatorio: boolean;
  opcoes: string[];
  ajuda: string | null;
  /** Parâmetro do estatuto exibido ao lado do campo como referência (§52). */
  referencia_estatutaria: string | null;
}

export interface Questionario {
  tipo_evento: string;
  titulo: string;
  campos: CampoQuestionario[];
}

export type ExigeReforma = "SEMPRE" | "NUNCA" | "DEPENDE_DO_ESTATUTO" | "NAO_APLICAVEL";
export type EspecieAssembleia =
  | "ORDINARIA"
  | "EXTRAORDINARIA"
  | "CONFORME_ESTATUTO"
  | "NAO_ASSEMBLEAR";

export interface Ato {
  tipo: string;
  titulo: string;
  categoria: string;
  descricao: string;
  orgao_competente: string;
  especie_assembleia: EspecieAssembleia;
  exige_reforma_estatutaria: ExigeReforma;
  exige_convocacao_especifica: boolean;
  chave_quorum: string | null;
  efeito_registral: "REGISTRO" | "AVERBACAO" | "INTERNO";
  assemblear: boolean;
  documentos: string[];
  fundamentos: { fonte: string; dispositivo: string }[];
  parametros_relevantes: string[];
  nota: string | null;
  alertas: string[];
}

export interface AtoDetalhado extends Ato {
  questionario: Questionario;
  parametros: { chave: string; rotulo: string; pergunta: string; nota: string | null }[];
}

export interface Evento {
  id: string;
  tipo: string;
  titulo: string | null;
  status: string;
  semaforo: Semaforo | null;
  data_referencia: string | null;
  dados: Record<string, unknown>;
}

export interface DocumentoResumo {
  id: string;
  tipo: string;
  categoria: string;
  titulo: string;
  status: string;
  versao_atual: number;
  data: string | null;
  evento_id: string | null;
  origem: string;
  template: string | null;
  assinaturas_pendentes: number;
}

export interface ResultadoGeracao {
  semaforo: Semaforo;
  gerados: {
    documento_id: string;
    tipo: string;
    titulo: string;
    versao: number;
    lacunas: string[];
  }[];
  sem_modelo_cadastrado: string[];
  ressalvas: Achado[];
}
