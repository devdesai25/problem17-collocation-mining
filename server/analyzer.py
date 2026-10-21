"""Analysis engine bridging FastAPI to src/preprocessing.py and src/models.py."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure src/ is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from models import (
    BIGRAM_METRICS,
    Contingency,
    build_counts,
    contingency_bigram,
    rank_metric,
    rank_trigram_pmi,
    score_bigram,
)
from preprocessing import CORPUS_DIR, preprocess_corpus, segment_and_tokenize

# In-memory LRU-like cache (stores up to 100 recent analysis results)
_CACHE: OrderedDict[str, Dict[str, Any]] = OrderedDict()
_MAX_CACHE = 100


def get_text_hash(text: str, options: Dict[str, Any]) -> str:
    key_str = f"{text}|{json.dumps(options, sort_keys=True)}"
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()[:16]


def analyze_text_or_corpus(
    text: str,
    ngram: int = 2,
    min_freq: int = 3,
    metric: str = "pmi",
    drop_stopwords: bool = False,
    top_k: int = 50,
    use_full_corpus: bool = False,
) -> Dict[str, Any]:
    """Perform deterministic collocation mining with caching."""
    options = {
        "ngram": ngram,
        "min_freq": min_freq,
        "metric": metric,
        "drop_stopwords": drop_stopwords,
        "top_k": top_k,
        "use_full_corpus": use_full_corpus,
    }
    cache_key = get_text_hash(text, options)
    if cache_key in _CACHE:
        _CACHE.move_to_end(cache_key)
        cached_result = _CACHE[cache_key].copy()
        cached_result["cached"] = True
        return cached_result

    # 1. Tokenize and segment
    if use_full_corpus:
        prep = preprocess_corpus(drop_stopwords=drop_stopwords)
        sentences = prep["sentences"]
        n_tokens = prep["n_tokens"]
    else:
        sentences = segment_and_tokenize(text, drop_stopwords=drop_stopwords)
        n_tokens = sum(len(s) for s in sentences)

    counts = build_counts(sentences)

    # 2. Extract stats
    n_sentences = len(sentences)
    n_bigrams = counts.get("n_bigrams", 0)
    n_trigrams = counts.get("n_trigrams", 0)
    unique_bigrams = len(counts.get("bigram", {}))
    unique_trigrams = len(counts.get("trigram", {}))

    warn_small_n = False
    warning_message = None
    if n_bigrams < 20 or (min_freq > 1 and unique_bigrams > 0 and max(counts.get("bigram", {}).values(), default=0) < min_freq):
        warn_small_n = True
        warning_message = (
            f"Small sample size (N={n_bigrams} bigram tokens). Collocation statistical metrics require sufficient "
            f"co-occurrences to reach significance. Suggest lowering min_freq to 1 or loading a sample transcript."
        )

    # 3. Rankings & Comparison Top-5
    rankings: List[Dict[str, Any]] = []
    per_metric_top5: Dict[str, List[Dict[str, Any]]] = {}

    if ngram == 2:
        valid_metric = metric if metric in BIGRAM_METRICS else "pmi"
        full_rankings = rank_metric(valid_metric, counts, min_freq=min_freq)
        rankings = full_rankings[:top_k]

        # Compute side-by-side top-5 across the four key distinct paradigms
        comparison_metrics = ["pmi", "chi_sq", "student_t", "likelihood_ratio"]
        for m in comparison_metrics:
            m_rankings = rank_metric(m, counts, min_freq=min_freq)
            per_metric_top5[m] = [
                {
                    "rank": r["rank"],
                    "phrase": r["phrase"],
                    "score": r["score"],
                    "freq": r["freq"],
                }
                for r in m_rankings[:5]
            ]
    else:
        # Trigram PMI
        full_tri = rank_trigram_pmi(counts, min_freq=min_freq)
        rankings = full_tri[:top_k]
        per_metric_top5["trigram_pmi"] = [
            {
                "rank": r["rank"],
                "phrase": r["phrase"],
                "score": r["score"],
                "freq": r["freq"],
            }
            for r in full_tri[:5]
        ]

    disagreement_note = (
        "PMI highlights rare, exclusive domain keyphrases (high information gain per word); "
        "Chi-Square tests non-directional co-occurrence independence; "
        "Student's t and Likelihood Ratio (G²) reward high joint frequencies, pulling in common conversational "
        "patterns (e.g. 'thank you', 'of the') and procedural formulas."
    )

    result = {
        "rankings": rankings,
        "stats": {
            "sentences": n_sentences,
            "tokens": n_tokens,
            "n_bigrams": n_bigrams,
            "n_trigrams": n_trigrams,
            "unique_bigrams": unique_bigrams,
            "unique_trigrams": unique_trigrams,
            "warn_small_n": warn_small_n,
            "warning_message": warning_message,
        },
        "per_metric_top5": per_metric_top5,
        "disagreement_note": disagreement_note,
        "options": options,
        "text_hash": cache_key,
        "cached": False,
    }

    # Save to LRU cache
    if len(_CACHE) >= _MAX_CACHE:
        _CACHE.popitem(last=False)
    _CACHE[cache_key] = result
    return result


def compute_contingency_detail(
    w1: str,
    w2: str,
    text: str,
    drop_stopwords: bool = False,
    use_full_corpus: bool = False,
) -> Dict[str, Any]:
    """Compute exact 2x2 contingency table, live metrics, and formula derivations."""
    if use_full_corpus:
        prep = preprocess_corpus(drop_stopwords=drop_stopwords)
        sentences = prep["sentences"]
    else:
        sentences = segment_and_tokenize(text, drop_stopwords=drop_stopwords)

    counts = build_counts(sentences)
    ct = contingency_bigram(w1, w2, counts)
    scores = score_bigram(ct)

    o11 = float(ct.o11)
    o12 = float(ct.o12)
    o21 = float(ct.o21)
    o22 = float(ct.o22)
    n = float(ct.n)
    r1 = float(ct.row1)
    r2 = float(ct.row2)
    c1 = float(ct.col1)
    c2 = float(ct.col2)

    e11 = (r1 * c1) / n if n > 0 else 0.0
    e12 = (r1 * c2) / n if n > 0 else 0.0
    e21 = (r2 * c1) / n if n > 0 else 0.0
    e22 = (r2 * c2) / n if n > 0 else 0.0

    # Format formulas with substituted numbers
    pmi_val = scores.get("pmi")
    npmi_val = scores.get("npmi")
    chi_val = scores.get("chi_sq")
    yates_val = scores.get("chi_sq_yates")
    t_val = scores.get("student_t")
    g2_val = scores.get("likelihood_ratio")

    formulas: Dict[str, Dict[str, Any]] = {
        "pmi": {
            "name": "Pointwise Mutual Information (PMI)",
            "formula": "PMI(w1, w2) = log2( (O11 * N) / (R1 * C1) )",
            "substituted": f"log2( ({o11:.0f} * {n:.0f}) / ({r1:.0f} * {c1:.0f}) )" if r1 * c1 > 0 else "Undefined (zero marginal)",
            "result": pmi_val,
            "explanation": "Measures information gain over the independence null hypothesis. Sensitive to rare exclusive pairs.",
        },
        "npmi": {
            "name": "Normalized PMI (NPMI)",
            "formula": "NPMI = PMI / ( -log2(O11 / N) )",
            "substituted": f"{pmi_val:.4f} / ( -log2({o11:.0f} / {n:.0f}) )" if pmi_val is not None and o11 > 0 else "Undefined",
            "result": npmi_val,
            "explanation": "Scales PMI to [-1, 1], where +1 indicates perfect co-occurrence and 0 is independent co-occurrence.",
        },
        "chi_sq": {
            "name": "Pearson's Chi-Square (χ²)",
            "formula": "χ² = N * (O11*O22 - O12*O21)² / (R1 * C1 * R2 * C2)",
            "substituted": f"{n:.0f} * ({o11:.0f}*{o22:.0f} - {o12:.0f}*{o21:.0f})² / ({r1:.0f} * {c1:.0f} * {r2:.0f} * {c2:.0f})",
            "result": chi_val,
            "explanation": "Non-directional test of statistical dependence. Saturates at N for exclusive pairs regardless of frequency.",
        },
        "chi_sq_yates": {
            "name": "Yates-Corrected Chi-Square (χ² Yates)",
            "formula": "χ² = N * ( max(0, |O11*O22 - O12*O21| - N/2) )² / (R1 * C1 * R2 * C2)",
            "substituted": f"{n:.0f} * ( max(0, |{o11:.0f}*{o22:.0f} - {o12:.0f}*{o21:.0f}| - {n/2:.1f}) )² / ({r1:.0f} * {c1:.0f} * {r2:.0f} * {c2:.0f})",
            "result": yates_val,
            "explanation": "Subtracts N/2 inside deviation to correct for small sample sizes and penalize isolated hapaxes.",
        },
        "student_t": {
            "name": "Student's t-test (Manning & Schütze)",
            "formula": "t = ( O11 - (R1 * C1 / N) ) / sqrt(O11)",
            "substituted": f"( {o11:.0f} - ({r1:.0f} * {c1:.0f} / {n:.0f}) ) / sqrt({o11:.0f})" if o11 > 0 else "Undefined",
            "result": t_val,
            "explanation": "One-sample t-statistic under Poisson variance-equals-mean assumption. Strongly rewards high raw counts.",
        },
        "likelihood_ratio": {
            "name": "Log-Likelihood Ratio (Dunning G²)",
            "formula": "G² = 2 * Σ [ Oij * ln(Oij / Eij) ]",
            "substituted": f"2 * [ {o11:.0f}*ln({o11:.0f}/{e11:.2f}) + {o12:.0f}*ln(...) + ... ]",
            "result": g2_val,
            "explanation": "Asymptotically chi-square (1 df). Best calibrated for sparse NLP counts and skewed distributions.",
        },
    }

    return {
        "phrase": f"{w1} {w2}",
        "w1": w1,
        "w2": w2,
        "o11": o11,
        "o12": o12,
        "o21": o21,
        "o22": o22,
        "n": n,
        "row1": r1,
        "row2": r2,
        "col1": c1,
        "col2": c2,
        "expected": {
            "e11": round(e11, 4),
            "e12": round(e12, 4),
            "e21": round(e21, 4),
            "e22": round(e22, 4),
        },
        "scores": scores,
        "formulas": formulas,
    }


def list_sample_transcripts() -> List[Dict[str, Any]]:
    """List available MeetingBank sample transcripts with metadata."""
    if not CORPUS_DIR.is_dir():
        return []

    samples = []
    files = sorted(CORPUS_DIR.glob("*.txt"))
    for idx, path in enumerate(files, start=1):
        filename = path.name
        # Filename pattern: 01_alamedacc_01152019_2019_6368.txt
        parts = filename.split("_")
        city_code = parts[1] if len(parts) > 1 else "meeting"
        city_map = {
            "alamedacc": "Alameda City Council",
            "bostoncc": "Boston City Council",
            "denvercitycouncil": "Denver City Council",
            "kingcountycc": "King County Council",
            "longbeachcc": "Long Beach City Council",
            "seattlecitycouncil": "Seattle City Council",
        }
        city = city_map.get(city_code, city_code.capitalize())
        content = path.read_text(encoding="utf-8")
        word_count = len(content.split())
        preview = " ".join(content.split()[:35]) + "..."
        samples.append(
            {
                "id": idx,
                "filename": filename,
                "city": city,
                "word_count": word_count,
                "preview": preview,
            }
        )
    return samples


def get_sample_transcript_content(file_id_or_name: str | int) -> str:
    """Retrieve full text of a selected sample transcript."""
    files = sorted(CORPUS_DIR.glob("*.txt"))
    if isinstance(file_id_or_name, int) or (isinstance(file_id_or_name, str) and file_id_or_name.isdigit()):
        idx = int(file_id_or_name) - 1
        if 0 <= idx < len(files):
            return files[idx].read_text(encoding="utf-8")
    for f in files:
        if f.name == file_id_or_name:
            return f.read_text(encoding="utf-8")
    if files:
        return files[0].read_text(encoding="utf-8")
    return ""
