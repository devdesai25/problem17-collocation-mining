"""Pydantic request and response schemas for the Collocation Mining API."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="Transcript text to analyze")
    ngram: Literal[2, 3] = Field(2, description="N-gram order (2 for Bigram, 3 for Trigram)")
    min_freq: int = Field(3, ge=1, le=10, description="Minimum frequency threshold")
    metric: str = Field("pmi", description="Primary association metric")
    drop_stopwords: bool = Field(False, description="Ablation: remove stopwords before counting")
    top_k: int = Field(50, ge=5, le=500, description="Number of top collocations to return")
    use_full_corpus: bool = Field(False, description="Whether to analyze the entire 28-file corpus")


class CollocationRow(BaseModel):
    rank: int
    phrase: str
    score: float | None
    freq: int
    f_w1: int | None = None
    f_w2: int | None = None
    o11: int | None = None
    o12: int | None = None
    o21: int | None = None
    o22: int | None = None
    n: int | None = None
    w1: str | None = None
    w2: str | None = None
    w3: str | None = None


class CorpusStats(BaseModel):
    sentences: int
    tokens: int
    n_bigrams: int
    n_trigrams: int
    unique_bigrams: int
    unique_trigrams: int
    warn_small_n: bool
    warning_message: str | None = None


class MetricTop5Item(BaseModel):
    rank: int
    phrase: str
    score: float | None
    freq: int


class AnalyzeResponse(BaseModel):
    rankings: list[CollocationRow]
    stats: CorpusStats
    per_metric_top5: dict[str, list[MetricTop5Item]]
    disagreement_note: str
    options: dict[str, Any]
    text_hash: str


class ContingencyFormulaDetail(BaseModel):
    name: str
    formula: str
    substituted: str
    result: float | None
    explanation: str


class ContingencyResponse(BaseModel):
    phrase: str
    w1: str
    w2: str
    o11: float
    o12: float
    o21: float
    o22: float
    n: float
    row1: float
    row2: float
    col1: float
    col2: float
    expected: dict[str, float]
    scores: dict[str, float | None]
    formulas: dict[str, ContingencyFormulaDetail]


class TraceRequest(BaseModel):
    text: str = Field(..., description="Full text to analyze")
    sample_sentence_index: int = Field(0, ge=0, description="Index of sentence to trace")
    target_phrase: str | None = Field(None, description="Optional chosen phrase to trace")
    drop_stopwords: bool = Field(False, description="Whether to drop stopwords")
    ngram: Literal[2, 3] = Field(2, description="N-gram order")
    use_full_corpus: bool = Field(False, description="Whether to trace against the full 28-file corpus")


class TraceStage(BaseModel):
    id: str
    title: str
    subtitle: str
    description: str
    data: dict[str, Any]


class TraceResponse(BaseModel):
    stages: list[TraceStage]
    sample_sentence_index: int
    total_sentences: int
    chosen_phrase: str
    available_sentences: list[dict[str, Any]]


class TranscribeResponse(BaseModel):
    text: str
    language: str
    duration: float


class SampleItem(BaseModel):
    id: int
    filename: str
    city: str
    word_count: int
    preview: str
