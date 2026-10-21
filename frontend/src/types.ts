export type NgramOrder = 2 | 3;

export type BigramMetric =
  | 'pmi'
  | 'npmi'
  | 'pmi2'
  | 'pmi3'
  | 'chi_sq'
  | 'chi_sq_yates'
  | 'student_t'
  | 'likelihood_ratio';

export interface CollocationRow {
  rank: number;
  phrase: string;
  score: number | null;
  freq: number;
  f_w1?: number | null;
  f_w2?: number | null;
  o11?: number | null;
  o12?: number | null;
  o21?: number | null;
  o22?: number | null;
  n?: number | null;
  w1?: string | null;
  w2?: string | null;
  w3?: string | null;
}

export interface CorpusStats {
  sentences: number;
  tokens: number;
  n_bigrams: number;
  n_trigrams: number;
  unique_bigrams: number;
  unique_trigrams: number;
  warn_small_n: boolean;
  warning_message?: string | null;
}

export interface MetricTop5Item {
  rank: number;
  phrase: string;
  score: number | null;
  freq: number;
}

export interface AnalyzeResponse {
  rankings: CollocationRow[];
  stats: CorpusStats;
  per_metric_top5: Record<string, MetricTop5Item[]>;
  disagreement_note: string;
  options: {
    ngram: NgramOrder;
    min_freq: number;
    metric: string;
    drop_stopwords: boolean;
    top_k: number;
    use_full_corpus: boolean;
  };
  text_hash: string;
  cached: boolean;
}

export interface ContingencyFormulaDetail {
  name: string;
  formula: string;
  substituted: string;
  result: number | null;
  explanation: string;
}

export interface ContingencyResponse {
  phrase: string;
  w1: string;
  w2: string;
  o11: number;
  o12: number;
  o21: number;
  o22: number;
  n: number;
  row1: number;
  row2: number;
  col1: number;
  col2: number;
  expected: {
    e11: number;
    e12: number;
    e21: number;
    e22: number;
  };
  scores: Record<string, number | null>;
  formulas: Record<string, ContingencyFormulaDetail>;
}

export interface TraceStage {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  data: Record<string, any>;
}

export interface TraceResponse {
  stages: TraceStage[];
  sample_sentence_index: number;
  total_sentences: number;
  chosen_phrase: string;
  available_sentences: Array<{
    index: number;
    text: string;
    word_count: number;
  }>;
}

export interface SampleItem {
  id: number;
  filename: string;
  city: string;
  word_count: number;
  preview: string;
}

export interface TranscribeResponse {
  text: string;
  language: string;
  duration: number;
}
