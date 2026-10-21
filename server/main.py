"""FastAPI Web Application for Problem 17 Collocation Mining & Association Scoring."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from server.analyzer import (
    analyze_text_or_corpus,
    compute_contingency_detail,
    get_sample_transcript_content,
    list_sample_transcripts,
)
from server.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ContingencyResponse,
    SampleItem,
    TraceRequest,
    TraceResponse,
    TranscribeResponse,
)
from server.trace import generate_pipeline_trace
from server.transcribe import is_ffmpeg_available, transcribe_audio_file

app = FastAPI(
    title="Collocation Mining & Association Scoring API",
    description="Deterministic statistical collocation extraction and association scoring for spoken transcripts.",
    version="2.0.0",
)

# Enable CORS for Vite dev server and local clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Maximum input payload size guard (approx 5 MB of text)
MAX_TEXT_LENGTH = 5_000_000


@app.get("/api/health")
def health_check() -> Dict[str, Any]:
    """Health check reporting system and dependency availability."""
    return {
        "status": "ok",
        "service": "Collocation Mining & Association Scoring Engine",
        "ffmpeg_available": is_ffmpeg_available(),
        "python_version": sys.version.split()[0],
    }


@app.post("/api/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(file: UploadFile = File(...)) -> TranscribeResponse:
    """Transcribe an uploaded audio file (wav/mp3/m4a/webm) using offline faster-whisper."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload.",
        )

    # 50MB audio upload limit
    audio_bytes = await file.read()
    if len(audio_bytes) > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file exceeds 50 MB limit.",
        )

    try:
        text, language, duration = transcribe_audio_file(audio_bytes, file.filename)
        return TranscribeResponse(
            text=text,
            language=language,
            duration=duration,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze_collocations(payload: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze text or MeetingBank corpus for collocations across 8 association measures."""
    if not payload.use_full_corpus and not payload.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input text cannot be empty when not using the full corpus.",
        )

    if len(payload.text) > MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Input text exceeds maximum allowed size ({MAX_TEXT_LENGTH} chars).",
        )

    try:
        result = analyze_text_or_corpus(
            text=payload.text,
            ngram=payload.ngram,
            min_freq=payload.min_freq,
            metric=payload.metric,
            drop_stopwords=payload.drop_stopwords,
            top_k=payload.top_k,
            use_full_corpus=payload.use_full_corpus,
        )
        return AnalyzeResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis pipeline error: {str(e)}",
        )


@app.post("/api/trace", response_model=TraceResponse)
def get_trace(payload: TraceRequest) -> TraceResponse:
    """Generate per-stage intermediate data for the step-by-step pipeline animation."""
    if not payload.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text cannot be empty for pipeline tracing.",
        )

    try:
        trace_data = generate_pipeline_trace(
            text=payload.text,
            sample_sentence_index=payload.sample_sentence_index,
            target_phrase=payload.target_phrase,
            drop_stopwords=payload.drop_stopwords,
            ngram=payload.ngram,
        )
        return TraceResponse(**trace_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline trace generation error: {str(e)}",
        )


@app.get("/api/contingency", response_model=ContingencyResponse)
def get_contingency(
    w1: str = Query(..., description="First word of collocation"),
    w2: str = Query(..., description="Second word of collocation"),
    text: str = Query("", description="Context text from which to calculate contingency"),
    drop_stopwords: bool = Query(False, description="Whether stopwords were dropped"),
    use_full_corpus: bool = Query(False, description="Whether to query full MeetingBank corpus"),
) -> ContingencyResponse:
    """Inspect exact 2x2 contingency table, live metrics, and substituted formulas."""
    if not use_full_corpus and not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text must be provided if not querying full corpus.",
        )

    try:
        contingency_data = compute_contingency_detail(
            w1=w1.strip().lower(),
            w2=w2.strip().lower(),
            text=text,
            drop_stopwords=drop_stopwords,
            use_full_corpus=use_full_corpus,
        )
        return ContingencyResponse(**contingency_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Contingency calculation error: {str(e)}",
        )


@app.get("/api/sample", response_model=List[SampleItem])
def list_samples() -> List[SampleItem]:
    """List the 28 curated MeetingBank municipal agenda transcripts."""
    samples = list_sample_transcripts()
    return [SampleItem(**s) for s in samples]


@app.get("/api/sample/{file_id}")
def get_sample_content(file_id: str) -> Dict[str, str]:
    """Retrieve the full text of a specific MeetingBank sample transcript."""
    content = get_sample_transcript_content(file_id)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample transcript '{file_id}' not found.",
        )
    return {"id": file_id, "content": content}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.main:app", host="127.0.0.1", port=8000, reload=True)
