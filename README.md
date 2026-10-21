# Problem 17 — Collocation Mining and Association Scoring

MT-AIML, Honors AIML, Sem 5, Module 4. A collocation mining and statistical association engine for municipal meeting transcripts. It extracts bigrams and trigrams using pointwise mutual information (PMI, NPMI, PMI², PMI³), Pearson's chi-square, Yates-corrected chi-square, Student's t-test, and Dunning's log-likelihood ratio (G²), then compares those ranks with NLTK's collocation finders.

The corpus is MeetingBank city-council transcripts (Hu et al., ACL 2023). License on the dataset card: CC BY-NC-SA 4.0. See `data/raw_transcripts/PROVENANCE.md`.

---

## Web Application (FastAPI + React)

A full-stack web application is provided for real-time transcription, statistical exploration, 2×2 contingency inspection, and animated pipeline visualization.

### Architecture & Request Flow

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              Web Browser (React + Vite)                                │
│                                                                                        │
│   [Browser Mic / File Upload] ──> [Editable Transcript Textarea] ──> [Controls Bar]    │
└──────────────────────────┬─────────────────────────────────────┬───────────────────────┘
                           │ audio file                          │ {text, ngram, min_freq,
                           │ (wav/mp3/webm)                      │  metric, drop_stopwords}
                           ▼                                     ▼
        ┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐
        │        POST /api/transcribe          │  │         POST /api/analyze            │
        │   (faster-whisper CPU int8)          │  │    (deterministic scoring & cache)   │
        └──────────────────┬───────────────────┘  └──────────────────┬───────────────────┘
                           │ transcript                              │
                           └──────────────► Populates Textarea ◄─────┘
                                                    │
                   ┌────────────────────────────────┴────────────────────────────────┐
                   ▼                                                                 ▼
┌──────────────────────────────────────┐                          ┌──────────────────────────────────────┐
│       POST /api/trace                │                          │     GET /api/contingency             │
│   (Real-Data Step-by-Step Stepper)   │                          │  (2×2 Matrix Inspector & Formulas)   │
│   • Stage 1: Raw Spoken Dictation    │                          │  • O11, O12, O21, O22, N cells       │
│   • Stage 2: Sentence Segmentation   │                          │  • Row & Column Marginals (R, C)     │
│   • Stage 3: Token Cleaning & Clitic │                          │  • Expected values under H0 (Eij)    │
│   • Stage 4: POS-Aware Lemmatization │                          │  • Live substituted formulas for     │
│   • Stage 5: N-Gram Extraction       │                          │    PMI, NPMI, χ², Yates, t, and G²   │
│   • Stage 6: Corpus Counting         │                          └──────────────────────────────────────┘
│   • Stage 7: Animated 2×2 Cells      │                                             ▲
│   • Stage 8: Association Scoring     │                                             │
│   • Stage 9: Global Ranks Placement  │                                    Click any phrase
└──────────────────────────────────────┘                                             │
                                                                  ┌──────────────────┴───────────────────┐
                                                                  │       Ranked Collocation Views       │
                                                                  │  • Top-K Table with CSV Export       │
                                                                  │  • Side-by-Side Top-5 Comparison     │
                                                                  │  • Disagreement Note (PMI vs t vs G²)│
                                                                  │  • Corpus KPI Stats & Small N Alerts │
                                                                  └──────────────────────────────────────┘
```

### Running the Web Application

#### 1. Start the FastAPI Backend
```bash
# From project root with .venv active:
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000 --reload
```
API docs available at: `http://127.0.0.1:8000/docs`

#### 2. Start the React Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

#### Optional: Installing FFmpeg for Audio Decoding
The backend uses `faster-whisper` with built-in PyAV to decode standard WAV, MP3, and WebM audio files natively without third-party tools. For unusual audio containers or format transcoding, install `ffmpeg`:
- **Windows**: `winget install Gyan.FFmpeg` or `choco install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Linux (Ubuntu/Debian)**: `sudo apt update && sudo apt install ffmpeg`

---

## What the Scores Are

Bigram $N$ is the number of sentence-internal bigram tokens. $f(w_1)$ and $f(w_2)$ are the left and right bigram marginals, ensuring the 2×2 contingency table sums strictly to $N$.

- **PMI**: $\text{PMI}(w_1, w_2) = \log_2 \frac{P(w_1, w_2)}{P(w_1) P(w_2)} = \log_2 \frac{O_{11} \cdot N}{R_1 \cdot C_1}$
- **NPMI**: $\text{NPMI} = \frac{\text{PMI}}{-\log_2 P(w_1, w_2)}$
- **PMI$^k$**: $\text{PMI}^k = \text{PMI}^k$ for $k \in \{2, 3\}$.
- **Pearson's $\chi^2$**: $\chi^2 = \frac{N (O_{11} O_{22} - O_{12} O_{21})^2}{R_1 C_1 R_2 C_2}$
- **Yates' $\chi^2$**: $\chi^2_{\text{Yates}} = \frac{N (\max(0, |O_{11} O_{22} - O_{12} O_{21}| - N/2))^2}{R_1 C_1 R_2 C_2}$
- **Student's $t$**: $t = \frac{O_{11} - (R_1 C_1 / N)}{\sqrt{O_{11}}}$ (Manning & Schütze 1999, eq. 5.10).
- **Log-Likelihood Ratio**: $G^2 = 2 \sum_{i,j} O_{ij} \ln \frac{O_{ij}}{E_{ij}}$ (Dunning 1993).

Rankings sort by score descending, then phrase string ascending.

---

## Install & Environment Setup

From the project root with Python 3.10+:

```bash
python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

NLTK assets are pre-packaged offline in `assets/nltk_data`. If missing, download via:
```bash
python -m nltk.downloader -d assets/nltk_data punkt wordnet omw-1.4 stopwords punkt_tab averaged_perceptron_tagger averaged_perceptron_tagger_eng
```

---

## Testing & Verification

Run both the statistical mathematical test suite and the FastAPI backend test suite:

```bash
# 1. First-principles scoring tests (Manning & Schütze oracle tables)
python -m unittest tests.test_metrics

# 2. Server API tests (/api/analyze, /api/trace, /api/contingency, toy example)
python -m unittest tests.test_server
```

---

## Offline Analysis Pipeline & Reports

```bash
# Run end-to-end evaluation pipeline
python src/pipeline.py

# Build formal academic PDFs
python scripts/build_docs.py

# Build executive presentation decks
python scripts/build_presentations.py
```

Generated deliverables:
- `docs/Architecture_and_Methodology.pdf`
- `docs/Evaluation_Report.pdf`
- `Presentation_Phase1_Primary_Updates.pptx`
- `Presentation_Final_Demo.pptx`
- `reports/metric_comparison.csv`, `reports/precision_at_k.csv`
- `reports/rank_correlation_spearman.csv`, `reports/top20_overlap_jaccard.csv`
- `reports/charts/*.png`

---

## Repository Layout

```text
problem17-collocation-mining/
├── server/
│   ├── main.py              # FastAPI application & REST endpoints
│   ├── schemas.py           # Pydantic request and response models
│   ├── analyzer.py          # Bridge to src/ with LRU caching
│   ├── trace.py             # 9-stage pipeline tracer with real user data
│   └── transcribe.py        # faster-whisper STT integration (CPU int8)
├── frontend/
│   ├── index.html
│   ├── vite.config.ts
│   ├── package.json
│   └── src/
│       ├── App.tsx          # Main application orchestrator
│       ├── api.ts           # Typed API client
│       ├── types.ts         # TypeScript schema definitions
│       └── components/
│           ├── Header.tsx                 # Branding & API status badge
│           ├── InputSection.tsx           # Textarea, Audio Upload, Mic Recorder, Sample Loader
│           ├── ControlsBar.tsx            # N-gram, frequency filter, metric selection, ablation
│           ├── CorpusStats.tsx            # KPI stats & small sample warning banners
│           ├── PipelineAnimation.tsx      # Step-by-step real-data pipeline animation
│           ├── MetricComparison.tsx       # Side-by-side Top-5 matrix & divergence note
│           ├── RankingsTable.tsx          # Filterable collocation table with CSV export
│           └── ContingencyInspector.tsx   # Live 2×2 contingency table & formula substitutions
├── src/
│   ├── preprocessing.py     # Tokenization, clitic expansion, POS lemmatization
│   ├── models.py            # 8 association metrics from scratch & NLTK baselines
│   └── pipeline.py          # Corpus-wide evaluation & chart generation
├── tests/
│   ├── test_metrics.py      # Mathematical oracle tests
│   └── test_server.py       # API integration tests for /api/analyze and /api/trace
├── data/
│   └── raw_transcripts/     # 28 MeetingBank municipal agenda transcripts
├── reports/                 # Evaluation tables, charts, and worked examples
├── docs/                    # PDF reports
├── requirements.txt
└── README.md
```
