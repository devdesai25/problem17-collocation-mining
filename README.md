# Problem 17 — Collocation Mining and Association Scoring

MT-AIML, Honors AIML, Sem 5, Module 4. A collocation engine for transcribed municipal meetings. It ranks bigrams and trigrams with pointwise mutual information, chi-square, Student's t, and the likelihood ratio, then compares those ranks with NLTK's collocation finders.

The corpus is MeetingBank city-council transcripts (government meeting text), not literally recorded voice memos and not synthetic speech. Source: https://huggingface.co/datasets/huuuyeah/meetingbank (Hu et al., ACL 2023). License on the dataset card: CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/). The assignment brief's "CC BY 4.0" does not match that card. See `data/raw_transcripts/PROVENANCE.md`.

## What the scores are

Bigram N is the number of sentence-internal bigram tokens. f(w1) and f(w2) are the left and right bigram marginals, so the 2×2 table sums to N.

- PMI(w1, w2) = log2( P(w1, w2) / (P(w1) P(w2)) ), with maximum-likelihood probabilities.
- NPMI = PMI / (−log2 P(w1, w2)).
- PMI^k = PMI ** k for k = 2 and k = 3.
- Chi-square = N (O11 O22 − O12 O21)^2 / ((O11+O12)(O11+O21)(O12+O22)(O21+O22)). The Yates variant subtracts N/2 inside the absolute deviation and floors at 0. Chi-square is non-directional.
- Student's t, Manning and Schütze (1999, eq. 5.10): t = (f(w1 w2) − f(w1)f(w2)/N) / sqrt(f(w1 w2)). This is the one-sample t with variance set equal to the mean. Count data do not meet the normal assumption.
- Likelihood ratio, Dunning (1993): G^2 = 2 Σ Oij ln(Oij / Eij), with Eij = (row i · column j) / N. Natural log. Asymptotically chi-square with the same degrees of freedom as Pearson's statistic.

Rankings sort by score descending, then phrase ascending.

## Install

From the project root, with Python 3.12:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m nltk.downloader -d assets/nltk_data punkt wordnet omw-1.4 stopwords
```

NLTK 3.9 also needs the sentence model and the tagger used for POS-aware lemmatization. If those are not already under `assets/nltk_data`, download them too:

```bash
python -m nltk.downloader -d assets/nltk_data punkt_tab averaged_perceptron_tagger averaged_perceptron_tagger_eng
```

Fallback, if `assets/nltk_data` is absent, the same commands with `-d ~/nltk_data`:

```bash
python -m nltk.downloader -d ~/nltk_data punkt wordnet omw-1.4 stopwords
python -m nltk.downloader -d ~/nltk_data punkt_tab averaged_perceptron_tagger averaged_perceptron_tagger_eng
```

This checkout already contains `assets/nltk_data`. After that directory is present, the pipeline does not use the network.

## Run

```bash
python src/pipeline.py
python src/pipeline.py --docs
python scripts/build_docs.py
python scripts/build_presentations.py
streamlit run app.py
python -m unittest tests.test_metrics
```

`streamlit run app.py` launches the interactive web application for real-time transcription analysis, contingency matrix inspection, and CSV export.

`python src/pipeline.py` reads `data/raw_transcripts/*.txt`, scores the corpus, and writes `reports/`. `--docs` rebuilds the two PDFs from those files. `scripts/build_docs.py` does only the PDF step and expects the reports to exist. `scripts/build_presentations.py` rebuilds both Phase 1 and Final PPTX slide decks.

Reports:

- `reports/metric_comparison.csv`, `reports/precision_at_k.csv`
- `reports/rank_correlation_spearman.csv`, `reports/top20_overlap_jaccard.csv`
- `reports/top20_<metric>.csv` and `reports/nltk_vs_scratch_<metric>.csv`
- `reports/qualitative_top20.md`, `reports/evaluation_report.md`
- `reports/charts/*.png` (precision curves, Spearman heatmap, frequency-versus-score scatter, top-20 Jaccard heatmap, pipeline diagram)

Documents:

- `docs/Architecture_and_Methodology.pdf`
- `docs/Evaluation_Report.pdf`

## Corpus

MeetingBank test-split agenda items (Hu et al., ACL 2023), 28 files, 66924 whitespace tokens, 67046 tokens after lemmatization. License on the dataset card: CC BY-NC-SA 4.0. The brief's "CC BY 4.0" does not match that card.

Limits that matter for the numbers: one split, segment-length transcripts rather than full meetings, recognition noise, an incomplete gold list (precision@20 is a lower bound), and lemmatization that turns *is/are/was* into *be*. Stopwords are kept on the main path because deleting them destroys formulas such as *motion to* and *in terms of*. Details are in `data/annotated/annotator_notes.md` and the evaluation report.

## Layout

```text
problem17-collocation-mining/
├── docs/
│   ├── Architecture_and_Methodology.pdf
│   └── Evaluation_Report.pdf
├── src/
│   ├── preprocessing.py
│   ├── models.py
│   └── pipeline.py
├── data/
│   ├── raw_transcripts/
│   └── annotated/
├── requirements.txt
└── README.md
```
