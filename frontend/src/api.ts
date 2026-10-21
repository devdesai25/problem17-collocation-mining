import {
  AnalyzeResponse,
  ContingencyResponse,
  NgramOrder,
  SampleItem,
  TraceResponse,
  TranscribeResponse,
} from './types';

const API_BASE = '/api';

export async function checkHealth(): Promise<{ status: string; ffmpeg_available: boolean }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Backend health check failed');
  return res.json();
}

export async function fetchSamples(): Promise<SampleItem[]> {
  const res = await fetch(`${API_BASE}/sample`);
  if (!res.ok) throw new Error('Failed to fetch sample transcripts');
  return res.json();
}

export async function fetchSampleContent(id: number | string): Promise<string> {
  const res = await fetch(`${API_BASE}/sample/${id}`);
  if (!res.ok) throw new Error(`Failed to load sample transcript #${id}`);
  const data = await res.json();
  return data.content;
}

export async function analyzeText(params: {
  text: string;
  ngram: NgramOrder;
  min_freq: number;
  metric: string;
  drop_stopwords: boolean;
  top_k: number;
  use_full_corpus: boolean;
}): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Analysis request failed');
  }
  return res.json();
}

export async function fetchTrace(params: {
  text: string;
  sample_sentence_index?: number;
  target_phrase?: string;
  drop_stopwords?: boolean;
  ngram?: NgramOrder;
  use_full_corpus?: boolean;
}): Promise<TraceResponse> {
  const res = await fetch(`${API_BASE}/trace`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: params.text,
      sample_sentence_index: params.sample_sentence_index ?? 0,
      target_phrase: params.target_phrase,
      drop_stopwords: params.drop_stopwords ?? false,
      ngram: params.ngram ?? 2,
      use_full_corpus: params.use_full_corpus ?? false,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Trace generation failed');
  }
  return res.json();
}

export async function fetchContingency(params: {
  w1: string;
  w2: string;
  text: string;
  drop_stopwords?: boolean;
  use_full_corpus?: boolean;
}): Promise<ContingencyResponse> {
  const url = new URL(`${window.location.origin}${API_BASE}/contingency`);
  url.searchParams.set('w1', params.w1);
  url.searchParams.set('w2', params.w2);
  url.searchParams.set('text', params.text);
  if (params.drop_stopwords) url.searchParams.set('drop_stopwords', 'true');
  if (params.use_full_corpus) url.searchParams.set('use_full_corpus', 'true');

  const res = await fetch(url.toString());
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Contingency calculation failed');
  }
  return res.json();
}

export async function transcribeAudioFile(file: File): Promise<TranscribeResponse> {
  const formData = new FormData();
  formData.append('file', file, file.name);

  const res = await fetch(`${API_BASE}/transcribe`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Transcription failed');
  }
  return res.json();
}
