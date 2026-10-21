"""Association measures for collocation mining, from first principles.

NLTK is not used for these formulas. NLTK's finder and association
functions are wrapped separately so the two implementations can be compared
on identical candidates.

N convention
    For bigrams, N is the number of sentence-internal bigram tokens, not the
    number of word tokens. A sentence of length L contributes L tokens and
    L-1 bigrams; bigrams never cross sentence boundaries.

    f(w1, w2) is the bigram count.
    f(w1) in the contingency table is the number of bigrams whose first word
    is w1 (a left marginal), not the raw unigram count.
    f(w2) is the number of bigrams whose second word is w2 (a right marginal).

    These marginals are required so the four cells sum to N. Using raw
    unigram counts would include a sentence-final token that never occupies
    the first slot of a bigram, and the bottom-right cell could go negative.

    For trigrams, N is the number of sentence-internal trigram tokens.
    Position-specific marginals are the number of trigrams with that word in
    the first, middle, or last slot.

Contingency table (bigrams)
    O11 = f(w1, w2)
    O12 = f(w1) - O11          w1 followed by something other than w2
    O21 = f(w2) - O11          w2 preceded by something other than w1
    O22 = N - O11 - O12 - O21  neither

    Row and column sums:
    R1 = O11 + O12 = f(w1),  R2 = O21 + O22
    C1 = O11 + O21 = f(w2),  C2 = O12 + O22

Maximum-likelihood probabilities
    P(w1, w2) = O11 / N
    P(w1) = R1 / N
    P(w2) = C1 / N

Pointwise mutual information
    PMI(w1, w2) = log2( P(w1, w2) / (P(w1) P(w2)) )
                = log2( O11 * N / (R1 * C1) )

Normalized PMI
    NPMI(w1, w2) = PMI(w1, w2) / (-log2 P(w1, w2))
    Undefined when P(w1, w2) is 0 or 1 (the denominator vanishes).

PMI to a power
    PMI^k = (log2( P(w1, w2) / (P(w1) P(w2)) ))^k
    implemented as PMI ** k for k = 2 and k = 3.
    Even k maps strong negative PMI onto a large positive score, so PMI^2
    ranks anti-collocations with true collocations. Odd k keeps the sign.

Chi-square (Pearson's, no continuity correction)
    chi2 = N * (O11*O22 - O12*O21)^2
           / ((O11+O12) * (O11+O21) * (O12+O22) * (O21+O22))
    Chi-square is non-directional. It detects dependence, not whether the
    pair co-occurs more often than chance. It does not penalise
    high-frequency pairs the way PMI does: a large count makes the same
    relative dependence produce a larger statistic. Undefined when any
    marginal sum is 0.

Yates correction
    chi2_Y = N * (max(0, |O11*O22 - O12*O21| - N/2))^2
             / ((O11+O12) * (O11+O21) * (O12+O22) * (O21+O22))
    The same denominator as chi-square. The correction subtracts N/2 inside
    the absolute deviation and floors at 0, which is severe on small N and
    can zero out a real association.

Student's t (collocation form)
    Manning and Schütze (1999), equation 5.10:
        t = ( f(w1, w2) - f(w1) f(w2) / N ) / sqrt( f(w1, w2) )
    The denominator treats the count as Poisson, so variance equals the mean,
    and the mean is estimated by the observed bigram count.

    This is the general one-sample t statistic
        t = (x_bar - mu) / sqrt(s^2 / n)
    with n = N, x_bar = O11 / N, mu = P(w1) P(w2) = R1 * C1 / N^2,
    and s^2 = x_bar (the Poisson variance-equals-mean assumption).
    Algebra:
        (O11/N - R1*C1/N^2) / sqrt( (O11/N) / N )
        = (O11 - R1*C1/N) / sqrt(O11)

    Manning and Schütze note that the normality assumption behind the t
    test is not strictly satisfied by count data. The statistic is still
    used as a ranking score. It is directional (negative when the pair
    occurs less often than independence) and it grows with frequency, so
    common grammatical pairs outrank rare domain terms.

Log-likelihood ratio
    Dunning (1993):
        G^2 = 2 * sum_ij  O_ij * ln(O_ij / E_ij)
    with expected counts E_ij = (row_i * col_j) / N under independence.
    The convention 0 * ln(0) = 0 is used when O_ij = 0. The statistic is
    undefined if some O_ij > 0 while E_ij = 0.

    Expanded 2x2 form, writing L(o, e) = o * ln(o / e) if o > 0 else 0:
        G^2 = 2 * ( L(O11, E11) + L(O12, E12) + L(O21, E21) + L(O22, E22) )
        E11 = R1 * C1 / N,  E12 = R1 * C2 / N
        E21 = R2 * C1 / N,  E22 = R2 * C2 / N

    G^2 is asymptotically chi-square distributed with the same degrees of
    freedom as Pearson's chi-square (1, for a 2x2 table with fixed
    margins). It is better behaved than Pearson's chi-square at the low
    counts that dominate voice memos. Like chi-square, the score is
    non-directional: large G^2 means dependence, not specifically attraction.

Trigram PMI
    PMI(w1, w2, w3) = log2( P(w1 w2 w3) / (P(w1) P(w2) P(w3)) )
                    = log2( f(w1 w2 w3) * N^2 / (f1 * f2 * f3) )
    where each fi is the position-specific trigram marginal and N is the
    trigram token count.

Tie-breaking
    Rankings sort by score descending, then by the phrase string ascending.
    That order is a pure function of the counts.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

import numpy as np

# Floor used only to decide that a probability is 1 (NPMI denominator ~ 0).
_PROB_ONE = 1.0 - 1e-15


@dataclass(frozen=True)
class Contingency:
    """2x2 co-occurrence table. Cells are counts; ``n`` is the bigram token count."""

    o11: float
    o12: float
    o21: float
    o22: float
    n: float

    @property
    def row1(self) -> float:
        return self.o11 + self.o12

    @property
    def row2(self) -> float:
        return self.o21 + self.o22

    @property
    def col1(self) -> float:
        return self.o11 + self.o21

    @property
    def col2(self) -> float:
        return self.o12 + self.o22

    def as_array(self) -> np.ndarray:
        return np.array([self.o11, self.o12, self.o21, self.o22], dtype=float)

    def marginals_ok(self) -> bool:
        return (
            self.n > 0
            and self.row1 > 0
            and self.row2 > 0
            and self.col1 > 0
            and self.col2 > 0
        )


def build_counts(sentences: list[list[str]]) -> dict:
    """Unigram, bigram, and trigram counts over sentence-internal n-grams."""
    unigram: Counter[str] = Counter()
    bigram: Counter[tuple[str, str]] = Counter()
    trigram: Counter[tuple[str, str, str]] = Counter()
    left: Counter[str] = Counter()
    right: Counter[str] = Counter()
    tri_left: Counter[str] = Counter()
    tri_mid: Counter[str] = Counter()
    tri_right: Counter[str] = Counter()
    for sent in sentences:
        unigram.update(sent)
        for a, b in zip(sent, sent[1:]):
            bigram[(a, b)] += 1
            left[a] += 1
            right[b] += 1
        for a, b, c in zip(sent, sent[1:], sent[2:]):
            trigram[(a, b, c)] += 1
            tri_left[a] += 1
            tri_mid[b] += 1
            tri_right[c] += 1
    return {
        "unigram": unigram,
        "bigram": bigram,
        "trigram": trigram,
        "left": left,
        "right": right,
        "tri_left": tri_left,
        "tri_mid": tri_mid,
        "tri_right": tri_right,
        "n_tokens": int(sum(unigram.values())),
        "n_bigrams": int(sum(bigram.values())),
        "n_trigrams": int(sum(trigram.values())),
    }


def contingency_bigram(w1: str, w2: str, counts: dict) -> Contingency:
    """Shared table used by every bigram metric."""
    o11 = float(counts["bigram"][(w1, w2)])
    f1 = float(counts["left"][w1])
    f2 = float(counts["right"][w2])
    n = float(counts["n_bigrams"])
    o12 = f1 - o11
    o21 = f2 - o11
    o22 = n - o11 - o12 - o21
    return Contingency(o11, o12, o21, o22, n)


def pmi(ct: Contingency) -> float | None:
    """PMI(w1, w2) = log2( P(w1, w2) / (P(w1) P(w2)) )."""
    if ct.o11 <= 0 or ct.row1 <= 0 or ct.col1 <= 0 or ct.n <= 0:
        return None
    ratio = (ct.o11 * ct.n) / (ct.row1 * ct.col1)
    if ratio <= 0:
        return None
    return float(math.log2(ratio))


def npmi(ct: Contingency) -> float | None:
    """NPMI = PMI / (-log2 P(w1, w2))."""
    value = pmi(ct)
    if value is None or ct.n <= 0 or ct.o11 <= 0:
        return None
    p_joint = ct.o11 / ct.n
    if p_joint <= 0 or p_joint >= _PROB_ONE:
        return None
    denom = -math.log2(p_joint)
    if denom == 0:
        return None
    return float(value / denom)


def pmi_power(ct: Contingency, k: int) -> float | None:
    """PMI^k implemented as PMI ** k."""
    value = pmi(ct)
    if value is None:
        return None
    return float(value**k)


def _chi_denominator(ct: Contingency) -> float | None:
    den = ct.row1 * ct.col1 * ct.col2 * ct.row2
    if den <= 0 or ct.n <= 0:
        return None
    return float(den)


def chi_square(ct: Contingency) -> float | None:
    """Pearson's chi-square on the 2x2 table. Non-directional."""
    den = _chi_denominator(ct)
    if den is None:
        return None
    observed = np.array([ct.o11, ct.o12, ct.o21, ct.o22], dtype=float)
    # Cross-product form is algebraically the Pearson statistic.
    cross = observed[0] * observed[3] - observed[1] * observed[2]
    return float(ct.n * (cross**2) / den)


def chi_square_yates(ct: Contingency) -> float | None:
    """Yates-corrected chi-square. Same denominator; continuity correction on the deviation."""
    den = _chi_denominator(ct)
    if den is None:
        return None
    observed = np.array([ct.o11, ct.o12, ct.o21, ct.o22], dtype=float)
    cross = abs(float(observed[0] * observed[3] - observed[1] * observed[2]))
    corrected = max(0.0, cross - ct.n / 2.0)
    return float(ct.n * (corrected**2) / den)


def student_t(ct: Contingency) -> float | None:
    """Manning and Schütze (1999) eq. 5.10 collocation t statistic."""
    if ct.o11 <= 0 or ct.n <= 0:
        return None
    expected = (ct.row1 * ct.col1) / ct.n
    return float((ct.o11 - expected) / math.sqrt(ct.o11))


def student_t_general(xbar: float, mu: float, s2: float, n: float) -> float | None:
    """General one-sample t = (x_bar - mu) / sqrt(s^2 / n).

    The collocation form sets s^2 = x_bar (Poisson variance = mean) and n = N.
    """
    if n <= 0 or s2 < 0:
        return None
    if s2 == 0:
        return None
    return float((xbar - mu) / math.sqrt(s2 / n))


def _ll_term(observed: float, expected: float) -> float | None:
    if observed < 0 or expected < 0:
        return None
    if observed == 0:
        return 0.0
    if expected == 0:
        return None
    return float(observed * math.log(observed / expected))


def likelihood_ratio(ct: Contingency) -> float | None:
    """Dunning (1993) G^2 = 2 * sum O_ij * ln(O_ij / E_ij)."""
    if ct.n <= 0 or not ct.marginals_ok():
        return None
    rows = np.array([ct.row1, ct.row2], dtype=float)
    cols = np.array([ct.col1, ct.col2], dtype=float)
    observed = ct.as_array().reshape(2, 2)
    expected = np.outer(rows, cols) / ct.n
    total = 0.0
    for obs, exp in zip(observed.ravel(), expected.ravel()):
        term = _ll_term(float(obs), float(exp))
        if term is None:
            return None
        total += term
    return float(2.0 * total)


def trigram_pmi(w1: str, w2: str, w3: str, counts: dict) -> float | None:
    """PMI(w1, w2, w3) = log2( f123 * N^2 / (f1 * f2 * f3) )."""
    n = float(counts["n_trigrams"])
    f123 = float(counts["trigram"][(w1, w2, w3)])
    f1 = float(counts["tri_left"][w1])
    f2 = float(counts["tri_mid"][w2])
    f3 = float(counts["tri_right"][w3])
    if f123 <= 0 or f1 <= 0 or f2 <= 0 or f3 <= 0 or n <= 0:
        return None
    ratio = (f123 * n * n) / (f1 * f2 * f3)
    if ratio <= 0:
        return None
    return float(math.log2(ratio))


BIGRAM_METRICS = (
    "pmi",
    "pmi2",
    "pmi3",
    "npmi",
    "chi_sq",
    "chi_sq_yates",
    "student_t",
    "likelihood_ratio",
)


def score_bigram(ct: Contingency) -> dict[str, float | None]:
    return {
        "pmi": pmi(ct),
        "pmi2": pmi_power(ct, 2),
        "pmi3": pmi_power(ct, 3),
        "npmi": npmi(ct),
        "chi_sq": chi_square(ct),
        "chi_sq_yates": chi_square_yates(ct),
        "student_t": student_t(ct),
        "likelihood_ratio": likelihood_ratio(ct),
    }


def phrase_of(ngram: tuple[str, ...]) -> str:
    return " ".join(ngram)


def sort_scored(rows: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Deterministic ranking: score descending, phrase ascending."""
    return sorted(rows, key=lambda item: (-item[1], item[0]))


def rank_metric(
    metric: str,
    counts: dict,
    min_freq: int,
) -> list[dict]:
    """Score every bigram at or above ``min_freq`` and rank it."""
    ranked_input: list[tuple[str, float, tuple[str, str], Contingency]] = []
    for (w1, w2), freq in counts["bigram"].items():
        if freq < min_freq:
            continue
        ct = contingency_bigram(w1, w2, counts)
        value = score_bigram(ct)[metric]
        if value is None or isinstance(value, float) and math.isnan(value):
            continue
        ranked_input.append((phrase_of((w1, w2)), float(value), (w1, w2), ct))
    ranked_input.sort(key=lambda item: (-item[1], item[0]))
    rows = []
    for rank, (phrase, value, (w1, w2), ct) in enumerate(ranked_input, start=1):
        rows.append(
            {
                "rank": rank,
                "phrase": phrase,
                "w1": w1,
                "w2": w2,
                "score": value,
                "freq": int(ct.o11),
                "f_w1": int(ct.row1),
                "f_w2": int(ct.col1),
                "o11": int(ct.o11),
                "o12": int(ct.o12),
                "o21": int(ct.o21),
                "o22": int(ct.o22),
                "n": int(ct.n),
            }
        )
    return rows


def rank_trigram_pmi(counts: dict, min_freq: int) -> list[dict]:
    rows_in = []
    for (w1, w2, w3), freq in counts["trigram"].items():
        if freq < min_freq:
            continue
        value = trigram_pmi(w1, w2, w3, counts)
        if value is None:
            continue
        rows_in.append((phrase_of((w1, w2, w3)), float(value), freq, w1, w2, w3))
    rows_in.sort(key=lambda item: (-item[1], item[0]))
    return [
        {
            "rank": rank,
            "phrase": phrase,
            "score": value,
            "freq": int(freq),
            "w1": w1,
            "w2": w2,
            "w3": w3,
        }
        for rank, (phrase, value, freq, w1, w2, w3) in enumerate(rows_in, start=1)
    ]


def nltk_scores_same_counts(o11: float, f1: float, f2: float, n: float) -> dict[str, float]:
    """Call NLTK's association functions on one explicit contingency.

    ``f1`` and ``f2`` are whatever marginals the caller supplies. Passing our
    left/right marginals and our N isolates log base, Yates, and the _SMALL
    smoother from the finder.N convention.
    """
    from nltk.collocations import BigramAssocMeasures

    measures = BigramAssocMeasures()
    marginals = (o11, (f1, f2), n)
    return {
        "pmi": float(measures.pmi(*marginals)),
        "chi_sq": float(measures.chi_sq(*marginals)),
        "student_t": float(measures.student_t(*marginals)),
        "likelihood_ratio": float(measures.likelihood_ratio(*marginals)),
    }


def nltk_bigram_rankings(sentences: list[list[str]], min_freq: int) -> dict:
    """Rank bigrams with BigramCollocationFinder and BigramAssocMeasures.

    ``apply_freq_filter`` is applied when ``min_freq`` > 1. ``finder.N`` is
    returned unchanged so the caller can compare it with our bigram N.
    """
    from nltk.collocations import BigramAssocMeasures, BigramCollocationFinder

    finder = BigramCollocationFinder.from_documents(sentences)
    nltk_n = int(finder.N)
    if min_freq > 1:
        finder.apply_freq_filter(min_freq)
    measures = BigramAssocMeasures()
    metric_fns = {
        "nltk_pmi": measures.pmi,
        "nltk_chi_sq": measures.chi_sq,
        "nltk_student_t": measures.student_t,
        "nltk_likelihood_ratio": measures.likelihood_ratio,
    }
    rankings = {}
    for name, fn in metric_fns.items():
        scored = []
        for ngram, score in finder.score_ngrams(fn):
            if score is None or (isinstance(score, float) and math.isnan(score)):
                continue
            scored.append((phrase_of(ngram), float(score), int(finder.ngram_fd[ngram])))
        # NLTK already sorts by (-score, ngram). Re-sort with our string key
        # so a tie on score uses the joined phrase, matching our rule.
        scored.sort(key=lambda item: (-item[1], item[0]))
        rankings[name] = [
            {"rank": i, "phrase": phrase, "score": score, "freq": freq}
            for i, (phrase, score, freq) in enumerate(scored, start=1)
        ]
    return {"finder_N": nltk_n, "rankings": rankings, "n_candidates": len(finder.ngram_fd)}


def nltk_trigram_rankings(sentences: list[list[str]], min_freq: int) -> dict:
    """TrigramCollocationFinder with PMI, chi-square, t, and likelihood ratio."""
    from nltk.collocations import TrigramAssocMeasures, TrigramCollocationFinder

    finder = TrigramCollocationFinder.from_documents(sentences)
    nltk_n = int(finder.N)
    if min_freq > 1:
        finder.apply_freq_filter(min_freq)
    measures = TrigramAssocMeasures()
    metric_fns = {
        "nltk_trigram_pmi": measures.pmi,
        "nltk_trigram_chi_sq": measures.chi_sq,
        "nltk_trigram_student_t": measures.student_t,
        "nltk_trigram_likelihood_ratio": measures.likelihood_ratio,
    }
    rankings = {}
    for name, fn in metric_fns.items():
        scored = []
        for ngram, score in finder.score_ngrams(fn):
            if score is None or (isinstance(score, float) and math.isnan(score)):
                continue
            scored.append((phrase_of(ngram), float(score), int(finder.ngram_fd[ngram])))
        scored.sort(key=lambda item: (-item[1], item[0]))
        rankings[name] = [
            {"rank": i, "phrase": phrase, "score": score, "freq": freq}
            for i, (phrase, score, freq) in enumerate(scored, start=1)
        ]
    return {"finder_N": nltk_n, "rankings": rankings, "n_candidates": len(finder.ngram_fd)}


def worked_example() -> dict:
    """Fully worked toy table. Every printed number is computed here."""
    tokens = ["city", "council", "city", "council", "budget"]
    counts = build_counts([tokens])
    pair = ("city", "council")
    ct = contingency_bigram(*pair, counts)
    scores = score_bigram(ct)
    xbar = ct.o11 / ct.n
    mu = (ct.row1 / ct.n) * (ct.col1 / ct.n)
    general_t = student_t_general(xbar, mu, xbar, ct.n)
    nltk_same = nltk_scores_same_counts(ct.o11, ct.row1, ct.col1, ct.n)
    nltk_finder = nltk_bigram_rankings([tokens], min_freq=1)
    nltk_city = next(
        row for row in nltk_finder["rankings"]["nltk_pmi"] if row["phrase"] == "city council"
    )
    all_pairs = []
    for (w1, w2), freq in sorted(counts["bigram"].items(), key=lambda kv: phrase_of(kv[0])):
        table = contingency_bigram(w1, w2, counts)
        all_pairs.append(
            {
                "phrase": phrase_of((w1, w2)),
                "freq": int(freq),
                **{key: score_bigram(table)[key] for key in BIGRAM_METRICS},
            }
        )
    p_joint = ct.o11 / ct.n
    p1 = ct.row1 / ct.n
    p2 = ct.col1 / ct.n
    e11 = ct.row1 * ct.col1 / ct.n
    e12 = ct.row1 * ct.col2 / ct.n
    e21 = ct.row2 * ct.col1 / ct.n
    e22 = ct.row2 * ct.col2 / ct.n
    cross = ct.o11 * ct.o22 - ct.o12 * ct.o21
    den = ct.row1 * ct.col1 * ct.col2 * ct.row2
    return {
        "sentence": " ".join(tokens),
        "tokens": tokens,
        "n_tokens": counts["n_tokens"],
        "n_bigrams": counts["n_bigrams"],
        "n_convention": (
            "N is the bigram token count (4). "
            "The sentence has 5 word tokens, so N_tokens - N_bigrams = 1, "
            "the sentence-final word that does not start a bigram."
        ),
        "pair": "city council",
        "o11": ct.o11,
        "o12": ct.o12,
        "o21": ct.o21,
        "o22": ct.o22,
        "f_w1": ct.row1,
        "f_w2": ct.col1,
        "p_joint": p_joint,
        "p_w1": p1,
        "p_w2": p2,
        "expected": {"e11": e11, "e12": e12, "e21": e21, "e22": e22},
        "cross_product": cross,
        "chi_denominator": den,
        "student_t_general": general_t,
        "student_t_xbar": xbar,
        "student_t_mu": mu,
        "scores": scores,
        "nltk_same_counts": nltk_same,
        "nltk_finder_N": nltk_finder["finder_N"],
        "nltk_finder_pmi_city_council": nltk_city["score"],
        "all_pairs": all_pairs,
    }
