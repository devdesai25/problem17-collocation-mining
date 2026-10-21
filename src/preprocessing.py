"""Corpus loading and preprocessing for collocation mining.

The pipeline reads plain-text transcripts from ``data/raw_transcripts/*.txt``.
Each file is one meeting segment (a dictated agenda item). Documents are
segmented into sentences, tokenized, normalized, and lemmatized before any
association score is computed.

Lowercasing
    Every token is lowercased. These transcripts mix case for the same spoken
    word (``Council`` / ``council``). Case is not a stable cue in meeting
    speech, so counts are pooled. The cost is that ``US`` (United States) and
    ``us`` (pronoun) collapse.

Punctuation and numbers
    Pure punctuation is dropped. Numeric tokens, including ordinals such as
    ``15th``, are dropped so agenda numbers do not become collocations.
    A leading or trailing punctuation mark is stripped. Internal hyphens and
    abbreviation dots are kept (``vice-mayor``, ``u.s``). Possessive ``'s``
    is stripped before lemmatization. Single-character tokens other than
    ``a`` and ``i`` are dropped. ``word_tokenize`` splits contractions, so
    the clitic pieces ``n't``, ``'re``, ``'ve``, ``'ll``, ``'m``, and ``'d``
    are rewritten as ``not``, ``are``, ``have``, ``will``, ``am``, and
    ``would``. A bare ``'s`` is dropped because it is ambiguous between the
    possessive and the copula.

Lemmatization
    ``WordNetLemmatizer`` with a POS tag from the averaged perceptron tagger.
    Treebank tags are mapped onto WordNet noun, verb, adjective, and adverb.
    Unknown tags are lemmatized as nouns. Lemmatization merges inflection
    (``meetings`` / ``meeting``) and can over-merge when the tagger is wrong
    on disfluent speech.

Stopword policy
    Stopwords are removed only in an explicit ablation. The primary token
    stream keeps them.

    Collocation statistics are defined on the word sequence as spoken.
    Deleting stopwords changes every count the metrics use: joint frequency,
    both marginals, and N. It also destroys fixed phrases that contain
    function words. ``in terms of``, ``motion to approve``, and ``point of
    order`` cannot be recovered after stopword removal. Keeping stopwords
    lets high-frequency function bigrams such as ``of the`` compete with
    domain terms, which is exactly the contrast PMI, chi-square, the t-test,
    and the likelihood ratio are meant to expose. The ablation report
    measures what the gold list loses when stopwords are stripped.

Segmentation
    Sentences come from ``nltk.sent_tokenize``. Bigrams and trigrams never
    cross a sentence boundary. Meeting speech is lightly punctuated, so some
    sentences are long; that is a property of the transcripts, not a join
    across speakers' turns beyond what the transcript already concatenated.

NLTK data
    Paths are resolved from ``assets/nltk_data`` first, then ``~/nltk_data``,
    so a completed checkout runs with no network access.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import nltk
from nltk import pos_tag, sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = PROJECT_ROOT / "data" / "raw_transcripts"
NLTK_LOCAL = PROJECT_ROOT / "assets" / "nltk_data"

_WORD = re.compile(r"[a-z]+(?:'[a-z]+)?(?:[-.][a-z]+)*")
_ORDINAL = re.compile(r"\d+(?:st|nd|rd|th)?$")
_DECIMAL = re.compile(r"\d+\.\d+$")
_PUNCT_EDGE = "\"'`“”‘’.,;:!?()[]{}<>"
# word_tokenize splits contractions. Map the clitic piece back to a word
# before lemmatization. Contracted "'s" is dropped: it is ambiguous between
# possessive (city's) and copula (it's), and expanding both to "is" would
# invent verb bigrams from possessives.
_CLITIC = {
    "n't": "not",
    "'re": "are",
    "'ve": "have",
    "'ll": "will",
    "'m": "am",
    "'d": "would",
}
_lemmatizer: WordNetLemmatizer | None = None
_stopword_set: set[str] | None = None


def ensure_nltk() -> None:
    """Prefer project-local NLTK data, then the user home fallback."""
    home = Path.home() / "nltk_data"
    # Insert local first so it wins over any later home path.
    ordered = []
    if NLTK_LOCAL.is_dir():
        ordered.append(str(NLTK_LOCAL))
    if home.is_dir():
        ordered.append(str(home))
    for path in reversed(ordered):
        if path in nltk.data.path:
            nltk.data.path.remove(path)
        nltk.data.path.insert(0, path)


def _lemmatizer_singleton() -> WordNetLemmatizer:
    global _lemmatizer
    if _lemmatizer is None:
        ensure_nltk()
        _lemmatizer = WordNetLemmatizer()
    return _lemmatizer


def stopword_set() -> set[str]:
    global _stopword_set
    if _stopword_set is None:
        ensure_nltk()
        _stopword_set = set(stopwords.words("english"))
    return _stopword_set


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = (
        text.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2014", " ")
        .replace("\u2013", " ")
        .replace("\u00a0", " ")
    )
    return text


def clean_token(token: str) -> str | None:
    """Return a normalized lexical token, or None if it should be dropped."""
    token = token.lower().replace("’", "'")
    if token in _CLITIC:
        token = _CLITIC[token]
    elif token in {"'s", "s'", "'"}:
        return None
    token = token.strip(_PUNCT_EDGE)
    if not token or token in {"a", "i"}:
        return token or None
    if _ORDINAL.fullmatch(token) or _DECIMAL.fullmatch(token) or token.isdigit():
        return None
    if _WORD.fullmatch(token) is None:
        return None
    if token.endswith("'s") and len(token) > 2:
        token = token[:-2]
    if token.endswith("'") and len(token) > 1:
        token = token[:-1]
    if len(token) < 2 and token not in {"a", "i"}:
        return None
    if not token or _WORD.fullmatch(token) is None:
        return None
    return token


def wordnet_pos(treebank_tag: str) -> str:
    if treebank_tag.startswith("J"):
        return "a"
    if treebank_tag.startswith("V"):
        return "v"
    if treebank_tag.startswith("N"):
        return "n"
    if treebank_tag.startswith("R"):
        return "r"
    return "n"


def lemmatize_sentence(tokens: list[str]) -> list[str]:
    """POS-aware lemmatization. ``tokens`` are already cleaned."""
    if not tokens:
        return []
    lemma = _lemmatizer_singleton()
    tagged = pos_tag(tokens)
    return [lemma.lemmatize(tok, wordnet_pos(tag)) for tok, tag in tagged]


def remove_stopwords(tokens: list[str]) -> list[str]:
    stops = stopword_set()
    return [tok for tok in tokens if tok not in stops]


def segment_and_tokenize(text: str, drop_stopwords: bool = False) -> list[list[str]]:
    """Sentence-segment ``text`` into lists of lemmatized tokens."""
    ensure_nltk()
    text = normalize_text(text)
    sentences: list[list[str]] = []
    for sent in sent_tokenize(text):
        raw = [clean_token(tok) for tok in word_tokenize(sent)]
        cleaned = [tok for tok in raw if tok]
        lemmas = lemmatize_sentence(cleaned)
        if drop_stopwords:
            lemmas = remove_stopwords(lemmas)
        if lemmas:
            sentences.append(lemmas)
    return sentences


def load_documents(corpus_dir: Path | None = None) -> list[dict]:
    """Load ``*.txt`` transcripts in filename order. Non-txt files are ignored."""
    corpus_dir = corpus_dir or CORPUS_DIR
    docs = []
    for path in sorted(corpus_dir.glob("*.txt")):
        docs.append(
            {
                "doc_id": path.name,
                "path": str(path),
                "text": path.read_text(encoding="utf-8"),
            }
        )
    if not docs:
        raise FileNotFoundError(f"No transcripts in {corpus_dir}")
    return docs


def preprocess_corpus(
    corpus_dir: Path | None = None,
    drop_stopwords: bool = False,
) -> dict:
    """Load and preprocess the corpus.

    Returns sentence token lists plus inventory counts. Token order follows
    sorted filenames, then sentence order, so repeated runs match.
    """
    documents = []
    sentences: list[list[str]] = []
    for doc in load_documents(corpus_dir):
        doc_sents = segment_and_tokenize(doc["text"], drop_stopwords=drop_stopwords)
        documents.append({**doc, "n_sentences": len(doc_sents)})
        sentences.extend(doc_sents)
    tokens = [tok for sent in sentences for tok in sent]
    return {
        "documents": documents,
        "sentences": sentences,
        "n_documents": len(documents),
        "n_sentences": len(sentences),
        "n_tokens": len(tokens),
        "n_types": len(set(tokens)),
        "drop_stopwords": drop_stopwords,
    }
