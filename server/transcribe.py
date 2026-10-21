"""Audio transcription module using faster-whisper (offline CPU int8)."""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Tuple

_whisper_model = None
_whisper_ready = False


def is_ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def is_whisper_ready() -> bool:
    global _whisper_ready
    return _whisper_ready


def warm_whisper_model() -> None:
    """Pre-warm the Whisper model on server startup without blocking initial requests."""
    global _whisper_ready
    try:
        get_whisper_model()
        _whisper_ready = True
    except Exception as e:
        print(f"Whisper background warming note: {e}")
        _whisper_ready = False


def get_whisper_model():
    """Lazily load the faster-whisper model."""
    global _whisper_model, _whisper_ready
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
        except Exception as e:
            raise RuntimeError(f"Could not load faster-whisper: {e}") from e

        model_size = os.getenv("WHISPER_MODEL", "base")
        download_root = os.getenv("HF_HOME")
        # Run on CPU using int8 quantization for lightweight offline laptop/Replit performance
        _whisper_model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
            download_root=download_root,
        )
        _whisper_ready = True
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
