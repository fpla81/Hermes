export interface Fundamento {
  id: string;
  tema: string;
  titulo: string;
  corpo_md: string;
  tags: string[] | null;
  resumo: string | null;
  source_case_id: string | null;
  usage_count: number;
  created_at: string;
}

export interface LearnResult {
  learned: number;
  fundamentos: Array<{
    id: string;
    tema: string;
    titulo: string;
    resumo: string | null;
  }>;
}

export interface FundamentoUpdate {
  tema?: string;
  titulo?: string;
  corpo_md?: string;
  tags?: string[];
  resumo?: string;
}
