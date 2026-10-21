"""Interactive Web Application for Collocation Mining & Association Scoring.

Executable Streamlit app for Problem 17:
Run via:
    streamlit run app.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

# Ensure src/ is on path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from models import (
    BIGRAM_METRICS,
    build_counts,
    contingency_bigram,
    phrase_of,
    rank_metric,
    rank_trigram_pmi,
    score_bigram,
)
from preprocessing import CORPUS_DIR, preprocess_corpus, segment_and_tokenize

st.set_page_config(
    page_title="Collocation Mining Engine — Problem 17",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #182B49;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #5A646E;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-header">🎙️ Collocation Mining & Association Scoring Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Executive Voice Memo & Spoken Transcript Analysis | Problem 17 (MT-AIML Module 4)</div>', unsafe_allow_html=True)


# Sidebar Configuration
st.sidebar.header("⚙️ Configuration & Controls")

data_source = st.sidebar.radio(
    "Data Source",
    ["Corpus Transcripts (MeetingBank)", "Custom Spoken Input"],
    index=0,
)

if data_source == "Corpus Transcripts (MeetingBank)":
    sample_files = sorted([f.name for f in CORPUS_DIR.glob("*.txt")])
    selected_file = st.sidebar.selectbox("Select Sample Transcript", sample_files, index=0)
    full_corpus = st.sidebar.checkbox("Analyze Full 28-File Corpus", value=False)
else:
    custom_text = st.sidebar.text_area(
        "Enter Spoken Dictation / Transcript:",
        value="""The city council met this morning to review the affordable housing master plan.
Council member Richardson moved to approve the annual action plan.
Those in favor please signify by saying aye.
The motion carries and the general fund allocation is secured.
Thank you council member for the presentation on law enforcement oversight.""",
        height=180,
    )

st.sidebar.subheader("Statistical Hyperparameters")
ngram_choice = st.sidebar.selectbox("N-Gram Order", ["Bigram (2-word)", "Trigram (3-word)"], index=0)
min_freq = st.sidebar.slider("Minimum Frequency Filter (f >= k)", min_value=1, max_value=10, value=3)
drop_stopwords = st.sidebar.checkbox("Ablation: Remove Stopwords", value=False)

metric_display = {
    "pmi": "Pointwise Mutual Information (PMI)",
    "npmi": "Normalized PMI (NPMI)",
    "chi_sq": "Pearson's Chi-Square (χ²)",
    "chi_sq_yates": "Yates-Corrected Chi-Square",
    "student_t": "Student's t-test (Manning & Schütze)",
    "likelihood_ratio": "Log-Likelihood Ratio (Dunning G²)",
}

metric_key = st.sidebar.selectbox(
    "Primary Association Metric",
    list(metric_display.keys()),
    format_func=lambda k: metric_display[k],
    index=0,
)


@st.cache_data(show_spinner=False)
def load_and_process_corpus(is_full: bool, file_name: str, remove_stops: bool):
    if is_full:
        sentences, files = preprocess_corpus(drop_stopwords=remove_stops)
        return sentences, len(files), sum(len(s) for s in sentences)
    else:
        path = CORPUS_DIR / file_name
        text = path.read_text(encoding="utf-8")
        sentences = segment_and_tokenize(text, drop_stopwords=remove_stops)
        return sentences, 1, sum(len(s) for s in sentences)


with st.spinner("Processing transcripts and building co-occurrence matrices..."):
    if data_source == "Corpus Transcripts (MeetingBank)":
        sentences, num_files, total_tokens = load_and_process_corpus(full_corpus, selected_file, drop_stopwords)
    else:
        sentences = segment_and_tokenize(custom_text, drop_stopwords=drop_stopwords)
        num_files = 1
        total_tokens = sum(len(s) for s in sentences)

counts = build_counts(sentences)

# KPI Metrics Row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Sentences Processed", f"{len(sentences):,}")
with col2:
    st.metric("Total Tokens", f"{counts['n_tokens']:,}")
with col3:
    st.metric("Unique Bigrams", f"{len(counts['bigram']):,}")
with col4:
    st.metric("Unique Trigrams", f"{len(counts['trigram']):,}")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📊 Top-20 Extracted Collocations", "⚖️ Multi-Metric Comparison", "🔬 2×2 Contingency Inspector"])

with tab1:
    st.subheader(f"Rankings by {metric_display[metric_key]} (f ≥ {min_freq})")
    
    if ngram_choice == "Bigram (2-word)":
        ranked = rank_metric(metric_key, counts, min_freq=min_freq)
        df_ranked = pd.DataFrame(ranked)
        if not df_ranked.empty:
            df_display = df_ranked[["rank", "phrase", "score", "freq", "f_w1", "f_w2", "o11", "o22"]].head(20)
            df_display.columns = ["Rank", "Collocation Phrase", "Score", "Joint Freq", "Left Marg (w1)", "Right Marg (w2)", "O11", "O22"]
            st.dataframe(df_display, use_container_width=True)
            
            csv = df_display.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Top-20 CSV", csv, f"collocations_{metric_key}.csv", "text/csv")
        else:
            st.warning("No bigrams met the minimum frequency threshold.")
    else:
        ranked_tri = rank_trigram_pmi(counts, min_freq=min_freq)
        df_tri = pd.DataFrame(ranked_tri)
        if not df_tri.empty:
            df_display = df_tri[["rank", "phrase", "score", "freq", "w1", "w2", "w3"]].head(20)
            df_display.columns = ["Rank", "Trigram Phrase", "PMI Score", "Freq", "Word 1", "Word 2", "Word 3"]
            st.dataframe(df_display, use_container_width=True)
        else:
            st.warning("No trigrams met the minimum frequency threshold.")

with tab2:
    st.subheader("Side-by-Side Top-5 Comparison across Association Measures")
    st.markdown("Observe the trade-off: **PMI** prioritizes exclusive rare terms, while **Student's t** and **Likelihood Ratio** favor frequent speech patterns.")
    
    cols = st.columns(4)
    key_metrics = ["pmi", "chi_sq", "student_t", "likelihood_ratio"]
    for i, m in enumerate(key_metrics):
        with cols[i]:
            st.markdown(f"**{metric_display[m]}**")
            m_ranked = rank_metric(m, counts, min_freq=min_freq)
            if m_ranked:
                top5_df = pd.DataFrame(m_ranked)[["phrase", "score", "freq"]].head(5)
                top5_df.columns = ["Phrase", "Score", "Count"]
                st.dataframe(top5_df, hide_index=True, use_container_width=True)

with tab3:
    st.subheader("Interactive 2×2 Contingency Table Inspection")
    if counts["bigram"]:
        available_phrases = [phrase_of(k) for k, v in counts["bigram"].most_common(50)]
        target_phrase = st.selectbox("Select Top Frequent Candidate for Deep Dive:", available_phrases)
        w1, w2 = target_phrase.split()
        ct = contingency_bigram(w1, w2, counts)
        scores = score_bigram(ct)
        
        c_left, c_right = st.columns([1, 1])
        with c_left:
            st.markdown(f"#### Observed Co-occurrence Grid (N = {int(ct.n):,})")
            ct_df = pd.DataFrame(
                [
                    [int(ct.o11), int(ct.o12), int(ct.row1)],
                    [int(ct.o21), int(ct.o22), int(ct.row2)],
                    [int(ct.col1), int(ct.col2), int(ct.n)],
                ],
                index=[f"w1 = '{w1}'", f"w1 ≠ '{w1}'", "Total Right Marg"],
                columns=[f"w2 = '{w2}'", f"w2 ≠ '{w2}'", "Total Left Marg"],
            )
            st.table(ct_df)
        
        with c_right:
            st.markdown("#### Computed Scores for This Candidate")
            st.write(f"- **PMI:** `{scores['pmi']:.4f}` bits")
            st.write(f"- **Normalized PMI (NPMI):** `{scores['npmi']:.4f}`")
            st.write(f"- **Pearson's Chi-Square:** `{scores['chi_sq']:.2f}`")
            st.write(f"- **Yates Chi-Square:** `{scores['chi_sq_yates']:.2f}`")
            st.write(f"- **Student's t-statistic:** `{scores['student_t']:.4f}`")
            st.write(f"- **Likelihood Ratio (G²):** `{scores['likelihood_ratio']:.2f}`")

st.markdown("---")
st.caption("MT-AIML Semester 5 | Natural Language Processing & Language Modeling | Honors AI & ML")
