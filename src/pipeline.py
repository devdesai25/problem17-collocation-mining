"""End-to-end collocation evaluation.

Run from the project root:

    python src/pipeline.py
    python src/pipeline.py --docs

The base run is offline. It reads ``data/raw_transcripts/*.txt`` and
``data/annotated/gold_collocations.csv``, writes ``reports/``, and refreshes
the processed-token block in ``PROVENANCE.md``. ``--docs`` rebuilds the two
PDFs from those report files.

Precision, recall, and F1 at k use the curated gold list for the same n-gram
order as the ranking:

    precision@k = |top-k intersect gold| / k
    recall@k    = |top-k intersect gold| / |gold|
    F1@k        = 2 * precision@k * recall@k / (precision@k + recall@k)

Bigram metrics are scored against bigram gold only. Trigram metrics are
scored against trigram gold only. A trigram can never appear in a bigram
top-k, so mixing the two lists would make recall uninterpretable.

Tie-breaking is score descending, then phrase ascending. Seeds are fixed
even though the ranking itself does not sample.
"""

from __future__ import annotations

import importlib.util
import json
import math
import random
import string
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from scipy.stats import spearmanr

from models import (
    BIGRAM_METRICS,
    build_counts,
    contingency_bigram,
    nltk_bigram_rankings,
    nltk_scores_same_counts,
    nltk_trigram_rankings,
    phrase_of,
    rank_metric,
    rank_trigram_pmi,
    worked_example,
)
from preprocessing import preprocess_corpus, stopword_set

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
CHARTS = REPORTS / "charts"
GOLD_PATH = ROOT / "data" / "annotated" / "gold_collocations.csv"
COMMENTARY_PATH = ROOT / "data" / "annotated" / "phrase_commentary.json"
FAILURE_PATH = ROOT / "data" / "annotated" / "failure_analysis.md"
PROVENANCE_PATH = ROOT / "data" / "raw_transcripts" / "PROVENANCE.md"
MANIFEST_PATH = ROOT / "data" / "corpus_manifest.json"

KS = (10, 20, 30, 40, 50)
TOP_N = 20

DISPLAY = {
    "pmi": "PMI",
    "pmi2": "PMI^2",
    "pmi3": "PMI^3",
    "npmi": "NPMI",
    "chi_sq": "Chi-square",
    "chi_sq_yates": "Chi-square (Yates)",
    "student_t": "Student's t",
    "likelihood_ratio": "Log-likelihood",
    "nltk_pmi": "NLTK PMI",
    "nltk_chi_sq": "NLTK chi-square",
    "nltk_student_t": "NLTK t",
    "nltk_likelihood_ratio": "NLTK G^2",
    "trigram_pmi": "Trigram PMI",
    "nltk_trigram_pmi": "NLTK trigram PMI",
    "nltk_trigram_chi_sq": "NLTK trigram chi-square",
    "nltk_trigram_student_t": "NLTK trigram t",
    "nltk_trigram_likelihood_ratio": "NLTK trigram G^2",
}

NLTK_BIGRAM = (
    "nltk_pmi",
    "nltk_chi_sq",
    "nltk_student_t",
    "nltk_likelihood_ratio",
)
NLTK_TRIGRAM = (
    "nltk_trigram_pmi",
    "nltk_trigram_chi_sq",
    "nltk_trigram_student_t",
    "nltk_trigram_likelihood_ratio",
)
SCRATCH_TO_NLTK = {
    "pmi": "nltk_pmi",
    "chi_sq": "nltk_chi_sq",
    "student_t": "nltk_student_t",
    "likelihood_ratio": "nltk_likelihood_ratio",
}
COMPARE_METRICS = list(BIGRAM_METRICS) + list(NLTK_BIGRAM)


class _SafeMap(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def fill_template(template: str, mapping: dict) -> str:
    return string.Formatter().vformat(template, (), _SafeMap(mapping))


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    frame = pd.DataFrame(rows)
    for column in columns:
        if column not in frame.columns:
            frame[column] = np.nan
    frame = frame[columns]
    frame.to_csv(path, index=False, float_format="%.10g")


def prf_at_k(phrases: list[str], gold: set[str], k: int) -> dict:
    top = phrases[:k]
    hits = len(set(top) & gold)
    precision = hits / k
    recall = hits / len(gold) if gold else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "k": k,
        "hits": hits,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def load_gold() -> pd.DataFrame:
    frame = pd.read_csv(GOLD_PATH)
    expected = {"phrase", "ngram", "category", "frequency"}
    missing = expected - set(frame.columns)
    if missing:
        raise SystemExit(f"gold file missing columns: {sorted(missing)}")
    frame["ngram"] = frame["ngram"].astype(int)
    frame["frequency"] = frame["frequency"].astype(int)
    frame["phrase"] = frame["phrase"].astype(str)
    return frame


def check_gold_frequencies(frame: pd.DataFrame, counts: dict) -> None:
    mismatches = []
    for row in frame.itertuples(index=False):
        parts = tuple(row.phrase.split())
        if row.ngram == 2:
            observed = int(counts["bigram"].get(parts, 0))
        elif row.ngram == 3:
            observed = int(counts["trigram"].get(parts, 0))
        else:
            mismatches.append(f"{row.phrase}: ngram {row.ngram}")
            continue
        if observed != int(row.frequency):
            mismatches.append(f"{row.phrase}: file={row.frequency} corpus={observed}")
    if mismatches:
        preview = "\n".join(mismatches[:12])
        raise SystemExit(f"Gold frequencies do not match the corpus:\n{preview}")


def index_rankings(rows: list[dict]) -> dict[str, dict]:
    return {row["phrase"]: row for row in rows}


def top_phrases(rows: list[dict], k: int = TOP_N) -> list[str]:
    return [row["phrase"] for row in rows[:k]]


def _rho(labels: list[str], matrix: np.ndarray, left: str, right: str) -> float:
    return float(matrix[labels.index(left), labels.index(right)])


def mean_freq(rows: list[dict], k: int = TOP_N) -> float:
    chunk = rows[:k]
    if not chunk:
        return float("nan")
    return float(sum(row["freq"] for row in chunk) / len(chunk))


def frac_freq(rows: list[dict], predicate, k: int = TOP_N) -> float:
    chunk = rows[:k]
    if not chunk:
        return float("nan")
    return float(sum(1 for row in chunk if predicate(row["freq"])) / len(chunk))


def spearman_score_vs_freq(rows: list[dict]) -> float:
    if len(rows) < 3:
        return float("nan")
    scores = [row["score"] for row in rows]
    freqs = [row["freq"] for row in rows]
    if len(set(scores)) < 2 or len(set(freqs)) < 2:
        return float("nan")
    rho = spearmanr(scores, freqs).statistic
    if rho is None or (isinstance(rho, float) and math.isnan(rho)):
        return float("nan")
    return float(rho)


def pairwise_spearman(rankings: dict[str, list[dict]], metrics: list[str]) -> tuple[list[str], np.ndarray, int]:
    phrase_sets = [set(index_rankings(rankings[name])) for name in metrics]
    common = set.intersection(*phrase_sets) if phrase_sets else set()
    phrases = sorted(common)
    matrix = np.eye(len(metrics))
    indexes = [index_rankings(rankings[name]) for name in metrics]
    for i, left in enumerate(indexes):
        for j in range(i + 1, len(indexes)):
            right = indexes[j]
            xs = [left[phrase]["score"] for phrase in phrases]
            ys = [right[phrase]["score"] for phrase in phrases]
            if len(phrases) < 3 or len(set(xs)) < 2 or len(set(ys)) < 2:
                rho = float("nan")
            else:
                rho = float(spearmanr(xs, ys).statistic)
            matrix[i, j] = rho
            matrix[j, i] = rho
    return matrix, len(phrases)


def jaccard_top(a: list[str], b: list[str]) -> tuple[int, float]:
    sa, sb = set(a), set(b)
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter, (inter / union if union else 0.0)


def enrich_counts(row: dict, counts: dict) -> dict:
    parts = tuple(row["phrase"].split())
    out = dict(row)
    if len(parts) == 2 and parts in counts["bigram"]:
        ct = contingency_bigram(parts[0], parts[1], counts)
        out["freq"] = int(ct.o11)
        out["f_w1"] = int(ct.row1)
        out["f_w2"] = int(ct.col1)
        out["o11"] = int(ct.o11)
        out["o12"] = int(ct.o12)
        out["o21"] = int(ct.o21)
        out["o22"] = int(ct.o22)
    elif len(parts) == 3 and parts in counts["trigram"]:
        out["freq"] = int(counts["trigram"][parts])
    return out


def nltk_same_count_table(counts: dict, min_freq: int) -> dict[str, dict[str, float]]:
    """NLTK association functions on our contingency cells, keyed by phrase."""
    table: dict[str, dict[str, float]] = {}
    for (w1, w2), freq in counts["bigram"].items():
        if freq < min_freq:
            continue
        ct = contingency_bigram(w1, w2, counts)
        if ct.o11 <= 0 or ct.row1 <= 0 or ct.col1 <= 0 or ct.n <= 0:
            continue
        try:
            scores = nltk_scores_same_counts(ct.o11, ct.row1, ct.col1, ct.n)
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        table[phrase_of((w1, w2))] = scores
    return table


def median(values: list[float]) -> float:
    if not values:
        return float("nan")
    return float(np.median(np.array(values, dtype=float)))


def log_base_summary(scratch: dict[str, list[dict]], same_counts: dict[str, dict[str, float]]) -> dict:
    buckets = {name: [] for name in SCRATCH_TO_NLTK}
    abs_pearson = []
    abs_yates = []
    abs_t = []
    for row in scratch["pmi"]:
        other = same_counts.get(row["phrase"])
        if not other:
            continue
        if abs(row["score"]) > 1e-6 and other["pmi"] != 0:
            buckets["pmi"].append(other["pmi"] / row["score"])
    for row in scratch["chi_sq"]:
        other = same_counts.get(row["phrase"])
        if not other:
            continue
        abs_pearson.append(abs(other["chi_sq"] - row["score"]))
    yates_index = index_rankings(scratch["chi_sq_yates"])
    for phrase, other in same_counts.items():
        if phrase in yates_index:
            abs_yates.append(abs(other["chi_sq"] - yates_index[phrase]["score"]))
    for row in scratch["student_t"]:
        other = same_counts.get(row["phrase"])
        if not other:
            continue
        abs_t.append(abs(other["student_t"] - row["score"]))
        if abs(row["score"]) > 1e-6 and other["likelihood_ratio"] != 0:
            pass
    ll_index = index_rankings(scratch["likelihood_ratio"])
    ll_ratios = []
    for phrase, other in same_counts.items():
        if phrase not in ll_index:
            continue
        ours = ll_index[phrase]["score"]
        if abs(ours) > 1e-6 and other["likelihood_ratio"] != 0:
            ll_ratios.append(other["likelihood_ratio"] / ours)
    pmi_ratio = median(buckets["pmi"])
    ll_ratio = median(ll_ratios)
    pearson_gap = median(abs_pearson)
    yates_gap = median(abs_yates)
    return {
        "pmi_median_ratio_nltk_over_scratch": pmi_ratio,
        "pmi_reference_if_natural_log": math.log(2),
        "pmi_uses": "log2" if abs(pmi_ratio - 1.0) < abs(pmi_ratio - math.log(2)) else "ln",
        "llr_median_ratio_nltk_over_scratch": ll_ratio,
        "llr_reference_if_log2": 1.0 / math.log(2),
        "llr_uses": "ln" if abs(ll_ratio - 1.0) < abs(ll_ratio - (1.0 / math.log(2))) else "log2",
        "chi_median_abs_diff_vs_pearson": pearson_gap,
        "chi_median_abs_diff_vs_yates": yates_gap,
        "chi_nltk_matches": "pearson_no_yates" if pearson_gap <= yates_gap else "yates",
        "student_t_median_abs_diff": median(abs_t),
        "n_pmi_ratios": len(buckets["pmi"]),
        "n_llr_ratios": len(ll_ratios),
    }


def comparison_rows(
    metric: str,
    scratch_rows: list[dict],
    finder_rows: list[dict],
    same_counts: dict[str, dict[str, float]],
) -> list[dict]:
    finder = index_rankings(finder_rows)
    nltk_key = {
        "pmi": "pmi",
        "chi_sq": "chi_sq",
        "student_t": "student_t",
        "likelihood_ratio": "likelihood_ratio",
    }[metric]
    rows = []
    for row in scratch_rows:
        phrase = row["phrase"]
        same = same_counts.get(phrase, {}).get(nltk_key)
        found = finder.get(phrase)
        finder_score = found["score"] if found else float("nan")
        same_score = float(same) if same is not None else float("nan")
        rows.append(
            {
                "phrase": phrase,
                "freq": row["freq"],
                "scratch_score": row["score"],
                "nltk_finder_score": finder_score,
                "nltk_same_counts_score": same_score,
                "abs_diff_finder": abs(row["score"] - finder_score) if found else float("nan"),
                "abs_diff_same_counts": abs(row["score"] - same_score) if same is not None else float("nan"),
            }
        )
    return rows


def largest_finder_gap(rows: list[dict]) -> dict:
    usable = [row for row in rows if not math.isnan(row["abs_diff_finder"])]
    if not usable:
        return {}
    worst = max(usable, key=lambda row: (row["abs_diff_finder"], row["phrase"]))
    return {
        "phrase": worst["phrase"],
        "freq": worst["freq"],
        "scratch_score": worst["scratch_score"],
        "nltk_finder_score": worst["nltk_finder_score"],
        "abs_diff_finder": worst["abs_diff_finder"],
    }


def unique_top_phrases(rankings: dict[str, list[dict]], metrics: list[str]) -> list[dict]:
    owners: dict[str, list[str]] = {}
    for name in metrics:
        for row in rankings[name][:TOP_N]:
            owners.setdefault(row["phrase"], []).append(name)
    singles = []
    for phrase, names in owners.items():
        if len(names) != 1:
            continue
        metric = names[0]
        row = index_rankings(rankings[metric])[phrase]
        singles.append(
            {
                "phrase": phrase,
                "metric": metric,
                "score": row["score"],
                "freq": row["freq"],
            }
        )
    singles.sort(key=lambda item: (item["metric"], -item["score"], item["phrase"]))
    return singles


def load_write_commentary():
    script = ROOT / "scripts" / "write_commentary.py"
    spec = importlib.util.spec_from_file_location("write_commentary", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def commentary_for_rankings(rankings: dict[str, list[dict]], metrics: list[str]) -> dict:
    """Regenerate per-phrase notes for the top-20 this run actually produced."""
    phrases_by_metric = {
        name: [row["phrase"] for row in rankings[name][:TOP_N]] for name in metrics
    }
    commentary = load_write_commentary().build_commentary(phrases_by_metric)
    COMMENTARY_PATH.write_text(json.dumps(commentary, indent=2), encoding="utf-8")
    return commentary


def resolve_commentary(metric: str, row: dict, commentary: dict) -> tuple[str, str]:
    entry = commentary.get(metric, {}).get(row["phrase"])
    if not entry:
        return "UNREVIEWED", "UNREVIEWED"
    mapping = {
        "phrase": row["phrase"],
        "freq": row.get("freq", ""),
        "score": f"{row['score']:.6g}",
        "f_w1": row.get("f_w1", ""),
        "f_w2": row.get("f_w2", ""),
        "metric": DISPLAY.get(metric, metric),
    }
    text = fill_template(str(entry.get("commentary", "UNREVIEWED")), mapping)
    label = str(entry.get("label", "UNREVIEWED"))
    return label, text


def markdown_table(headers: list[str], records: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for record in records:
        cells = [str(cell).replace("|", "\\|").replace("\n", " ") for cell in record]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def flat_mapping(summary: dict) -> dict[str, str]:
    flat: dict[str, str] = {}

    def walk(prefix: str, value) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                walk(f"{prefix}_{key}" if prefix else str(key), child)
        elif isinstance(value, list):
            return
        elif isinstance(value, float):
            flat[prefix] = f"{value:.6g}"
        elif value is None:
            flat[prefix] = ""
        else:
            flat[prefix] = str(value)

    walk("", summary)
    return flat


def update_provenance(n_tokens: int, n_sentences: int, n_types: int) -> None:
    text = PROVENANCE_PATH.read_text(encoding="utf-8")
    start = "<!-- PROCESSED_STATS_START -->"
    end = "<!-- PROCESSED_STATS_END -->"
    block = (
        f"{start}\n"
        f"processed_tokens: {n_tokens}\n"
        f"processed_sentences: {n_sentences}\n"
        f"processed_lemmas: {n_types}\n"
        f"{end}"
    )
    if start in text and end in text:
        pre, rest = text.split(start, 1)
        _, post = rest.split(end, 1)
        text = pre + block + post
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    PROVENANCE_PATH.write_text(text, encoding="utf-8")


def draw_architecture(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11.2, 7.2))
    ax.set_xlim(0, 112)
    ax.set_ylim(0, 72)
    ax.axis("off")
    ax.set_title("Collocation extraction pipeline", fontsize=14, pad=8)

    def box(x, y, w, h, text, face):
        patch = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.4,rounding_size=0.8",
            facecolor=face,
            edgecolor="#1f2933",
            linewidth=1.0,
        )
        ax.add_patch(patch)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8, wrap=True)

    def arrow(x1, y1, x2, y2):
        ax.add_patch(
            FancyArrowPatch(
                (x1, y1),
                (x2, y2),
                arrowstyle="-|>",
                mutation_scale=12,
                linewidth=1.0,
                color="#334e68",
            )
        )

    box(4, 58, 22, 9, "raw transcripts\n*.txt", "#e6f2ff")
    box(32, 58, 24, 9, "normalize\nsentence-split", "#e6f2ff")
    box(62, 58, 22, 9, "tokenize\nPOS lemma", "#e6f2ff")
    box(90, 58, 18, 9, "keep stopwords\n(main path)", "#fff4d6")
    arrow(26, 62.5, 32, 62.5)
    arrow(56, 62.5, 62, 62.5)
    arrow(84, 62.5, 90, 62.5)

    box(8, 40, 28, 10, "sentence-internal\nunigram / bigram / trigram\ncounts", "#e3f7ea")
    box(44, 40, 24, 10, "frequency filter\nmain: f >= 3\nfailure: f >= 1", "#e3f7ea")
    box(76, 40, 30, 10, "PMI, PMI^k, NPMI\nchi-square, Yates\nt, G^2", "#e3f7ea")
    arrow(22, 58, 22, 50)
    arrow(36, 45, 44, 45)
    arrow(68, 45, 76, 45)

    box(8, 22, 30, 10, "rank\nscore desc, phrase asc", "#f3e8ff")
    box(44, 22, 28, 10, "gold list\nprecision / recall / F1\nSpearman, Jaccard", "#f3e8ff")
    box(78, 22, 28, 10, "reports/*.csv\ncharts/*.png\nqualitative notes", "#f3e8ff")
    arrow(91, 40, 91, 32)
    arrow(86, 27, 78, 27)
    arrow(44, 27, 38, 27)

    box(8, 4, 46, 12, "NLTK BigramCollocationFinder and\nTrigramCollocationFinder\napply_freq_filter, then pmi / chi_sq /\nstudent_t / likelihood_ratio\ncompared with the same candidates", "#fde8e8")
    box(60, 4, 46, 12, "Stopword ablation is off the main path.\nRemoving stopwords deletes formulas\nsuch as motion to and in term of\nand changes N and both marginals.", "#fff4d6")
    arrow(23, 40, 23, 32)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def draw_precision(path: Path, precision_rows: list[dict], metrics: list[str]) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    for metric in metrics:
        subset = [row for row in precision_rows if row["metric"] == metric]
        subset.sort(key=lambda row: row["k"])
        ax.plot(
            [row["k"] for row in subset],
            [row["precision"] for row in subset],
            marker="o",
            linewidth=1.6,
            label=DISPLAY.get(metric, metric),
        )
    ax.set_xlabel("k")
    ax.set_ylabel("Precision at k")
    ax.set_title("Precision at k on the curated bigram gold list")
    ax.set_xticks(list(KS))
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def draw_heatmap(path: Path, labels: list[str], matrix: np.ndarray, title: str, vmin: float, vmax: float, cmap: str) -> None:
    fig, ax = plt.subplots(figsize=(11.2, 9.2))
    image = ax.imshow(matrix, cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    short = [DISPLAY.get(label, label) for label in labels]
    ax.set_xticklabels(short, rotation=55, ha="right", fontsize=8)
    ax.set_yticklabels(short, fontsize=8)
    for i in range(len(labels)):
        for j in range(len(labels)):
            value = matrix[i, j]
            if isinstance(value, float) and math.isnan(value):
                text = ""
            else:
                text = f"{value:.2f}"
            color = "white" if abs(value) > (vmax * 0.65 if vmax > 0 else 0.65) else "black"
            ax.text(j, i, text, ha="center", va="center", fontsize=6.5, color=color)
    ax.set_title(title)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def draw_frequency_scatter(path: Path, rankings: dict[str, list[dict]]) -> None:
    fig, axes = plt.subplots(2, 4, figsize=(14.5, 7.6))
    for ax, metric in zip(axes.ravel(), BIGRAM_METRICS):
        rows = rankings[metric]
        top = {row["phrase"] for row in rows[:TOP_N]}
        xs_rest, ys_rest, xs_top, ys_top = [], [], [], []
        for row in rows:
            if row["phrase"] in top:
                xs_top.append(row["freq"])
                ys_top.append(row["score"])
            else:
                xs_rest.append(row["freq"])
                ys_rest.append(row["score"])
        ax.scatter(xs_rest, ys_rest, s=8, alpha=0.22, c="#4c78a8", rasterized=True, linewidths=0)
        ax.scatter(xs_top, ys_top, s=28, alpha=0.9, c="#e45756", rasterized=True, linewidths=0, label="top 20")
        ax.set_xscale("log")
        ax.set_title(DISPLAY[metric], fontsize=10)
        ax.set_xlabel("frequency")
        ax.set_ylabel("score")
        ax.grid(True, alpha=0.25)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", frameon=False)
    fig.suptitle("Unfiltered bigrams (frequency >= 1): score against frequency", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=140)
    plt.close(fig)


def build_summary(
    prepared: dict,
    counts: dict,
    gold: pd.DataFrame,
    rankings_f3: dict[str, list[dict]],
    rankings_f1: dict[str, list[dict]],
    nltk_filtered: dict,
    log_base: dict,
    spearman_labels: list[str],
    spearman_matrix: np.ndarray,
    n_common: int,
    unique_rows: list[dict],
    ablation: dict,
    trigram_stats: dict,
    gaps: dict,
) -> dict:
    gold_bi = set(gold.loc[gold["ngram"] == 2, "phrase"])
    metric_block = {}
    best_name = None
    best_f1 = -1.0
    for name in COMPARE_METRICS:
        rows = rankings_f3[name]
        stats = prf_at_k(top_phrases(rows, 50), gold_bi, 20)
        # prf_at_k uses phrases[:k], so passing 50 then k=20 is correct.
        unfiltered = rankings_f1[name]
        metric_block[name] = {
            "precision_at_20": stats["precision"],
            "recall_at_20": stats["recall"],
            "f1_at_20": stats["f1"],
            "hits_at_20": stats["hits"],
            "n_candidates_filtered": len(rows),
            "top1_phrase": rows[0]["phrase"] if rows else "",
            "top1_score": rows[0]["score"] if rows else float("nan"),
            "top20_mean_freq": mean_freq(rows),
            "top20_mean_freq_unfiltered": mean_freq(unfiltered),
            "top20_frac_freq_eq_1_unfiltered": frac_freq(unfiltered, lambda freq: freq == 1),
            "top20_frac_freq_le_3_unfiltered": frac_freq(unfiltered, lambda freq: freq <= 3),
            "spearman_score_vs_freq_filtered": spearman_score_vs_freq(rows),
            "spearman_score_vs_freq_unfiltered": spearman_score_vs_freq(unfiltered),
        }
        if name in BIGRAM_METRICS and metric_block[name]["f1_at_20"] > best_f1:
            best_f1 = metric_block[name]["f1_at_20"]
            best_name = name
    highlights = []
    for i, left in enumerate(spearman_labels):
        for j in range(i + 1, len(spearman_labels)):
            highlights.append(
                {
                    "a": left,
                    "b": spearman_labels[j],
                    "rho": float(spearman_matrix[i, j]),
                }
            )
    highlights_sorted = sorted(
        highlights,
        key=lambda item: (math.isnan(item["rho"]), item["rho"] if not math.isnan(item["rho"]) else 0),
    )
    whitespace = None
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        whitespace = int(manifest.get("total_whitespace_tokens") or sum(item["whitespace_tokens"] for item in manifest["files"]))
    return {
        "corpus": {
            "n_documents": prepared["n_documents"],
            "n_sentences": prepared["n_sentences"],
            "n_tokens": prepared["n_tokens"],
            "n_types": prepared["n_types"],
            "n_bigram_tokens": counts["n_bigrams"],
            "n_bigram_types": len(counts["bigram"]),
            "n_bigram_types_freq3": sum(1 for freq in counts["bigram"].values() if freq >= 3),
            "n_trigram_tokens": counts["n_trigrams"],
            "n_trigram_types": len(counts["trigram"]),
            "n_trigram_types_freq3": sum(1 for freq in counts["trigram"].values() if freq >= 3),
            "whitespace_tokens": whitespace,
            "source_name": "MeetingBank",
            "license": "CC BY-NC-SA 4.0",
            "retrieval_date": "2026-10-05",
            "source_url": "https://huggingface.co/datasets/huuuyeah/meetingbank",
        },
        "gold": {
            "n_bigram": int((gold["ngram"] == 2).sum()),
            "n_trigram": int((gold["ngram"] == 3).sum()),
            "n_total": int(len(gold)),
        },
        "n_convention": {
            "our_n_bigram": counts["n_bigrams"],
            "nltk_finder_N": nltk_filtered["finder_N"],
            "n_tokens": prepared["n_tokens"],
            "n_sentences": prepared["n_sentences"],
            "finder_N_minus_our_N": int(nltk_filtered["finder_N"]) - int(counts["n_bigrams"]),
        },
        "log_base": log_base,
        "metrics": metric_block,
        "best_metric": best_name,
        "best_f1": best_f1,
        "n_common_candidates": n_common,
        "spearman_lowest": highlights_sorted[:6],
        "spearman_highest": list(reversed(highlights_sorted[-6:])),
        "unique_top20": unique_rows[:12],
        "n_unique_top20": len(unique_rows),
        "finder_gaps": gaps,
        "stopword_ablation": ablation,
        "trigram": trigram_stats,
        "spearman_selected": {
            "pmi_student_t": _rho(spearman_labels, spearman_matrix, "pmi", "student_t"),
            "pmi_likelihood_ratio": _rho(spearman_labels, spearman_matrix, "pmi", "likelihood_ratio"),
            "pmi_chi_sq": _rho(spearman_labels, spearman_matrix, "pmi", "chi_sq"),
            "pmi_pmi2": _rho(spearman_labels, spearman_matrix, "pmi", "pmi2"),
            "pmi_npmi": _rho(spearman_labels, spearman_matrix, "pmi", "npmi"),
            "pmi_nltk_pmi": _rho(spearman_labels, spearman_matrix, "pmi", "nltk_pmi"),
            "chi_sq_nltk_chi_sq": _rho(spearman_labels, spearman_matrix, "chi_sq", "nltk_chi_sq"),
            "student_t_nltk_student_t": _rho(spearman_labels, spearman_matrix, "student_t", "nltk_student_t"),
            "likelihood_ratio_nltk_likelihood_ratio": _rho(
                spearman_labels, spearman_matrix, "likelihood_ratio", "nltk_likelihood_ratio"
            ),
            "chi_sq_yates": _rho(spearman_labels, spearman_matrix, "chi_sq", "chi_sq_yates"),
            "chi_sq_likelihood_ratio": _rho(
                spearman_labels, spearman_matrix, "chi_sq", "likelihood_ratio"
            ),
        },
    }


def render_reports(
    summary: dict,
    rankings_f3: dict[str, list[dict]],
    precision_rows: list[dict],
    comparison_rows_map: dict[str, list[dict]],
    spearman_labels: list[str],
    spearman_matrix: np.ndarray,
    jaccard_rows: list[dict],
    commentary: dict,
    counts: dict,
) -> None:
    gold_note = (
        f"Bigram gold size {summary['gold']['n_bigram']}. "
        f"Trigram gold size {summary['gold']['n_trigram']}."
    )
    metric_rows = []
    for name, block in summary["metrics"].items():
        metric_rows.append(
            {
                "metric": name,
                "display": DISPLAY.get(name, name),
                "gold_split": "bigram",
                "n_gold": summary["gold"]["n_bigram"],
                "precision_at_20": block["precision_at_20"],
                "recall_at_20": block["recall_at_20"],
                "f1_at_20": block["f1_at_20"],
                "hits_at_20": block["hits_at_20"],
                "n_candidates": block["n_candidates_filtered"],
                "top1_phrase": block["top1_phrase"],
                "top1_score": block["top1_score"],
                "top20_mean_freq": block["top20_mean_freq"],
            }
        )
    for name, block in summary["trigram"]["metrics"].items():
        metric_rows.append(
            {
                "metric": name,
                "display": DISPLAY.get(name, name),
                "gold_split": "trigram",
                "n_gold": summary["gold"]["n_trigram"],
                "precision_at_20": block["precision_at_20"],
                "recall_at_20": block["recall_at_20"],
                "f1_at_20": block["f1_at_20"],
                "hits_at_20": block["hits_at_20"],
                "n_candidates": block["n_candidates"],
                "top1_phrase": block["top1_phrase"],
                "top1_score": block["top1_score"],
                "top20_mean_freq": block["top20_mean_freq"],
            }
        )
    write_csv(
        REPORTS / "metric_comparison.csv",
        metric_rows,
        [
            "metric",
            "display",
            "gold_split",
            "n_gold",
            "precision_at_20",
            "recall_at_20",
            "f1_at_20",
            "hits_at_20",
            "n_candidates",
            "top1_phrase",
            "top1_score",
            "top20_mean_freq",
        ],
    )
    write_csv(
        REPORTS / "precision_at_k.csv",
        precision_rows,
        ["metric", "gold_split", "k", "hits", "precision", "recall", "f1"],
    )

    spearman_records = []
    for i, left in enumerate(spearman_labels):
        record = {"metric": left}
        for j, right in enumerate(spearman_labels):
            record[right] = float(spearman_matrix[i, j])
        spearman_records.append(record)
    write_csv(REPORTS / "rank_correlation_spearman.csv", spearman_records, ["metric"] + spearman_labels)
    write_csv(
        REPORTS / "top20_overlap_jaccard.csv",
        jaccard_rows,
        ["metric_a", "metric_b", "intersection_count", "jaccard"],
    )

    top_columns = ["rank", "phrase", "score", "freq", "f_w1", "f_w2", "o11", "o12", "o21", "o22"]
    resolved = []
    qualitative_parts = [
        "# Qualitative top-20 review",
        "",
        "Scores and counts are the filtered run (bigram or trigram frequency >= 3) unless a heading says otherwise.",
        gold_note,
        "Labels: genuine (on the gold list), acceptable (fixed or topical but not gold), junk (grammatical, lemmatized, or accidental).",
        "A missing gold hit is not by itself evidence of junk. The gold list is incomplete, so precision@20 is a lower bound.",
        "",
    ]
    unreviewed = 0
    for name in list(COMPARE_METRICS) + ["trigram_pmi"] + list(NLTK_TRIGRAM):
        rows = []
        for row in rankings_f3[name][:TOP_N]:
            enriched = enrich_counts(row, counts)
            label, text = resolve_commentary(name, enriched, commentary)
            if label == "UNREVIEWED":
                unreviewed += 1
            enriched_out = {
                "rank": enriched["rank"],
                "phrase": enriched["phrase"],
                "score": enriched["score"],
                "freq": enriched.get("freq", ""),
                "f_w1": enriched.get("f_w1", ""),
                "f_w2": enriched.get("f_w2", ""),
                "o11": enriched.get("o11", ""),
                "o12": enriched.get("o12", ""),
                "o21": enriched.get("o21", ""),
                "o22": enriched.get("o22", ""),
            }
            rows.append(enriched_out)
            resolved.append({"metric": name, "label": label, "commentary": text, **enriched_out})
        write_csv(REPORTS / f"top20_{name}.csv", rows, top_columns)
        qualitative_parts.append(f"## {DISPLAY.get(name, name)} (`{name}`)")
        qualitative_parts.append("")
        qualitative_parts.append(
            markdown_table(
                ["rank", "phrase", "score", "freq", "label", "commentary"],
                [
                    [
                        item["rank"],
                        item["phrase"],
                        f"{item['score']:.6g}",
                        item["freq"],
                        next(r["label"] for r in resolved if r["metric"] == name and r["phrase"] == item["phrase"] and r["rank"] == item["rank"]),
                        next(r["commentary"] for r in resolved if r["metric"] == name and r["phrase"] == item["phrase"] and r["rank"] == item["rank"]),
                    ]
                    for item in rows
                ],
            )
        )
        qualitative_parts.append("")

    for metric, rows in comparison_rows_map.items():
        write_csv(
            REPORTS / f"nltk_vs_scratch_{metric}.csv",
            rows,
            [
                "phrase",
                "freq",
                "scratch_score",
                "nltk_finder_score",
                "nltk_same_counts_score",
                "abs_diff_finder",
                "abs_diff_same_counts",
            ],
        )

    (REPORTS / "commentary_resolved.json").write_text(json.dumps(resolved, indent=2), encoding="utf-8")
    mapping = flat_mapping(summary)
    if summary["unique_top20"]:
        mapping["unique_phrase_1"] = summary["unique_top20"][0]["phrase"]
        mapping["unique_metric_1"] = summary["unique_top20"][0]["metric"]
        mapping["unique_freq_1"] = str(summary["unique_top20"][0]["freq"])
    failure_body = ""
    if FAILURE_PATH.exists():
        failure_body = fill_template(FAILURE_PATH.read_text(encoding="utf-8"), mapping)
    qualitative_parts.append("## Failure analysis")
    qualitative_parts.append("")
    qualitative_parts.append(failure_body.strip() or "_Failure-analysis notes have not been added yet._")
    qualitative_parts.append("")
    (REPORTS / "qualitative_top20.md").write_text("\n".join(qualitative_parts) + "\n", encoding="utf-8")

    # Numeric report. Tables are rendered from the same rows just written.
    lines = [
        "# Evaluation report",
        "",
        "Generated by `src/pipeline.py`. Figures below are the values just computed for this run.",
        "",
        "## Corpus",
        "",
        f"- Documents: {summary['corpus']['n_documents']}",
        f"- Sentences: {summary['corpus']['n_sentences']}",
        f"- Processed tokens: {summary['corpus']['n_tokens']}",
        f"- Unique lemmas: {summary['corpus']['n_types']}",
        f"- Whitespace tokens in the raw files: {summary['corpus']['whitespace_tokens']}",
        f"- Bigram tokens N: {summary['corpus']['n_bigram_tokens']}",
        f"- Bigram types: {summary['corpus']['n_bigram_types']} ({summary['corpus']['n_bigram_types_freq3']} with frequency >= 3)",
        f"- Trigram tokens: {summary['corpus']['n_trigram_tokens']}",
        f"- Trigram types: {summary['corpus']['n_trigram_types']} ({summary['corpus']['n_trigram_types_freq3']} with frequency >= 3)",
        f"- Source: {summary['corpus']['source_name']} ({summary['corpus']['license']}), retrieved {summary['corpus']['retrieval_date']}",
        "",
        "## N convention",
        "",
        f"- Our bigram N: {summary['n_convention']['our_n_bigram']}",
        f"- NLTK finder.N: {summary['n_convention']['nltk_finder_N']}",
        f"- finder.N minus our N: {summary['n_convention']['finder_N_minus_our_N']}",
        f"- Sentence count: {summary['n_convention']['n_sentences']}",
        "",
        "## Metric comparison",
        "",
        markdown_table(
            ["metric", "split", "P@20", "R@20", "F1@20", "hits", "top phrase", "mean freq of top 20"],
            [
                [
                    row["display"],
                    row["gold_split"],
                    f"{row['precision_at_20']:.4f}",
                    f"{row['recall_at_20']:.4f}",
                    f"{row['f1_at_20']:.4f}",
                    row["hits_at_20"],
                    row["top1_phrase"],
                    f"{row['top20_mean_freq']:.2f}",
                ]
                for row in metric_rows
            ],
        ),
        "",
        f"Best from-scratch bigram metric by F1@20: {DISPLAY.get(summary['best_metric'], summary['best_metric'])} ({summary['best_f1']:.4f}).",
        "",
        "## Log base and chi-square variant (identical counts)",
        "",
        f"- Median NLTK PMI / our PMI: {summary['log_base']['pmi_median_ratio_nltk_over_scratch']:.6g} (natural-log reference {summary['log_base']['pmi_reference_if_natural_log']:.6g}). Decision: {summary['log_base']['pmi_uses']}.",
        f"- Median NLTK G^2 / our G^2: {summary['log_base']['llr_median_ratio_nltk_over_scratch']:.6g} (log2 reference {summary['log_base']['llr_reference_if_log2']:.6g}). Decision: {summary['log_base']['llr_uses']}.",
        f"- Median |NLTK chi-square - our Pearson|: {summary['log_base']['chi_median_abs_diff_vs_pearson']:.6g}",
        f"- Median |NLTK chi-square - our Yates|: {summary['log_base']['chi_median_abs_diff_vs_yates']:.6g}",
        f"- NLTK chi-square matches: {summary['log_base']['chi_nltk_matches']}.",
        f"- Median |NLTK t - our t| on the same cells: {summary['log_base']['student_t_median_abs_diff']:.6g}",
        "",
        "## Spearman highlights",
        "",
        "Lowest correlations on the common filtered bigram set "
        f"({summary['n_common_candidates']} phrases):",
        "",
    ]
    for item in summary["spearman_lowest"]:
        lines.append(f"- {DISPLAY.get(item['a'], item['a'])} vs {DISPLAY.get(item['b'], item['b'])}: {item['rho']:.4f}")
    lines.append("")
    lines.append("Highest correlations:")
    lines.append("")
    for item in summary["spearman_highest"]:
        lines.append(f"- {DISPLAY.get(item['a'], item['a'])} vs {DISPLAY.get(item['b'], item['b'])}: {item['rho']:.4f}")
    lines.extend(["", "## Stopword ablation", ""])
    ablation = summary["stopword_ablation"]
    for key, value in ablation.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Phrases in exactly one from-scratch top-20", ""])
    if summary["unique_top20"]:
        for item in summary["unique_top20"]:
            lines.append(
                f"- {item['phrase']} ({DISPLAY.get(item['metric'], item['metric'])}), frequency {item['freq']}, score {item['score']:.6g}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Failure analysis", "", failure_body.strip(), ""])
    (REPORTS / "evaluation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return unreviewed


def print_summary(summary: dict) -> None:
    corpus = summary["corpus"]
    print(
        f"Corpus: {corpus['n_documents']} documents, {corpus['n_sentences']} sentences, "
        f"{corpus['n_tokens']} tokens, {corpus['n_types']} unique lemmas"
    )
    print(
        f"Bigram types: {corpus['n_bigram_types']} "
        f"({corpus['n_bigram_types_freq3']} with frequency >= 3); "
        f"trigram types: {corpus['n_trigram_types']} "
        f"({corpus['n_trigram_types_freq3']} with frequency >= 3)"
    )
    print(
        f"N_bigram = {summary['n_convention']['our_n_bigram']}; "
        f"NLTK finder.N = {summary['n_convention']['nltk_finder_N']}"
    )
    print()
    print(f"{'metric':<28} {'P@20':>8} {'R@20':>8} {'F1@20':>8} {'hits':>6}")
    for name, block in summary["metrics"].items():
        print(
            f"{DISPLAY[name]:<28} {block['precision_at_20']:8.3f} "
            f"{block['recall_at_20']:8.3f} {block['f1_at_20']:8.3f} {block['hits_at_20']:6d}"
        )
    print()
    print(
        f"Best from-scratch bigram metric by F1@20: "
        f"{DISPLAY.get(summary['best_metric'], summary['best_metric'])} "
        f"({summary['best_f1']:.3f})"
    )
    print("Spearman correlations (filtered common set), lowest then highest:")
    for item in summary["spearman_lowest"][:4]:
        print(f"  {item['rho']:+.3f}  {DISPLAY.get(item['a'], item['a'])} vs {DISPLAY.get(item['b'], item['b'])}")
    for item in summary["spearman_highest"][:4]:
        print(f"  {item['rho']:+.3f}  {DISPLAY.get(item['a'], item['a'])} vs {DISPLAY.get(item['b'], item['b'])}")
    print(
        f"NLTK PMI log base: {summary['log_base']['pmi_uses']} "
        f"(median ratio {summary['log_base']['pmi_median_ratio_nltk_over_scratch']:.4f}); "
        f"NLTK G^2 log base: {summary['log_base']['llr_uses']} "
        f"(median ratio {summary['log_base']['llr_median_ratio_nltk_over_scratch']:.4f}); "
        f"NLTK chi-square: {summary['log_base']['chi_nltk_matches']}"
    )


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    random.seed(0)
    np.random.seed(0)
    REPORTS.mkdir(parents=True, exist_ok=True)
    CHARTS.mkdir(parents=True, exist_ok=True)

    prepared = preprocess_corpus(drop_stopwords=False)
    counts = build_counts(prepared["sentences"])
    gold = load_gold()
    check_gold_frequencies(gold, counts)
    gold_bi = set(gold.loc[gold["ngram"] == 2, "phrase"])
    gold_tri = set(gold.loc[gold["ngram"] == 3, "phrase"])

    rankings_f3: dict[str, list[dict]] = {}
    rankings_f1: dict[str, list[dict]] = {}
    for metric in BIGRAM_METRICS:
        rankings_f3[metric] = rank_metric(metric, counts, min_freq=3)
        rankings_f1[metric] = rank_metric(metric, counts, min_freq=1)

    nltk_filtered = nltk_bigram_rankings(prepared["sentences"], min_freq=3)
    nltk_open = nltk_bigram_rankings(prepared["sentences"], min_freq=1)
    rankings_f3.update(nltk_filtered["rankings"])
    rankings_f1.update(nltk_open["rankings"])

    rankings_f3["trigram_pmi"] = rank_trigram_pmi(counts, min_freq=3)
    rankings_f1["trigram_pmi"] = rank_trigram_pmi(counts, min_freq=1)
    nltk_tri_f3 = nltk_trigram_rankings(prepared["sentences"], min_freq=3)
    nltk_tri_f1 = nltk_trigram_rankings(prepared["sentences"], min_freq=1)
    rankings_f3.update(nltk_tri_f3["rankings"])
    rankings_f1.update(nltk_tri_f1["rankings"])

    precision_rows = []
    for name in COMPARE_METRICS:
        phrases = top_phrases(rankings_f3[name], max(KS))
        for k in KS:
            stats = prf_at_k(phrases, gold_bi, k)
            precision_rows.append({"metric": name, "gold_split": "bigram", **stats})
    trigram_metric_names = ["trigram_pmi", *NLTK_TRIGRAM]
    trigram_metrics_summary = {}
    for name in trigram_metric_names:
        phrases = top_phrases(rankings_f3[name], max(KS))
        for k in KS:
            stats = prf_at_k(phrases, gold_tri, k)
            precision_rows.append({"metric": name, "gold_split": "trigram", **stats})
        at_20 = prf_at_k(phrases, gold_tri, 20)
        rows = rankings_f3[name]
        trigram_metrics_summary[name] = {
            "precision_at_20": at_20["precision"],
            "recall_at_20": at_20["recall"],
            "f1_at_20": at_20["f1"],
            "hits_at_20": at_20["hits"],
            "n_candidates": len(rows),
            "top1_phrase": rows[0]["phrase"] if rows else "",
            "top1_score": rows[0]["score"] if rows else float("nan"),
            "top20_mean_freq": mean_freq(rows),
            "top20_mean_freq_unfiltered": mean_freq(rankings_f1[name]),
            "top20_frac_freq_eq_1_unfiltered": frac_freq(rankings_f1[name], lambda freq: freq == 1),
        }

    spearman_matrix, n_common = pairwise_spearman(rankings_f3, COMPARE_METRICS)
    spearman_labels = list(COMPARE_METRICS)
    jaccard_rows = []
    jaccard_matrix = np.eye(len(COMPARE_METRICS))
    for i, left in enumerate(COMPARE_METRICS):
        for j, right in enumerate(COMPARE_METRICS):
            inter, score = jaccard_top(top_phrases(rankings_f3[left]), top_phrases(rankings_f3[right]))
            jaccard_matrix[i, j] = score
            if j >= i:
                jaccard_rows.append(
                    {
                        "metric_a": left,
                        "metric_b": right,
                        "intersection_count": inter,
                        "jaccard": score,
                    }
                )

    same_counts = nltk_same_count_table(counts, min_freq=3)
    log_base = log_base_summary(rankings_f3, same_counts)
    comparison_map = {}
    gaps = {}
    for metric, nltk_name in SCRATCH_TO_NLTK.items():
        rows = comparison_rows(metric, rankings_f3[metric], rankings_f3[nltk_name], same_counts)
        comparison_map[metric] = rows
        gaps[metric] = largest_finder_gap(rows)

    # Trigram PMI finder comparison (no same-count reconstruction).
    tri_finder = index_rankings(rankings_f3["nltk_trigram_pmi"])
    tri_rows = []
    for row in rankings_f3["trigram_pmi"]:
        found = tri_finder.get(row["phrase"])
        finder_score = found["score"] if found else float("nan")
        tri_rows.append(
            {
                "phrase": row["phrase"],
                "freq": row["freq"],
                "scratch_score": row["score"],
                "nltk_finder_score": finder_score,
                "nltk_same_counts_score": float("nan"),
                "abs_diff_finder": abs(row["score"] - finder_score) if found else float("nan"),
                "abs_diff_same_counts": float("nan"),
            }
        )
    comparison_map["trigram_pmi"] = tri_rows

    stops = stopword_set()
    gold_with_stop = sorted(phrase for phrase in gold_bi if any(part in stops for part in phrase.split()))
    ablated = preprocess_corpus(drop_stopwords=True)
    ablated_counts = build_counts(ablated["sentences"])
    ablation = {
        "n_tokens_without_stopwords": ablated["n_tokens"],
        "n_bigram_tokens_without_stopwords": ablated_counts["n_bigrams"],
        "gold_bigrams_containing_a_stopword": len(gold_with_stop),
        "gold_bigrams_blocked_examples": ", ".join(gold_with_stop[:12]),
    }
    for metric in ("pmi", "student_t", "likelihood_ratio", "chi_sq"):
        ranked = rank_metric(metric, ablated_counts, min_freq=3)
        stats = prf_at_k(top_phrases(ranked), gold_bi, 20)
        ablation[f"{metric}_precision_at_20"] = round(stats["precision"], 6)
        ablation[f"{metric}_recall_at_20"] = round(stats["recall"], 6)
        ablation[f"{metric}_f1_at_20"] = round(stats["f1"], 6)
        ablation[f"{metric}_hits_at_20"] = stats["hits"]

    unique_rows = unique_top_phrases(rankings_f3, list(BIGRAM_METRICS))
    summary = build_summary(
        prepared,
        counts,
        gold,
        rankings_f3,
        rankings_f1,
        nltk_filtered,
        log_base,
        spearman_labels,
        spearman_matrix,
        n_common,
        unique_rows,
        ablation,
        {"metrics": trigram_metrics_summary, "nltk_finder_N": nltk_tri_f3["finder_N"]},
        gaps,
    )
    # JSON cannot store NaN. Convert via a round trip that preserves None.
    def _clean(value):
        if isinstance(value, dict):
            return {key: _clean(child) for key, child in value.items()}
        if isinstance(value, list):
            return [_clean(child) for child in value]
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        if isinstance(value, (np.floating,)):
            number = float(value)
            return None if math.isnan(number) or math.isinf(number) else number
        if isinstance(value, (np.integer,)):
            return int(value)
        return value

    summary = _clean(summary)
    (REPORTS / "summary_stats.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (REPORTS / "worked_example.json").write_text(
        json.dumps(_clean(worked_example()), indent=2),
        encoding="utf-8",
    )
    (REPORTS / "nltk_convention.json").write_text(
        json.dumps(_clean({"n_convention": summary["n_convention"], "log_base": summary["log_base"], "finder_gaps": gaps}), indent=2),
        encoding="utf-8",
    )

    unfiltered_columns = ["rank", "phrase", "score", "freq"]
    for name in list(BIGRAM_METRICS) + ["trigram_pmi"]:
        write_csv(
            REPORTS / f"top20_unfiltered_{name}.csv",
            [
                {"rank": row["rank"], "phrase": row["phrase"], "score": row["score"], "freq": row["freq"]}
                for row in rankings_f1[name][:TOP_N]
            ],
            unfiltered_columns,
        )

    commentary = commentary_for_rankings(
        rankings_f3,
        list(COMPARE_METRICS) + ["trigram_pmi"] + list(NLTK_TRIGRAM),
    )
    unreviewed = render_reports(
        summary,
        rankings_f3,
        precision_rows,
        comparison_map,
        spearman_labels,
        spearman_matrix,
        jaccard_rows,
        commentary,
        counts,
    )

    draw_architecture(CHARTS / "architecture.png")
    draw_precision(CHARTS / "precision_at_k.png", precision_rows, COMPARE_METRICS)
    draw_heatmap(
        CHARTS / "spearman_heatmap.png",
        COMPARE_METRICS,
        spearman_matrix,
        f"Spearman rank correlation on {n_common} shared bigrams (frequency >= 3)",
        vmin=-1,
        vmax=1,
        cmap="coolwarm",
    )
    draw_heatmap(
        CHARTS / "top20_jaccard_heatmap.png",
        COMPARE_METRICS,
        jaccard_matrix,
        "Jaccard overlap of top-20 bigrams (frequency >= 3)",
        vmin=0,
        vmax=1,
        cmap="YlGnBu",
    )
    draw_frequency_scatter(CHARTS / "frequency_vs_score.png", rankings_f1)
    update_provenance(prepared["n_tokens"], prepared["n_sentences"], prepared["n_types"])
    print_summary(summary)
    if unreviewed:
        print(f"Commentary entries still UNREVIEWED: {unreviewed}")
    if "--docs" in argv:
        script = ROOT / "scripts" / "build_docs.py"
        spec = importlib.util.spec_from_file_location("build_docs", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.main()


if __name__ == "__main__":
    main()
