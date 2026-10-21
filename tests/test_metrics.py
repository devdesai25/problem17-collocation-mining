"""Hand-checked association measures on a toy corpus.

Oracle values below were derived from the formulas in models.py, not by
calling the functions under test. The arithmetic is written next to each
assertion.
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from models import (  # noqa: E402
    Contingency,
    build_counts,
    chi_square,
    chi_square_yates,
    contingency_bigram,
    likelihood_ratio,
    nltk_bigram_rankings,
    nltk_scores_same_counts,
    npmi,
    pmi,
    pmi_power,
    score_bigram,
    sort_scored,
    student_t,
    student_t_general,
)


class ToyCountTests(unittest.TestCase):
    def test_city_council_table(self):
        # tokens: city council city council budget
        # bigrams (N = 4): (city, council)=2, (council, city)=1, (council, budget)=1
        # left(city)=2, right(council)=2
        # O11=2, O12=0, O21=0, O22=2
        counts = build_counts([["city", "council", "city", "council", "budget"]])
        self.assertEqual(counts["n_tokens"], 5)
        self.assertEqual(counts["n_bigrams"], 4)
        ct = contingency_bigram("city", "council", counts)
        self.assertEqual((ct.o11, ct.o12, ct.o21, ct.o22, ct.n), (2, 0, 0, 2, 4))

        # PMI = log2( (2/4) / ((2/4)*(2/4)) ) = log2(2) = 1
        self.assertAlmostEqual(pmi(ct), 1.0, places=12)
        # NPMI = 1 / -log2(2/4) = 1
        self.assertAlmostEqual(npmi(ct), 1.0, places=12)
        self.assertAlmostEqual(pmi_power(ct, 2), 1.0, places=12)
        self.assertAlmostEqual(pmi_power(ct, 3), 1.0, places=12)

        # chi2 = 4 * (2*2 - 0*0)^2 / (2*2*2*2) = 64/16 = 4
        self.assertAlmostEqual(chi_square(ct), 4.0, places=12)
        # Yates: |4| - 4/2 = 2; 4 * 4 / 16 = 1
        self.assertAlmostEqual(chi_square_yates(ct), 1.0, places=12)

        # t = (2 - 2*2/4) / sqrt(2) = 1/sqrt(2)
        self.assertAlmostEqual(student_t(ct), 1.0 / math.sqrt(2), places=12)
        xbar = 2 / 4
        mu = (2 / 4) * (2 / 4)
        general = student_t_general(xbar, mu, xbar, 4)
        self.assertAlmostEqual(general, student_t(ct), places=12)

        # Eij = 1 for every cell; G^2 = 2 * (2 ln 2 + 2 ln 2) = 8 ln 2
        self.assertAlmostEqual(likelihood_ratio(ct), 8.0 * math.log(2), places=12)

    def test_negative_pmi_and_even_power_sign_flip(self):
        # tokens: a a b b a a b b
        # N = 7
        # (b, a) = 1, left(b) = 3, right(a) = 3
        # O11=1, O12=2, O21=2, O22=2
        counts = build_counts([["a", "a", "b", "b", "a", "a", "b", "b"]])
        ct = contingency_bigram("b", "a", counts)
        self.assertEqual((ct.o11, ct.o12, ct.o21, ct.o22, ct.n), (1, 2, 2, 2, 7))

        # PMI = log2(1 * 7 / (3 * 3)) = log2(7/9)
        expected_pmi = math.log2(7 / 9)
        self.assertAlmostEqual(pmi(ct), expected_pmi, places=12)
        self.assertLess(pmi(ct), 0)
        # PMI^2 is positive even though PMI is negative. PMI^3 keeps the sign.
        self.assertAlmostEqual(pmi_power(ct, 2), expected_pmi**2, places=12)
        self.assertGreater(pmi_power(ct, 2), 0)
        self.assertAlmostEqual(pmi_power(ct, 3), expected_pmi**3, places=12)
        self.assertLess(pmi_power(ct, 3), 0)

        # NPMI = log2(7/9) / -log2(1/7)
        self.assertAlmostEqual(npmi(ct), expected_pmi / -math.log2(1 / 7), places=12)

        # chi2 = 7 * (1*2 - 2*2)^2 / (3*3*4*4) = 28/144
        self.assertAlmostEqual(chi_square(ct), 28 / 144, places=12)
        # |cross|=2, N/2=3.5, max(0, 2-3.5)=0, so Yates is 0
        self.assertAlmostEqual(chi_square_yates(ct), 0.0, places=12)

        # t = (1 - 9/7) / 1 = -2/7
        self.assertAlmostEqual(student_t(ct), -2 / 7, places=12)

        # G^2 = 2 * (ln(7/9) + 4 ln(7/6) + 2 ln(7/8))
        expected_g = 2 * (
            math.log(7 / 9) + 4 * math.log(7 / 6) + 2 * math.log(7 / 8)
        )
        self.assertAlmostEqual(likelihood_ratio(ct), expected_g, places=12)

    def test_undefined_when_joint_or_marginal_is_zero(self):
        # Joint count 0: PMI, t, and G^2 (via marginals_ok, row products) are undefined.
        zero_joint = Contingency(0, 3, 3, 4, 10)
        self.assertIsNone(pmi(zero_joint))
        self.assertIsNone(npmi(zero_joint))
        self.assertIsNone(pmi_power(zero_joint, 2))
        self.assertIsNone(student_t(zero_joint))

        # A zero marginal makes chi-square's denominator 0.
        zero_marginal = Contingency(0, 0, 4, 6, 10)
        self.assertIsNone(chi_square(zero_marginal))
        self.assertIsNone(chi_square_yates(zero_marginal))
        self.assertIsNone(likelihood_ratio(zero_marginal))
        self.assertIsNone(pmi(zero_marginal))

    def test_perfect_dependence_cells(self):
        # O12 = O21 = 0, both words always co-occur with each other,
        # and half the bigrams are something else.
        # PMI = log2( (5/10) / ((5/10)*(5/10)) ) = log2(2) = 1
        ct = Contingency(5, 0, 0, 5, 10)
        self.assertAlmostEqual(pmi(ct), 1.0, places=12)
        self.assertAlmostEqual(chi_square(ct), 10.0, places=12)
        # |5*5 - 0| - 10/2 = 20; 10 * 20^2 / (5*5*5*5) = 4000/625 = 6.4
        self.assertAlmostEqual(chi_square_yates(ct), 6.4, places=12)

    def test_sort_tie_break_is_alphabetical(self):
        ranked = sort_scored([("b b", 1.0), ("a a", 1.0), ("c c", 2.0)])
        self.assertEqual([phrase for phrase, _ in ranked], ["c c", "a a", "b b"])

    def test_zero_cell_does_not_contribute_to_g2(self):
        # City/council table has two zero cells. Compare against the expanded
        # sum that drops those cells, which is the 0 * ln(0) := 0 convention.
        ct = Contingency(2, 0, 0, 2, 4)
        expanded = 2 * (2 * math.log(2 / 1) + 2 * math.log(2 / 1))
        self.assertAlmostEqual(likelihood_ratio(ct), expanded, places=12)
        self.assertEqual(score_bigram(ct)["pmi2"], 1.0)


class NltkFormulaTests(unittest.TestCase):
    def test_identical_counts_match_log_base_and_chi_square_variant(self):
        # Same cells as the city/council toy. NLTK is called on these counts,
        # not on finder.N, so this isolates the formula.
        ct = Contingency(2, 0, 0, 2, 4)
        ours = score_bigram(ct)
        nltk_scores = nltk_scores_same_counts(ct.o11, ct.row1, ct.col1, ct.n)

        # PMI ratio of 1 means NLTK uses log2, not natural log.
        # Natural log would produce a ratio of ln(2) ≈ 0.693.
        self.assertAlmostEqual(nltk_scores["pmi"] / ours["pmi"], 1.0, places=8)
        self.assertNotAlmostEqual(nltk_scores["pmi"] / ours["pmi"], math.log(2), places=3)

        # Uncorrected chi-square matches. Yates (1.0 on this table) does not.
        self.assertAlmostEqual(nltk_scores["chi_sq"], ours["chi_sq"], places=8)
        self.assertNotAlmostEqual(nltk_scores["chi_sq"], ours["chi_sq_yates"], places=3)

        # t matches aside from NLTK's 1e-20 smoother in the square root.
        self.assertAlmostEqual(nltk_scores["student_t"], ours["student_t"], places=8)

        # G^2 matches aside from the same smoother inside the log.
        self.assertAlmostEqual(
            nltk_scores["likelihood_ratio"], ours["likelihood_ratio"], places=6
        )
        # And the ratio is near 1, not 1/ln(2), so NLTK's likelihood ratio is natural log.
        ratio = nltk_scores["likelihood_ratio"] / ours["likelihood_ratio"]
        self.assertAlmostEqual(ratio, 1.0, places=6)

    def test_finder_n_is_token_count_not_bigram_count(self):
        sentences = [["city", "council", "city", "council", "budget"]]
        found = nltk_bigram_rankings(sentences, min_freq=1)
        self.assertEqual(found["finder_N"], 5)
        counts = build_counts(sentences)
        self.assertEqual(counts["n_bigrams"], 4)
        self.assertNotEqual(found["finder_N"], counts["n_bigrams"])


if __name__ == "__main__":
    unittest.main()
