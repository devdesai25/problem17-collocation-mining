"""Rebuild the two graded PDFs from pipeline report files.

    python scripts/build_docs.py
    python src/pipeline.py --docs

Every measured number is read from reports/. Formula markup uses ReportLab
<sub> and <super> tags rather than LaTeX source.
"""

from __future__ import annotations

import json
import string
from pathlib import Path

import matplotlib
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
CHARTS = REPORTS / "charts"
DOCS = ROOT / "docs"
TITLE = (
    "MT-AIML, Honors AIML, Sem 5, Module 4 — "
    "Collocation Mining & Association Scoring, Problem 17"
)

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
METRIC_ORDER = list(DISPLAY)


class _Safe(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def flatten(value, prefix: str = "", out: dict | None = None) -> dict:
    out = {} if out is None else out
    if isinstance(value, dict):
        for key, child in value.items():
            flatten(child, f"{prefix}_{key}" if prefix else str(key), out)
    elif isinstance(value, list):
        return out
    elif isinstance(value, float):
        out[prefix] = f"{value:.6g}"
    elif value is None:
        out[prefix] = "n/a"
    else:
        out[prefix] = str(value)
    return out


def fill(template: str, mapping: dict) -> str:
    return string.Formatter().vformat(template, (), _Safe(mapping))


def register_fonts() -> None:
    font_dir = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    pdfmetrics.registerFont(TTFont("DejaVu", str(font_dir / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVuBold", str(font_dir / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVuItalic", str(font_dir / "DejaVuSans-Oblique.ttf")))
    pdfmetrics.registerFontFamily(
        "DejaVu",
        normal="DejaVu",
        bold="DejaVuBold",
        italic="DejaVuItalic",
        boldItalic="DejaVuBold",
    )


def styles() -> dict:
    base = getSampleStyleSheet()
    common = dict(fontName="DejaVu", textColor=colors.HexColor("#1f2933"), leading=13)
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName="DejaVuBold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#102a43"),
            spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName="DejaVuBold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#102a43"),
            spaceBefore=12,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="DejaVuBold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#243b53"),
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle("body", parent=base["BodyText"], alignment=TA_JUSTIFY, fontSize=9.5, **common),
        "formula": ParagraphStyle(
            "formula",
            parent=base["BodyText"],
            fontName="DejaVu",
            fontSize=10,
            leading=15,
            leftIndent=8,
            textColor=colors.HexColor("#102a43"),
            spaceBefore=3,
            spaceAfter=3,
        ),
        "caption": ParagraphStyle(
            "caption",
            parent=base["BodyText"],
            fontName="DejaVuItalic",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#334e68"),
            spaceAfter=8,
        ),
        "cell": ParagraphStyle("cell", fontName="DejaVu", fontSize=7.5, leading=9.5, textColor=colors.HexColor("#102a43")),
        "cell_head": ParagraphStyle("cell_head", fontName="DejaVuBold", fontSize=7.5, leading=9.5, textColor=colors.white),
        "small": ParagraphStyle("small", fontName="DejaVu", fontSize=8, leading=10.5, alignment=TA_LEFT, textColor=colors.HexColor("#1f2933")),
    }


def esc(text) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def P(text: str, style) -> Paragraph:
    return Paragraph(text, style)


def bullet_list(items: list[str], style) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, style), leftIndent=12) for item in items],
        bulletType="bullet",
        start="•",
        leftIndent=14,
        bulletFontName="DejaVu",
        bulletFontSize=9,
    )


def table(headers: list[str], rows: list[list], style_map, col_widths=None) -> Table:
    head = [Paragraph(esc(cell), style_map["cell_head"]) for cell in headers]
    body = [[Paragraph(esc(cell), style_map["cell"]) for cell in row] for row in rows]
    tbl = Table([head] + body, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bcccdc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ]
        )
    )
    return tbl


def chart(path: Path, width: float = 7.05 * inch) -> list:
    if not path.exists():
        raise FileNotFoundError(path)
    from reportlab.lib.utils import ImageReader

    pixels_w, pixels_h = ImageReader(str(path)).getSize()
    height = width * pixels_h / pixels_w
    return [Image(str(path), width=width, height=height), Spacer(1, 4)]


def num(value, digits=4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, str):
        return value
    return f"{float(value):.{digits}f}"


def load_inputs() -> dict:
    summary = json.loads((REPORTS / "summary_stats.json").read_text(encoding="utf-8"))
    worked = json.loads((REPORTS / "worked_example.json").read_text(encoding="utf-8"))
    comparison = pd.read_csv(REPORTS / "metric_comparison.csv")
    precision = pd.read_csv(REPORTS / "precision_at_k.csv")
    spearman = pd.read_csv(REPORTS / "rank_correlation_spearman.csv")
    jaccard = pd.read_csv(REPORTS / "top20_overlap_jaccard.csv")
    commentary = json.loads((REPORTS / "commentary_resolved.json").read_text(encoding="utf-8"))
    gold = pd.read_csv(ROOT / "data/annotated/gold_collocations.csv")
    failure_template = (ROOT / "data/annotated/failure_analysis.md").read_text(encoding="utf-8")
    return {
        "summary": summary,
        "worked": worked,
        "comparison": comparison,
        "precision": precision,
        "spearman": spearman,
        "jaccard": jaccard,
        "commentary": commentary,
        "gold": gold,
        "failure": fill(failure_template, flatten(summary)),
    }


def header_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#102a43"))
    canvas.rect(0, letter[1] - 0.42 * inch, letter[0], 0.42 * inch, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("DejaVu", 7.5)
    canvas.drawString(0.65 * inch, letter[1] - 0.26 * inch, TITLE)
    canvas.setFillColor(colors.HexColor("#334e68"))
    canvas.setFont("DejaVu", 8)
    canvas.drawString(0.65 * inch, 0.38 * inch, "Problem 17 — Collocation Mining and Association Scoring")
    canvas.drawRightString(letter[0] - 0.65 * inch, 0.38 * inch, f"{doc.page}")
    canvas.restoreState()


def methodology(data: dict, S: dict) -> list:
    summary = data["summary"]
    corpus = summary["corpus"]
    worked = data["worked"]
    convention = summary["n_convention"]
    log_base = summary["log_base"]
    story = []
    story.append(P(TITLE, S["title"]))
    story.append(P("Architecture and Methodology", S["h1"]))
    story.append(
        P(
            "Application context. Executive voice-memo tools turn a dictated note or a "
            "council hearing into tags. The useful tags are not the most frequent words. "
            "They are fixed multiword expressions: role titles, procedural formulas, "
            "policy terms, and place names. This note specifies the collocation engine "
            "that proposes those phrases, the association scores it compares, and the "
            "decisions that change what the scores mean.",
            S["body"],
        )
    )
    story.append(P("What counts as a collocation", S["h1"]))
    story.append(
        P(
            "A collocation here is a contiguous bigram or trigram that speakers treat as "
            "a unit. The unit can be institutionalized (city council, general fund), "
            "procedural (motion to, president pro tem), or a fixed name (long beach, "
            "mile high stadium). Compositional grammar such as of the is frequent and "
            "is not a collocation. A fixed discourse formula such as thank you is a "
            "collocation of a different kind: real, and not a domain tag. The gold file "
            "records the domain and procedural units the evaluation is allowed to count "
            "as hits. It is a curated sample, not a complete inventory of the corpus.",
            S["body"],
        )
    )
    story.append(P("Association measures", S["h1"]))
    story.append(
        P(
            "All eight from-scratch scores share one 2×2 table. N is the number of "
            "sentence-internal bigram tokens, not the number of word tokens. "
            f"On this corpus that N is {convention['our_n_bigram']}. "
            f"NLTK's finder.N is {convention['nltk_finder_N']}, which equals the "
            f"processed token count. The difference is {convention['finder_N_minus_our_N']}, "
            f"the same as the sentence count {convention['n_sentences']}: each sentence "
            "contributes one word that does not start a bigram. "
            "f(w1) is the number of bigrams that start with w1, and f(w2) is the number "
            "that end with w2. Raw unigram counts would count a sentence-final token in "
            "a slot it never occupies, and the bottom-right cell could go negative.",
            S["body"],
        )
    )
    story.append(
        P(
            "O<sub>11</sub> = f(w<sub>1</sub>, w<sub>2</sub>), "
            "O<sub>12</sub> = f(w<sub>1</sub>) − O<sub>11</sub>, "
            "O<sub>21</sub> = f(w<sub>2</sub>) − O<sub>11</sub>, "
            "O<sub>22</sub> = N − O<sub>11</sub> − O<sub>12</sub> − O<sub>21</sub>.",
            S["formula"],
        )
    )
    story.append(
        P(
            "Maximum-likelihood probabilities use that same N: "
            "P(w<sub>1</sub>, w<sub>2</sub>) = O<sub>11</sub> / N, "
            "P(w<sub>1</sub>) = (O<sub>11</sub> + O<sub>12</sub>) / N, "
            "P(w<sub>2</sub>) = (O<sub>11</sub> + O<sub>21</sub>) / N.",
            S["formula"],
        )
    )
    story.append(P("Pointwise mutual information", S["h2"]))
    story.append(
        P(
            "PMI(w<sub>1</sub>, w<sub>2</sub>) = log<sub>2</sub>( P(w<sub>1</sub>, w<sub>2</sub>) / (P(w<sub>1</sub>) P(w<sub>2</sub>)) ) "
            "= log<sub>2</sub>( O<sub>11</sub> · N / (R<sub>1</sub> · C<sub>1</sub>) ).",
            S["formula"],
        )
    )
    story.append(
        P(
            "NPMI = PMI / (−log<sub>2</sub> P(w<sub>1</sub>, w<sub>2</sub>)). "
            "The denominator is zero when the joint probability is 0 or 1, and the score is then left undefined.",
            S["formula"],
        )
    )
    story.append(
        P(
            "PMI<sup>k</sup> = ( log<sub>2</sub>( P(w<sub>1</sub>, w<sub>2</sub>) / (P(w<sub>1</sub>) P(w<sub>2</sub>)) ) )<super>k</super>, "
            "implemented as PMI ** k for k = 2 and k = 3. "
            "An even power turns a strong negative PMI into a large positive score.",
            S["formula"],
        )
    )
    story.append(
        P(
            "PMI is high when two rare words occur mostly together. That is useful for names and technical compounds, "
            "and it is also why a frequency-1 accident can outrank city council. NPMI divides by the self-information "
            "of the pair, which reduces the extra reward for rarity and does not remove the reward for exclusivity.",
            S["body"],
        )
    )
    story.append(P("Chi-square", S["h2"]))
    story.append(
        P(
            "χ<super>2</super> = N (O<sub>11</sub>O<sub>22</sub> − O<sub>12</sub>O<sub>21</sub>)<super>2</super> "
            "/ ( (O<sub>11</sub>+O<sub>12</sub>)(O<sub>11</sub>+O<sub>21</sub>)(O<sub>12</sub>+O<sub>22</sub>)(O<sub>21</sub>+O<sub>22</sub>) ).",
            S["formula"],
        )
    )
    story.append(
        P(
            "χ<super>2</super><sub>Yates</sub> = N ( max(0, |O<sub>11</sub>O<sub>22</sub> − O<sub>12</sub>O<sub>21</sub>| − N/2) )<super>2</super> "
            "/ (the same denominator).",
            S["formula"],
        )
    )
    story.append(
        P(
            "Chi-square is non-directional. It detects dependence, not attraction, and it does not penalize a "
            "high-frequency grammatical pair in the way PMI's ratio does. A perfectly exclusive pair of any "
            "positive count saturates at N, so the top of an unfiltered chi-square list is a tie, broken only "
            "by sorting the phrase string. Yates's continuity correction subtracts N/2 inside the deviation and "
            "floors at zero, which demotes those exclusive hapaxes.",
            S["body"],
        )
    )
    story.append(P("Student's t", S["h2"]))
    story.append(
        P(
            "The collocation form in Manning and Schütze (1999, eq. 5.10) is "
            "t = ( f(w<sub>1</sub>w<sub>2</sub>) − f(w<sub>1</sub>)f(w<sub>2</sub>)/N ) / √f(w<sub>1</sub>w<sub>2</sub>). "
            "The denominator is the Poisson assumption that variance equals the mean, with the mean estimated by the observed bigram count.",
            S["formula"],
        )
    )
    story.append(
        P(
            "That expression is the ordinary one-sample statistic "
            "t = (x-bar − μ) / √(s<super>2</super> / n) "
            "with n = N, x-bar = O<sub>11</sub>/N, μ = P(w<sub>1</sub>)P(w<sub>2</sub>), and s<super>2</super> = x-bar. "
            "Manning and Schütze note that the normality assumption is not strictly satisfied by count data. "
            "The score is still used as a rank. It is directional, and it grows with frequency, so common grammatical pairs outrank rare domain terms.",
            S["body"],
        )
    )
    story.append(P("Likelihood ratio", S["h2"]))
    story.append(
        P(
            "Dunning (1993): G<super>2</super> = 2 Σ<sub>ij</sub> O<sub>ij</sub> ln(O<sub>ij</sub> / E<sub>ij</sub>), "
            "with E<sub>ij</sub> = (row<sub>i</sub> · column<sub>j</sub>) / N. "
            "The term with O<sub>ij</sub> = 0 contributes 0. "
            "Expanded on the 2×2 table, G<super>2</super> = 2 ( L<sub>11</sub> + L<sub>12</sub> + L<sub>21</sub> + L<sub>22</sub> ) "
            "where L<sub>ij</sub> = O<sub>ij</sub> ln(O<sub>ij</sub>/E<sub>ij</sub>) when O<sub>ij</sub> &gt; 0.",
            S["formula"],
        )
    )
    story.append(
        P(
            "G<super>2</super> is asymptotically chi-square with one degree of freedom for a 2×2 table with fixed margins, "
            "the same reference distribution as Pearson's statistic. It is better behaved at the low counts typical of "
            "voice memos. Like chi-square, a large value means dependence, not specifically attraction.",
            S["body"],
        )
    )
    story.append(
        P(
            "Asymptotic equivalence does not imply the same top-20. It describes the null distribution as N grows, "
            "not a monotone relationship between the two scores on strongly associated pairs. "
            f"On the {summary['n_common_candidates']} candidates with frequency at least 3, "
            f"the Spearman correlation of our chi-square and our G<super>2</super> is "
            f"{num(summary['spearman_selected']['chi_sq_likelihood_ratio'], 4)}, "
            "and the two top-20 lists share only <i>long beach</i>. "
            f"An exclusive pair scores Pearson chi-square equal to the bigram N "
            f"({int(convention['our_n_bigram'])}), at any frequency. "
            "<i>boot camp</i> (frequency 4, both marginals 4) has chi-square 61728 and G<super>2</super> 85.1533 "
            "(ranks 1 and 236). Decomposing Pearson's sum, the O<super>11</super> term is 61720.0003 and the "
            "O<super>22</super> term is 0.0003, so the huge complementary cell is not what puts exclusive names on top. "
            "E<super>11</super> = 0.000259, and (O<super>11</super> − E<super>11</super>)<super>2</super> / E<super>11</super> saturates at N. "
            "G<super>2</super> = 2 Σ O<super>ij</super> ln(O<super>ij</super> / E<super>ij</super>) is led by the O<super>11</super> term, "
            "which grows with the joint count. "
            "<i>thank you</i> (frequency 488, marginals 524 and 1129, O<super>11</super>/E<super>11</super> = 50.92) "
            "has G<super>2</super> 3890.29, of which 3835.90 is that O<super>11</super> term, "
            "and chi-square 24535 (rank 25), under the exclusive-pair ceiling. "
            "The same pattern holds for the rest of each head: "
            "<i>coffee shop</i>, <i>dry ice</i>, <i>mm hmm</i>, and <i>san francisco</i> sit near N with G<super>2</super> between 66 and 153, "
            "while <i>want to</i>, <i>you know</i>, <i>i think</i>, and <i>do not</i> lead G<super>2</super> "
            "with chi-square ranks 128 to 154. "
            "Both formulas match scipy.stats.chi2_contingency on these tables "
            "(Pearson and Yates within 1e-11; the uncorrected log-likelihood statistic exactly). "
            f"The N in the table is the bigram count, not the {int(convention['n_tokens'])} word tokens.",
            S["body"],
        )
    )
    story.append(P("Trigram PMI", S["h2"]))
    story.append(
        P(
            "PMI(w<sub>1</sub>, w<sub>2</sub>, w<sub>3</sub>) = log<sub>2</sub>( f(w<sub>1</sub>w<sub>2</sub>w<sub>3</sub>) · N<super>2</super> / (f<sub>1</sub> f<sub>2</sub> f<sub>3</sub>) ), "
            "where N is the number of sentence-internal trigram tokens and each f<sub>i</sub> is the count of trigrams with that word in that slot.",
            S["formula"],
        )
    )

    story.append(P("Worked count table", S["h1"]))
    story.append(
        P(
            f"The toy sentence is <i>{esc(worked['sentence'])}</i>. "
            f"It has {int(worked['n_tokens'])} tokens and N = {int(worked['n_bigrams'])} bigrams. "
            f"The pair under test is <i>{esc(worked['pair'])}</i>. "
            f"O<super>11</super> = {num(worked['o11'], 0)}, "
            f"O<super>12</super> = {num(worked['o12'], 0)}, "
            f"O<super>21</super> = {num(worked['o21'], 0)}, "
            f"O<super>22</super> = {num(worked['o22'], 0)}. "
            f"P(pair) = {num(worked['p_joint'], 4)}, "
            f"P(w<super>1</super>) = {num(worked['p_w1'], 4)}, "
            f"P(w<super>2</super>) = {num(worked['p_w2'], 4)}.",
            S["body"],
        )
    )
    o11, o12, o21, o22 = worked["o11"], worked["o12"], worked["o21"], worked["o22"]
    n = worked["n_bigrams"]
    cross = abs(o11 * o22 - o12 * o21)
    corrected = max(0.0, cross - n / 2.0)
    story.append(
        P(
            f"PMI = log<super>2</super>( ({num(o11, 0)}/{num(n, 0)}) / "
            f"(({num(worked['f_w1'], 0)}/{num(n, 0)}) · ({num(worked['f_w2'], 0)}/{num(n, 0)})) ) "
            f"= {num(worked['scores']['pmi'], 6)}. "
            f"NPMI = {num(worked['scores']['npmi'], 6)}. "
            f"PMI<super>2</super> = {num(worked['scores']['pmi2'], 6)}. "
            f"PMI<super>3</super> = {num(worked['scores']['pmi3'], 6)}.",
            S["formula"],
        )
    )
    story.append(
        P(
            f"χ<super>2</super> = {num(n, 0)} · ({num(worked['cross_product'], 4)})<super>2</super> "
            f"/ {num(worked['chi_denominator'], 4)} = {num(worked['scores']['chi_sq'], 6)}. "
            f"Yates uses max(0, |cross| − N/2) = max(0, {num(cross, 4)} − {num(n / 2, 4)}) = {num(corrected, 4)}, "
            f"so χ<super>2</super><sub>Yates</sub> = {num(worked['scores']['chi_sq_yates'], 6)}.",
            S["formula"],
        )
    )
    story.append(
        P(
            f"The general t uses x-bar = {num(worked['student_t_xbar'], 6)}, "
            f"μ = {num(worked['student_t_mu'], 6)}, s<super>2</super> = x-bar, n = N. "
            f"It equals {num(worked['student_t_general'], 6)}, the same value as the Manning and Schütze form "
            f"{num(worked['scores']['student_t'], 6)}. "
            f"Expected cells under independence are all {num(worked['expected']['e11'], 4)}. "
            f"G<super>2</super> = {num(worked['scores']['likelihood_ratio'], 6)}.",
            S["formula"],
        )
    )
    story.append(
        P(
            f"Calling NLTK's association functions on these same four cells reproduces PMI "
            f"{num(worked['nltk_same_counts']['pmi'], 6)}, chi-square {num(worked['nltk_same_counts']['chi_sq'], 6)}, "
            f"t {num(worked['nltk_same_counts']['student_t'], 6)}, and G<super>2</super> "
            f"{num(worked['nltk_same_counts']['likelihood_ratio'], 6)}. "
            f"Building an NLTK finder on the same five tokens sets finder.N = {int(worked['nltk_finder_N'])} "
            f"and scores city council at PMI {num(worked['nltk_finder_pmi_city_council'], 6)}, "
            f"not at {num(worked['scores']['pmi'], 6)}. The gap is the token-count convention, not the logarithm.",
            S["body"],
        )
    )
    pair_rows = []
    for row in worked["all_pairs"]:
        pair_rows.append(
            [
                row["phrase"],
                int(row["freq"]),
                num(row["pmi"], 4),
                num(row["chi_sq"], 4),
                num(row["chi_sq_yates"], 4),
                num(row["student_t"], 4),
                num(row["likelihood_ratio"], 4),
            ]
        )
    story.append(
        table(
            ["pair", "f", "PMI", "chi-square", "Yates", "t", "G^2"],
            pair_rows,
            S,
            [1.5 * inch, 0.5 * inch, 0.7 * inch, 0.9 * inch, 0.7 * inch, 0.7 * inch, 0.9 * inch],
        )
    )
    story.append(Spacer(1, 6))
    story.append(P("Every cell in that table was computed by src/models.py on the five-token sentence.", S["caption"]))

    story.append(P("Preprocessing", S["h1"]))
    story.append(
        P(
            "Transcripts are read from data/raw_transcripts as plain text, one agenda item per file, in filename order. "
            "Unicode punctuation is normalized, sentences come from NLTK's sentence tokenizer, and tokens come from "
            "NLTK's word tokenizer. Tokens are lowercased. Numeric tokens and bare punctuation are dropped. "
            "Contractions that the tokenizer splits are repaired: n't becomes not, 're becomes are, and a bare 's is "
            "dropped because it is ambiguous between the possessive and the copula. Lemmas use WordNet with a "
            "part-of-speech tag from the averaged perceptron tagger. Bigrams and trigrams never cross a sentence boundary.",
            S["body"],
        )
    )
    story.append(
        P(
            f"The main experiment keeps stopwords. The processed corpus has {corpus['n_tokens']} tokens, "
            f"{corpus['n_sentences']} sentences, and {corpus['n_types']} lemmas. "
            "Removing stopwords would delete motion to, point of order, and in term of, and it would change N "
            "and both marginals, so every score would describe a different sequence from the one that was spoken. "
            f"An ablation that does remove them leaves {summary['stopword_ablation']['n_tokens_without_stopwords']} tokens. "
            f"Only {summary['stopword_ablation']['gold_bigrams_containing_a_stopword']} gold bigrams contain a stopword "
            f"({esc(summary['stopword_ablation']['gold_bigrams_blocked_examples'])}), "
            f"but Student's t precision@20 moves from 0 on the main path to "
            f"{num(summary['stopword_ablation']['student_t_precision_at_20'], 3)} after the deletion, "
            "because of the can no longer occupy the top of the list. That gain is the trade-off: fewer grammatical "
            "false friends, and every function-word formula destroyed.",
            S["body"],
        )
    )
    story.append(
        P(
            "Lemmatization has its own cost. is, are, and was become be, so this is becomes the pseudo-bigram this be. "
            "paid sick becomes pay sick. in terms of becomes in term of. The gold list uses the lemmatized string, "
            "because that is the string the ranker emits. Rankings that look topical and are actually copulas are "
            "called out in the evaluation, not quietly relabeled.",
            S["body"],
        )
    )
    story.append(P("Pipeline", S["h1"]))
    story.extend(chart(CHARTS / "architecture.png"))
    story.append(P("Figure. Main path, NLTK comparison, and the stopword ablation that is kept off that path.", S["caption"]))
    story.append(
        P(
            "The runner builds unigram, bigram, and trigram counts, scores every bigram at frequency at least 3, "
            "and repeats the ranking at frequency at least 1 for the low-count failure analysis. "
            "Candidates are sorted by score descending and phrase ascending, with no random sampling. "
            f"Precision@k = |top k ∩ gold| / k, recall@k = |top k ∩ gold| / |gold|, "
            "and F1 is the harmonic mean of those two. Bigram metrics use the bigram gold list only "
            f"({summary['gold']['n_bigram']} phrases). Trigram metrics use the trigram gold list only "
            f"({summary['gold']['n_trigram']} phrases). "
            "Spearman correlation is computed on the intersection of candidates that every bigram metric scored. "
            f"That intersection has {summary['n_common_candidates']} phrases. "
            "Top-20 overlap is the Jaccard index and the raw intersection size.",
            S["body"],
        )
    )
    story.append(P("NLTK beside the from-scratch scores", S["h1"]))
    story.append(
        P(
            "The assignment's library path is used as a second implementation, not as the definition of the math. "
            "BigramCollocationFinder.from_documents and TrigramCollocationFinder.from_documents are built on the "
            "same lemmatized sentences. apply_freq_filter(3) is applied for the main ranking. "
            "BigramAssocMeasures.pmi, chi_sq, student_t, and likelihood_ratio, and the trigram equivalents, produce the NLTK rankings.",
            S["body"],
        )
    )
    story.append(
        P(
            f"On identical cells, the median ratio of NLTK PMI to our PMI is "
            f"{num(log_base['pmi_median_ratio_nltk_over_scratch'], 6)} "
            f"across {log_base['n_pmi_ratios']} filtered bigrams. "
            f"A natural logarithm would have produced a ratio near {num(log_base['pmi_reference_if_natural_log'], 6)}. "
            f"The measured ratio matches log base 2 ({log_base['pmi_uses']}). "
            f"The median ratio of NLTK's likelihood ratio to our G<super>2</super> is "
            f"{num(log_base['llr_median_ratio_nltk_over_scratch'], 6)}. "
            f"A log<super>2</super> implementation of G<super>2</super> would sit near "
            f"{num(log_base['llr_reference_if_log2'], 6)}. "
            f"The measured ratio matches the natural logarithm ({log_base['llr_uses']}), which is what Dunning's definition uses.",
            S["body"],
        )
    )
    story.append(
        P(
            f"The median absolute difference between NLTK chi-square and our Pearson chi-square, on the same cells, is "
            f"{num(log_base['chi_median_abs_diff_vs_pearson'], 6)}. "
            f"The median absolute difference against the Yates variant is "
            f"{num(log_base['chi_median_abs_diff_vs_yates'], 6)}. "
            f"NLTK therefore implements {log_base['chi_nltk_matches'].replace('_', ' ')}. "
            f"The median absolute difference for the t statistic on the same cells is "
            f"{num(log_base['student_t_median_abs_diff'], 6)}. "
            "NLTK adds 1e-20 inside a square root and a logarithm; at these counts that smoother is invisible.",
            S["body"],
        )
    )
    story.append(
        P(
            "Finder scores still disagree with ours, because finder.N is the token count and the marginals are raw "
            "unigram counts rather than left and right bigram counts. The largest absolute PMI gap on the filtered "
            f"set is {esc(summary['finder_gaps']['pmi']['phrase'])}: our score "
            f"{num(summary['finder_gaps']['pmi']['scratch_score'], 4)} versus the finder score "
            f"{num(summary['finder_gaps']['pmi']['nltk_finder_score'], 4)}. "
            f"The largest chi-square gap is {esc(summary['finder_gaps']['chi_sq']['phrase'])} "
            f"({num(summary['finder_gaps']['chi_sq']['scratch_score'], 1)} versus "
            f"{num(summary['finder_gaps']['chi_sq']['nltk_finder_score'], 1)}). "
            "Rank correlation between the two PMI lists remains high, which is a statement about order, not about the value of N.",
            S["body"],
        )
    )
    story.append(P("Design limits", S["h1"]))
    story.append(
        bullet_list(
            [
                "The corpus is a 28-file subset of MeetingBank's test split, not the full set of council meetings, and not AMI or VoxPopuli audio.",
                "Contiguous sentence-internal windows miss collocations that are interrupted by a disfluency or a parenthetical.",
                "Lowercasing merges US and us. Lemmatization merges inflection and manufactures be-collocations.",
                "Chi-square and G<super>2</super> are used as ranks, not as tests with a reported p-value. The asymptotic chi-square reference is noted and not applied as a cutoff.",
                "The gold list is incomplete on purpose as a human sample. Precision@20 against it is a lower bound.",
                "No neural ranker and no part-of-speech filter on the candidate list. The comparison is among association scores.",
            ],
            S["body"],
        )
    )
    return story


def comparison_table(frame: pd.DataFrame, S: dict) -> Table:
    rows = []
    for record in frame.itertuples(index=False):
        rows.append(
            [
                DISPLAY.get(record.metric, record.metric),
                record.gold_split,
                num(record.precision_at_20, 3),
                num(record.recall_at_20, 3),
                num(record.f1_at_20, 3),
                int(record.hits_at_20),
                f"{record.top20_mean_freq:.1f}",
                record.top1_phrase,
            ]
        )
    return table(
        ["metric", "gold", "P@20", "R@20", "F1@20", "hits", "mean f", "top phrase"],
        rows,
        S,
        [1.35 * inch, 0.65 * inch, 0.55 * inch, 0.55 * inch, 0.55 * inch, 0.42 * inch, 0.55 * inch, 1.7 * inch],
    )


def evaluation(data: dict, S: dict) -> list:
    summary = data["summary"]
    corpus = summary["corpus"]
    gold = data["gold"]
    story = []
    story.append(P(TITLE, S["title"]))
    story.append(P("Evaluation Report", S["h1"]))
    story.append(
        P(
            "This report compares association scores as collocation rankers on transcribed municipal meetings. "
            "The numbers are the pipeline's report files for this run. Precision@20 is a hit rate against a curated "
            "gold list that is not exhaustive, so it is a lower bound on precision against every true collocation.",
            S["body"],
        )
    )
    story.append(P("Corpus", S["h1"]))
    story.append(
        P(
            f"Source: {esc(corpus['source_name'])}, retrieved {esc(corpus['retrieval_date'])}, "
            f"license {esc(corpus['license'])} as declared on the Hugging Face dataset card "
            f"({esc(corpus['source_url'])}). "
            "The assignment brief called MeetingBank CC BY 4.0. The card on the snapshot that was downloaded "
            "says CC BY-NC-SA 4.0. The non-commercial and share-alike terms are the ones that apply. "
            "AMI was inspected first and not used: the public parquet shards embed audio. VoxPopuli English "
            "shards are larger for the same reason. Only MeetingBank transcript text was kept.",
            S["body"],
        )
    )
    story.append(
        P(
            f"The analysis set is 28 agenda-item transcripts selected deterministically from MeetingBank test.json "
            f"(whitespace length between 1400 and 3200, round-robin by city, stop at 65000 whitespace tokens). "
            f"Raw whitespace tokens: {corpus['whitespace_tokens']}. "
            f"After preprocessing: {corpus['n_documents']} documents, {corpus['n_sentences']} sentences, "
            f"{corpus['n_tokens']} tokens, {corpus['n_types']} lemmas. "
            f"Bigram tokens N = {corpus['n_bigram_tokens']}, bigram types = {corpus['n_bigram_types']} "
            f"of which {corpus['n_bigram_types_freq3']} have frequency at least 3. "
            f"Trigram tokens = {corpus['n_trigram_tokens']}, trigram types = {corpus['n_trigram_types']} "
            f"of which {corpus['n_trigram_types_freq3']} have frequency at least 3. "
            "Cities in the sample: Alameda, Boston, Denver, King County, Long Beach, and Seattle. "
            "These are segment transcripts, not full multi-hour meetings, and they contain recognition errors and thin punctuation.",
            S["body"],
        )
    )
    counts = gold.groupby(["ngram", "category"]).size().reset_index(name="n")
    story.append(
        table(
            ["ngram", "category", "gold phrases"],
            [[int(row.ngram), row.category, int(row.n)] for row in counts.itertuples(index=False)],
            S,
            [1.2 * inch, 1.6 * inch, 1.6 * inch],
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        P(
            f"Gold total {int(len(gold))}: {int((gold.ngram == 2).sum())} bigrams and {int((gold.ngram == 3).sum())} trigrams. "
            "Inclusion required frequency at least 3 in the lemmatized stream and a judgment that the phrase is a fixed "
            "domain, procedural, or name unit. Grammatical bigrams and compositional time expressions were rejected. "
            "The annotator notes record the procedure and the lower-bound caveat.",
            S["caption"],
        )
    )
    story.append(P("Metric comparison", S["h1"]))
    story.append(
        P(
            "precision@20 = |top 20 ∩ gold| / 20. recall@20 = |top 20 ∩ gold| / |gold|. "
            "F1@20 is the harmonic mean. Bigram rows use the bigram gold list. Trigram rows use the trigram gold list.",
            S["body"],
        )
    )
    story.append(comparison_table(data["comparison"], S))
    story.append(Spacer(1, 6))
    story.append(
        P(
            f"Best from-scratch bigram metric by F1@20: {DISPLAY.get(summary['best_metric'], summary['best_metric'])} "
            f"at {num(summary['best_f1'], 3)}. "
            "NPMI and chi-square lead because their top 20 is dominated by exclusive names and compounds that were "
            "gold-listed. Student's t scores 0 hits: the top 20 is grammatical and lemmatized copula bigrams. "
            "Log-likelihood sits between them, with a few real titles inside a list that is still mostly discourse.",
            S["body"],
        )
    )
    story.append(P("Precision at k", S["h2"]))
    prec_rows = []
    for record in data["precision"].itertuples(index=False):
        if int(record.k) not in (10, 20, 50):
            continue
        prec_rows.append(
            [
                DISPLAY.get(record.metric, record.metric),
                record.gold_split,
                int(record.k),
                int(record.hits),
                num(record.precision, 3),
                num(record.recall, 3),
                num(record.f1, 3),
            ]
        )
    story.append(
        table(
            ["metric", "gold", "k", "hits", "P", "R", "F1"],
            prec_rows,
            S,
            [1.7 * inch, 0.75 * inch, 0.4 * inch, 0.5 * inch, 0.55 * inch, 0.55 * inch, 0.55 * inch],
        )
    )
    story.append(Spacer(1, 8))
    story.extend(chart(CHARTS / "precision_at_k.png"))
    story.append(P("Figure. Precision at k for every bigram metric, including the NLTK variants.", S["caption"]))

    story.append(P("Rank correlation", S["h1"]))
    story.append(
        P(
            f"Spearman correlation on {summary['n_common_candidates']} shared filtered bigrams. "
            f"PMI versus Student's t is {num(summary['spearman_selected']['pmi_student_t'], 3)}. "
            f"PMI versus log-likelihood is {num(summary['spearman_selected']['pmi_likelihood_ratio'], 3)}. "
            f"PMI versus chi-square is {num(summary['spearman_selected']['pmi_chi_sq'], 3)}. "
            f"PMI versus PMI squared is {num(summary['spearman_selected']['pmi_pmi2'], 3)}, below 1 because squaring "
            f"folds negative PMI upward. PMI versus PMI cubed is a perfect monotone. "
            f"PMI versus NLTK PMI is {num(summary['spearman_selected']['pmi_nltk_pmi'], 3)}. "
            f"Chi-square versus NLTK chi-square is {num(summary['spearman_selected']['chi_sq_nltk_chi_sq'], 3)}. "
            f"Student's t versus NLTK t is {num(summary['spearman_selected']['student_t_nltk_student_t'], 3)}. "
            f"G<super>2</super> versus NLTK's likelihood ratio is "
            f"{num(summary['spearman_selected']['likelihood_ratio_nltk_likelihood_ratio'], 3)}.",
            S["body"],
        )
    )
    labels = [column for column in data["spearman"].columns if column != "metric"]
    indexed = {row.metric: row for row in data["spearman"].itertuples(index=False)}
    pair_rows = []
    for i, left in enumerate(labels):
        for right in labels[i + 1 :]:
            pair_rows.append([DISPLAY.get(left, left), DISPLAY.get(right, right), num(getattr(indexed[left], right), 4)])
    story.append(
        table(
            ["metric A", "metric B", "Spearman"],
            pair_rows,
            S,
            [2.3 * inch, 2.5 * inch, 1.2 * inch],
        )
    )
    story.append(P("Every off-diagonal Spearman correlation on the shared filtered bigrams. The heatmap is the same matrix.", S["caption"]))
    story.append(Spacer(1, 8))
    story.extend(chart(CHARTS / "spearman_heatmap.png"))
    story.append(P("Figure. Spearman correlations. PMI-family scores cluster. The t-test is the outlier.", S["caption"]))

    story.append(P("Top-20 overlap", S["h1"]))
    jac_rows = []
    for record in data["jaccard"].itertuples(index=False):
        if record.metric_a == record.metric_b:
            continue
        jac_rows.append(
            [
                DISPLAY.get(record.metric_a, record.metric_a),
                DISPLAY.get(record.metric_b, record.metric_b),
                int(record.intersection_count),
                num(record.jaccard, 3),
            ]
        )
    story.append(
        table(
            ["metric A", "metric B", "shared top-20", "Jaccard"],
            jac_rows,
            S,
            [1.8 * inch, 1.8 * inch, 1.2 * inch, 1.0 * inch],
        )
    )
    story.append(Spacer(1, 8))
    story.extend(chart(CHARTS / "top20_jaccard_heatmap.png"))
    story.append(P("Figure. Jaccard overlap of the filtered top-20 lists.", S["caption"]))

    story.append(P("From-scratch values against NLTK", S["h1"]))
    story.append(
        P(
            f"finder.N = {summary['n_convention']['nltk_finder_N']} and our bigram N = {summary['n_convention']['our_n_bigram']}. "
            f"PMI log base decision: {log_word(summary)}. "
            f"G<super>2</super> log base decision: {summary['log_base']['llr_uses']}. "
            f"Chi-square variant: {summary['log_base']['chi_nltk_matches'].replace('_', ' ')}.",
            S["body"],
        )
    )
    gap_rows = []
    for metric, gap in summary["finder_gaps"].items():
        gap_rows.append(
            [
                DISPLAY.get(metric, metric),
                gap["phrase"],
                int(gap["freq"]),
                num(gap["scratch_score"], 4),
                num(gap["nltk_finder_score"], 4),
                num(gap["abs_diff_finder"], 4),
            ]
        )
    story.append(
        table(
            ["metric", "largest finder gap", "f", "ours", "NLTK finder", "|diff|"],
            gap_rows,
            S,
            [1.3 * inch, 1.5 * inch, 0.45 * inch, 1.1 * inch, 1.2 * inch, 1.0 * inch],
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        P(
            "Same-count differences for chi-square against Pearson are numerically zero at the reported precision. "
            "Finder differences are the N convention and the unigram-versus-positional marginals. "
            "Full pair tables are in reports/nltk_vs_scratch_*.csv.",
            S["caption"],
        )
    )

    story.append(P("Frequency against score", S["h1"]))
    story.extend(chart(CHARTS / "frequency_vs_score.png", width=7.15 * inch))
    story.append(
        P(
            "Figure. Every unfiltered bigram. Red points are that metric's own top 20. "
            "PMI's red points sit on frequency 1. The t-test's red points sit at the high-frequency edge. "
            "Yates is the chi-square panel that does not paint the hapax cloud red.",
            S["caption"],
        )
    )
    unfiltered = pd.read_csv(REPORTS / "top20_unfiltered_pmi.csv")
    story.append(
        P(
            "Unfiltered PMI top, all frequency 1, in alphabetical tie-break order: "
            + ", ".join(esc(phrase) for phrase in unfiltered["phrase"].head(8))
            + ". Several are real names. Several are one-sentence accidents. The tie, not a graded association strength, produced the order.",
            S["body"],
        )
    )

    story.append(P("Qualitative top-20 review", S["h1"]))
    story.append(
        P(
            "Each row is the filtered ranking (frequency at least 3). "
            "genuine means the phrase is on the gold list. "
            "acceptable means it is a fixed expression or a real name the gold list did not include. "
            "junk means grammar, a lemmatization artifact, a backchannel, or a window cut out of a list. "
            "An acceptable miss lowers measured precision and is not an extraction error.",
            S["body"],
        )
    )
    by_metric: dict[str, list] = {}
    for row in data["commentary"]:
        by_metric.setdefault(row["metric"], []).append(row)
    for metric in METRIC_ORDER:
        rows = by_metric.get(metric, [])
        if not rows:
            continue
        story.append(P(DISPLAY.get(metric, metric), S["h2"]))
        table_rows = []
        for row in rows:
            table_rows.append(
                [
                    int(row["rank"]),
                    row["phrase"],
                    num(row["score"], 4),
                    int(row["freq"]) if row.get("freq") not in ("", None) else "",
                    row["label"],
                    row["commentary"],
                ]
            )
        story.append(
            table(
                ["#", "phrase", "score", "f", "label", "commentary"],
                table_rows,
                S,
                [0.28 * inch, 1.25 * inch, 0.62 * inch, 0.32 * inch, 0.72 * inch, 3.85 * inch],
            )
        )
        story.append(Spacer(1, 6))

    story.append(P("Failure analysis", S["h1"]))
    for block in data["failure"].split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.startswith("### "):
            story.append(P(esc(block[4:]), S["h2"]))
        else:
            story.append(P(esc(block).replace("\n", " "), S["body"]))

    story.append(P("What this evaluation shows, and what it does not", S["h1"]))
    story.append(
        P(
            f"It shows, on {corpus['n_tokens']} processed tokens of real council speech, that the eight scores "
            "do not rank the same phrases. PMI, NPMI, and chi-square concentrate on exclusive compounds and names. "
            f"Their filtered precision@20 values are {num(summary['metrics']['pmi']['precision_at_20'], 3)}, "
            f"{num(summary['metrics']['npmi']['precision_at_20'], 3)}, and "
            f"{num(summary['metrics']['chi_sq']['precision_at_20'], 3)}. "
            f"Student's t precision@20 is {num(summary['metrics']['student_t']['precision_at_20'], 3)} "
            f"with mean top-20 frequency {num(summary['metrics']['student_t']['top20_mean_freq'], 1)}. "
            f"Log-likelihood precision@20 is {num(summary['metrics']['likelihood_ratio']['precision_at_20'], 3)} "
            f"and is the only from-scratch list that contains council member. "
            "It shows that NLTK's formulas match ours when the cells match, and that finder.N does not match our N. "
            "It shows that a frequency floor of 3 changes PMI and Pearson chi-square from an alphabetical hapax list into a list of repeated names, and that Yates does part of that job without the floor.",
            S["body"],
        )
    )
    story.append(
        P(
            "It does not show that NPMI or chi-square is a calibrated tagger. Nineteen of twenty top phrases landing "
            "on the gold list is partly a property of this gold list, which includes rare exclusive names and excludes "
            "thank you. A gold list built only from high-frequency institutional titles would have reversed the "
            "precision ranking. It does not show significance. No p-value cutoff was applied, and the t-test's normal "
            "model is already known to be the wrong sampling story for these counts. It does not show trigram "
            "extraction working as a general phrase chunker: windows of three tokens slice committee titles, and "
            "the unfiltered trigram PMI list is entirely frequency 1. It does not transfer, without a new gold list, "
            "to a different genre of voice memo. The license is non-commercial. The sample is one split and 28 segments.",
            S["body"],
        )
    )
    return story


def log_word(summary: dict) -> str:
    return (
        f"{summary['log_base']['pmi_uses']} "
        f"(median ratio {num(summary['log_base']['pmi_median_ratio_nltk_over_scratch'], 4)})"
    )


def build(path: Path, story: list) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.58 * inch,
        title=path.stem,
    )
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)


def main() -> None:
    register_fonts()
    S = styles()
    data = load_inputs()
    if "{" in data["failure"] and "metrics_" in data["failure"]:
        raise SystemExit("Failure-analysis template still contains unfilled placeholders.")
    arch = DOCS / "Architecture_and_Methodology.pdf"
    ev = DOCS / "Evaluation_Report.pdf"
    build(arch, methodology(data, S))
    build(ev, evaluation(data, S))
    print(arch)
    print(ev)


if __name__ == "__main__":
    main()
