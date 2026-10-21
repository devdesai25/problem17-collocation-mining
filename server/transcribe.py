"""Audio transcription module using faster-whisper (offline CPU int8)."""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Tuple

_whisper_model = None


def is_ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def get_whisper_model():
    """Lazily load the faster-whisper model."""
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise RuntimeError("faster-whisper is not installed in the Python environment.") from e

        model_size = os.getenv("WHISPER_MODEL", "base")
        # Run on CPU using int8 quantization for lightweight offline laptop performance
        _whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _whisper_model


def transcribe_audio_file(file_bytes: bytes, filename: str) -> Tuple[str, str, float]:
    """Transcribe audio bytes to text using faster-whisper.
    
    Returns:
        (transcription_text, language_detected, duration_seconds)
    """
    ext = Path(filename).suffix.lower()
    if not ext:
        ext = ".wav"

    # Write to a temporary file for PyAV / faster-whisper reader
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        start_time = time.time()
        model = get_whisper_model()
        segments, info = model.transcribe(
            tmp_path,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        transcript_parts = []
        for segment in segments:
            text = segment.text.strip()
            if text:
                transcript_parts.append(text)

        full_text = " ".join(transcript_parts)
        duration = float(info.duration) if info and hasattr(info, "duration") else (time.time() - start_time)
        language = info.language if info and hasattr(info, "language") else "en"

        return full_text, language, round(duration, 2)
    except Exception as e:
        msg = str(e)
        if "av" in msg.lower() or "codec" in msg.lower() or "ffmpeg" in msg.lower():
            raise RuntimeError(
                f"Audio format decoding error ({ext}): {msg}. "
                "Ensure standard WAV, MP3, or WebM audio is provided, or install ffmpeg on your system."
            ) from e
        raise RuntimeError(f"Transcription failed: {msg}") from e
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
