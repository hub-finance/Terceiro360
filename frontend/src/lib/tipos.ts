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
