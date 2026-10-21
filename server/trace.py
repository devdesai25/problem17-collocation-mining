"""Pipeline trace generator: produces real per-stage intermediate data for animation."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure src/ is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from nltk import pos_tag, sent_tokenize, word_tokenize
from preprocessing import (
    _CLITIC,
    _lemmatizer_singleton,
    clean_token,
    ensure_nltk,
    normalize_text,
    remove_stopwords,
    wordnet_pos,
)
from models import (
    build_counts,
    contingency_bigram,
    rank_metric,
    score_bigram,
)


def generate_pipeline_trace(
    text: str,
    sample_sentence_index: int = 0,
    target_phrase: str | None = None,
    drop_stopwords: bool = False,
    ngram: int = 2,
) -> Dict[str, Any]:
    """Extract real stage-by-stage intermediate transformations from the user's actual text."""
    ensure_nltk()
    normalized = normalize_text(text)
    raw_sentences = sent_tokenize(normalized)
    if not raw_sentences:
        raw_sentences = ["The city council approved the affordable housing proposal."]

    total_sentences = len(raw_sentences)

    # Pick the chosen sentence (fallback to first sentence with >= 2 words if possible)
    valid_indices = []
    available_sentences = []
    for idx, s in enumerate(raw_sentences):
        words = [w for w in s.split() if len(w) > 1]
        available_sentences.append({
            "index": idx,
            "text": s,
            "word_count": len(words),
        })
        if len(words) >= 2:
            valid_indices.append(idx)

    if 0 <= sample_sentence_index < total_sentences:
        chosen_idx = sample_sentence_index
    elif valid_indices:
        chosen_idx = valid_indices[0]
    else:
        chosen_idx = 0

    sample_raw = raw_sentences[chosen_idx]

    # Full corpus processed for counting
    all_processed = []
    for s in raw_sentences:
        toks = [clean_token(t) for t in word_tokenize(s)]
        toks = [t for t in toks if t]
        tagged = pos_tag(toks) if toks else []
        lemma_obj = _lemmatizer_singleton()
        lemmas = [lemma_obj.lemmatize(t, wordnet_pos(tag)) for t, tag in tagged]
        if drop_stopwords:
            lemmas = remove_stopwords(lemmas)
        if lemmas:
            all_processed.append(lemmas)

    corpus_counts = build_counts(all_processed)

    # Detailed stage transformations for the sample sentence:
    # Stage 1: Raw text input
    stage1 = {
        "id": "raw_text",
        "title": "Stage 1: Raw Spoken Dictation",
        "subtitle": "Unstructured transcript or ASR speech input",
        "description": "User dictation or MeetingBank transcript text as received.",
        "data": {
            "sentence": sample_raw,
            "sentence_index": chosen_idx,
            "total_sentences": total_sentences,
        },
    }

    # Stage 2: Sentence segmentation
    stage2 = {
        "id": "sentence_split",
        "title": "Stage 2: Sentence Segmentation",
        "subtitle": "Boundaries preserved; n-grams never cross sentences",
        "description": "Text is segmented into distinct grammatical utterances so collocations cannot bridge conversational turns.",
        "data": {
            "all_sentences_preview": raw_sentences[:5],
            "chosen_sentence": sample_raw,
            "sentence_index": chosen_idx,
            "total_sentences": total_sentences,
        },
    }

    # Stage 3: Tokenization & Normalization
    raw_words = word_tokenize(sample_raw)
    token_steps = []
    cleaned_tokens = []
    for tok in raw_words:
        cleaned = clean_token(tok)
        is_clitic = tok.lower() in _CLITIC
        token_steps.append({
            "original": tok,
            "cleaned": cleaned,
            "was_clitic": is_clitic,
            "dropped": cleaned is None,
        })
        if cleaned:
            cleaned_tokens.append(cleaned)

    stage3 = {
        "id": "tokenize_clean",
        "title": "Stage 3: Token Cleaning & Clitic Expansion",
        "subtitle": "Regex noise filtering, lowercase, punctuation trimming",
        "description": "Clitics expanded (e.g. n't -> not), numbers and punctuation removed, contractions normalized.",
        "data": {
            "original_count": len(raw_words),
            "cleaned_count": len(cleaned_tokens),
            "token_transformations": token_steps,
            "tokens": cleaned_tokens,
        },
    }

    # Stage 4: POS-Aware Lemmatization
    tagged_tokens = pos_tag(cleaned_tokens) if cleaned_tokens else []
    lemma_obj = _lemmatizer_singleton()
    lemmatized = []
    lemma_details = []
    for tok, tag in tagged_tokens:
        pos_code = wordnet_pos(tag)
        lem = lemma_obj.lemmatize(tok, pos_code)
        lemma_details.append({
            "token": tok,
            "pos_tag": tag,
            "pos_category": pos_code,
            "lemma": lem,
            "changed": (tok != lem),
        })
        lemmatized.append(lem)

    if drop_stopwords:
        lemmatized = remove_stopwords(lemmatized)

    stage4 = {
        "id": "lemmatize",
        "title": "Stage 4: POS-Aware Lemmatization",
        "subtitle": "Collapse inflectional variants (nouns, verbs, adjectives)",
        "description": "WordNet lemmatizer collapses plurals and conjugations using Perceptron POS tags while preserving function words.",
        "data": {
            "lemmatized_tokens": lemmatized,
            "lemma_transformations": lemma_details,
            "stopwords_dropped": drop_stopwords,
        },
    }

    # Stage 5: Sentence-Internal N-gram Extraction
    sentence_bigrams = []
    if len(lemmatized) >= 2:
        for i in range(len(lemmatized) - 1):
            sentence_bigrams.append((lemmatized[i], lemmatized[i + 1]))

    sentence_trigrams = []
    if len(lemmatized) >= 3:
        for i in range(len(lemmatized) - 2):
            sentence_trigrams.append((lemmatized[i], lemmatized[i + 1], lemmatized[i + 2]))

    # Select target phrase to trace through remaining stages
    chosen_w1, chosen_w2 = "", ""
    chosen_phrase_str = ""
    if target_phrase and " " in target_phrase:
        parts = target_phrase.strip().split()
        if len(parts) >= 2:
            chosen_w1, chosen_w2 = parts[0], parts[1]
            chosen_phrase_str = f"{chosen_w1} {chosen_w2}"

    if not chosen_phrase_str:
        # Pick from sentence bigrams if available, or first bigram in corpus counts
        if sentence_bigrams:
            chosen_w1, chosen_w2 = sentence_bigrams[0]
            chosen_phrase_str = f"{chosen_w1} {chosen_w2}"
        elif corpus_counts.get("bigram"):
            (b1, b2), _ = next(iter(corpus_counts["bigram"].items()))
            chosen_w1, chosen_w2 = b1, b2
            chosen_phrase_str = f"{b1} {b2}"
        else:
            chosen_w1, chosen_w2 = "city", "council"
            chosen_phrase_str = "city council"

    stage5 = {
        "id": "ngram_extraction",
        "title": "Stage 5: Candidate N-Gram Extraction",
        "subtitle": f"Generating sliding window {ngram}-grams",
        "description": "Sentence-internal sliding window extracts multi-word candidates without crossing boundaries.",
        "data": {
            "extracted_bigrams": [" ".join(bg) for bg in sentence_bigrams],
            "extracted_trigrams": [" ".join(tg) for tg in sentence_trigrams],
            "chosen_target_phrase": chosen_phrase_str,
        },
    }

    # Stage 6: Corpus Counting & Marginal Tracking
    f_bigram = corpus_counts["bigram"].get((chosen_w1, chosen_w2), 0)
    f_left = corpus_counts["left"].get(chosen_w1, 0)
    f_right = corpus_counts["right"].get(chosen_w2, 0)
    total_n = corpus_counts.get("n_bigrams", 0)

    stage6 = {
        "id": "counting",
        "title": "Stage 6: Corpus Counting & Marginal Tracking",
        "subtitle": f"Joint co-occurrence & directional margins for '{chosen_phrase_str}'",
        "description": "Global aggregation computes exact sentence-internal joint count O11 and left/right marginal sums.",
        "data": {
            "phrase": chosen_phrase_str,
            "w1": chosen_w1,
            "w2": chosen_w2,
            "f_joint_o11": f_bigram,
            "f_w1_left": f_left,
            "f_w2_right": f_right,
            "total_bigram_tokens_N": total_n,
        },
    }

    # Stage 7: 2x2 Contingency Table Construction
    ct = contingency_bigram(chosen_w1, chosen_w2, corpus_counts)
    stage7 = {
        "id": "contingency_table",
        "title": "Stage 7: 2x2 Contingency Matrix",
        "subtitle": f"Complete 4-cell distribution for '{chosen_phrase_str}'",
        "description": "Joint, partial, and negative co-occurrences structured so row sums and column sums equal total tokens N.",
        "data": {
            "phrase": chosen_phrase_str,
            "w1": chosen_w1,
            "w2": chosen_w2,
            "o11": ct.o11,
            "o12": ct.o12,
            "o21": ct.o21,
            "o22": ct.o22,
            "row1": ct.row1,
            "row2": ct.row2,
            "col1": ct.col1,
            "col2": ct.col2,
            "n": ct.n,
            "cells_step_by_step": [
                {"cell": "O11", "label": f"'{chosen_w1}' followed by '{chosen_w2}'", "formula": "f(w1, w2)", "value": ct.o11},
                {"cell": "O12", "label": f"'{chosen_w1}' followed by other words", "formula": "f(w1) - O11", "value": ct.o12},
                {"cell": "O21", "label": f"Other words followed by '{chosen_w2}'", "formula": "f(w2) - O11", "value": ct.o21},
                {"cell": "O22", "label": "Neither word in bigram", "formula": "N - O11 - O12 - O21", "value": ct.o22},
            ],
        },
    }

    # Stage 8: Mathematical Association Scoring
    scores = score_bigram(ct)
    stage8 = {
        "id": "scoring",
        "title": "Stage 8: Multi-Paradigm Association Scoring",
        "subtitle": f"First-principles evaluation of '{chosen_phrase_str}'",
        "description": "Vectorized statistical tests compare observed co-occurrence against expected counts under independence.",
        "data": {
            "phrase": chosen_phrase_str,
            "scores": {
                "pmi": scores.get("pmi"),
                "npmi": scores.get("npmi"),
                "chi_sq": scores.get("chi_sq"),
                "chi_sq_yates": scores.get("chi_sq_yates"),
                "student_t": scores.get("student_t"),
                "likelihood_ratio": scores.get("likelihood_ratio"),
            },
        },
    }

    # Stage 9: Corpus-Wide Ranking & Filtering
    rankings_pmi = rank_metric("pmi", corpus_counts, min_freq=1)
    target_rank = None
    for r in rankings_pmi:
        if r["phrase"] == chosen_phrase_str:
            target_rank = r["rank"]
            break

    top_preview = [
        {"rank": r["rank"], "phrase": r["phrase"], "score": r["score"], "freq": r["freq"]}
        for r in rankings_pmi[:5]
    ]

    stage9 = {
        "id": "ranking",
        "title": "Stage 9: Global Ranking & Threshold Filtering",
        "subtitle": f"'{chosen_phrase_str}' placed at Rank #{target_rank or 'N/A'}",
        "description": "Sorted deterministically by score descending, then phrase string ascending with frequency thresholds applied.",
        "data": {
            "phrase": chosen_phrase_str,
            "target_rank": target_rank,
            "total_candidates": len(rankings_pmi),
            "top_5_pmi": top_preview,
        },
    }

    return {
        "stages": [stage1, stage2, stage3, stage4, stage5, stage6, stage7, stage8, stage9],
        "sample_sentence_index": chosen_idx,
        "total_sentences": total_sentences,
        "chosen_phrase": chosen_phrase_str,
        "available_sentences": available_sentences,
    }
