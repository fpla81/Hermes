export interface Fundamento {
  id: string;
  tema: string;
  titulo: string;
  corpo_md: string;
  tags: string[] | null;
  resumo: string | null;
  conclusao_provimento: string | null;
  conclusao_nao_conhecimento: string | null;
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

export interface FundamentoExtractedItem {
  tema: string;
  titulo: string;
  corpo_md: string;
  tags: string[] | null;
  resumo: string | null;
  conclusao_provimento: string | null;
  conclusao_nao_conhecimento: string | null;
  source_case_id: string | null;
}

export interface ExtractResult {
  case_id: string;
  extracted: number;
  fundamentos: FundamentoExtractedItem[];
}

export interface FundamentoUpdate {
  tema?: string;
  titulo?: string;
  corpo_md?: string;
  tags?: string[];
  resumo?: string;
  conclusao_provimento?: string;
  conclusao_nao_conhecimento?: string;
}
