# Replit Deployment Guide: Collocation Mining & Association Scoring Engine

This repository ([`devdesai25/problem17-collocation-mining`](https://github.com/devdesai25/problem17-collocation-mining)) is configured for deployment as a **single, unified service** on [Replit](https://replit.com). A single FastAPI process serves both the backend API (`/api/*`) and the compiled React/Vite single-page application from `frontend/dist` at the root URL (`/`), enabling full functionality over a single public HTTPS URL.

---

## Architecture Overview

```
                      ┌──────────────────────────────────────────────┐
                      │             Single Public URL                │
                      │         https://<replit-app>.replit.app      │
                      └──────────────────────┬───────────────────────┘
                                             │
                                     [FastAPI Server]
                                    (server/main.py)
                                             │
                        ┌────────────────────┴────────────────────┐
                        │                                         │
                 GET / , /assets/*                         POST /api/analyze
            Mounted StaticFiles (dist/)                    POST /api/trace
                        │                                  POST /api/transcribe
                 [React 19 Frontend]                       GET  /api/contingency
                 Tailwind CSS + Lucide                     GET  /api/health
                        │                                         │
             ┌──────────┴──────────┐                      ┌───────┴───────┐
             │ Interactive Stages  │                      │ faster-whisper│
             │ Contingency Matrix  │                      │ src/models.py │
             │ Mic (iOS/Safari OK) │                      │ NLTK (offline)│
             └─────────────────────┘                      └───────────────┘
```

---

## 1. Quick Deploy Steps on Replit

1. **Import Repository**:
   - Go to [Replit](https://replit.com), click **Create Repl** -> **Import from GitHub**.
   - Enter repo URL: `https://github.com/devdesai25/problem17-collocation-mining`.
   - Language/Environment: Replit will detect `.replit` and `replit.nix`.

2. **Verify Configuration**:
   - Replit automatically loads `.replit` and `replit.nix`:
     - System packages: `python-3.12`, `nodejs-20`, `ffmpeg`.
     - Build command:
       ```bash
       pip install -r requirements-server.txt && python scripts/download_whisper.py && cd frontend && npm ci && npm run build
       ```
     - Run command:
       ```bash
       uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
       ```

3. **Deploy**:
   - Click the **Deploy** button in the top right.
   - Select **Autoscale** (or **Reserved VM** if continuous zero-latency uptime is desired).
   - Click **Deploy Now**.

---

## 2. Environment Variables & Secrets

Configure these in the Replit **Secrets / Environment Variables** tab:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `WHISPER_MODEL` | `base` | faster-whisper model size (`tiny`, `base`, `small`). Use `tiny` for lower RAM / faster boot. |
| `HF_HOME` | `./.hf_cache` | Path for cached model weights. Storing inside project directory prevents repeated downloads. |
| `DEV` | `""` | Set to `1` only during local frontend dev proxying to allow wildcard CORS. Defaults to secure same-origin. |
| `CORS_ORIGINS` | `""` | Optional comma-separated origins if accessing API from an external domain. |
| `PORT` | `8000` | Injected automatically by Replit's runtime environment. |

> [!NOTE]
> No paid third-party API keys (e.g. OpenAI, Cloud Speech) are required. All STT (faster-whisper) and association scoring math run 100% offline and locally.

---

## 3. Autoscale & Cold Start Notes

> [!WARNING]
> **Autoscale Sleep Behavior**:
> - With Replit Autoscale, inactive containers scale to zero after idle periods.
> - When a new request arrives, a **cold start** occurs: the container boots, starts Uvicorn, and loads Python dependencies.
> - The server starts accepting requests immediately, while a background lifespan thread pre-warms the Whisper model into RAM.
> - Check `GET /api/health` — when `"whisper_ready": true`, audio transcription is fully warmed up.
> - If cold start RAM or time is limited, set `WHISPER_MODEL=tiny` in Replit Secrets (takes ~75MB RAM vs ~145MB for base).

---

## 4. Mobile & Browser Compatibility (Microphone Recording)

Microphone audio capture uses HTML5 `MediaRecorder` with dynamic MIME type negotiation:
- **Chrome / Firefox / Edge**: Records using `audio/webm;codecs=opus` (`.webm`).
- **Safari / iOS (WebKit)**: Automatically falls back to `audio/mp4` or `audio/aac` (`.m4a`/`.mp4`).
- **Backend Decoding**: `faster-whisper` and bundled `ffmpeg` ingest all formats seamlessly.

---

## 5. Verification Checklist (Post-Deployment)

Once deployed at your public HTTPS Replit URL (`https://<your-repl>.replit.app`):

1. **Health Check**:
   - Visit `https://<your-repl>.replit.app/api/health`.
   - Confirm response: `{"status": "ok", "whisper_ready": true, "ffmpeg_available": true}`.
2. **Web App Frontend**:
   - Visit root URL `https://<your-repl>.replit.app/`.
   - Confirm React interface loads with 3 input options (Text, File Upload, Microphone).
3. **Sample Analysis & 9-Stage Process Animation**:
   - Click **"Load Sample Transcript"** -> Click **"Run Collocation Analysis"**.
   - Confirm rankings table populates, top-5 cross-metric comparison displays, and contingency inspector works on click.
   - Click through or Play all 9 stages of the process animation.
4. **Full Corpus Mode**:
   - Toggle **"Full Corpus"** and run analysis.
   - Confirm $N = 61,728$ and target phrase (e.g., "coffee shop") shows PMI $\approx 14.33$ and rank #1 in both results and animation.
5. **Speech-to-Text**:
   - Test audio file upload (.wav, .mp3, .m4a).
   - Test browser microphone recording. Confirm transcript is populated and editable in the text area.
