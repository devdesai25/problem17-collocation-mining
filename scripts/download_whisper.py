#!/usr/bin/env python3
"""Pre-download faster-whisper model at build time into HF_HOME or default cache."""

import os
import sys

def main():
    model_size = os.getenv("WHISPER_MODEL", "base")
    download_root = os.getenv("HF_HOME", None)
    print(f"[build] Pre-downloading faster-whisper model '{model_size}' (download_root={download_root})...")
    try:
        from faster_whisper import WhisperModel
        _ = WhisperModel(model_size, device="cpu", compute_type="int8", download_root=download_root)
        print(f"[build] Successfully pre-downloaded faster-whisper model '{model_size}'.")
    except Exception as e:
        print(f"[build] Warning: Could not pre-download whisper model '{model_size}': {e}", file=sys.stderr)
        # Continue build; runtime can still download or run without whisper if needed
        sys.exit(0)

if __name__ == "__main__":
    main()
