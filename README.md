# 🛡️ Finguard AI

Deepfake detection and live liveness verification for video and audio. A FastAPI backend serves both the inference API and a static HTML/CSS/JS dashboard, so one process is enough.

## Features

- **Video analysis:** face detection, Xception frame scoring, temporal aggregation, then a verdict (REAL / UNCERTAIN / DEEPFAKE) with risk level and explanation.
- **Audio analysis:** mel-spectrogram scoring with MobileNetV2.
- **Live verification:** record a short webcam clip while reading a session code aloud. Video score, audio score and spoken-code match run in parallel.
- **Security:** PBKDF2-hashed login, expiring bearer-token sessions, login lockout, 50 MB limit and SHA-256 check on every upload, audit logging.
- **Dashboard:** login page, batch uploads, live mode, device and environment info panel.

## Tech stack

| Layer | Tools |
|---|---|
| API | FastAPI, Uvicorn |
| Frontend | HTML, CSS, vanilla JavaScript |
| Video | OpenCV, PyTorch, timm (Xception) |
| Audio | librosa, PyTorch (MobileNetV2), ffmpeg |
| Speech check | SpeechRecognition |

## How to run

```bash
pip install -r requirements.txt
python -m app.main
```

Open **http://localhost:8000** and sign in with `admin` / `1234`.

Change the login before real use:

```bash
FINGUARD_USER=operator FINGUARD_PASSWORD='a-strong-passphrase' python -m app.main
```

| Option | Default | Purpose |
|---|---|---|
| `PORT` | 8000 | Server port |
| `SESSION_TTL_SECONDS` | 3600 | Login session length |

Put model weights in `models/`. Install ffmpeg and add it to your PATH for fast audio extraction.

## Live verification

1. Sign in and open **Live Mode**.
2. Allow camera and microphone access.
3. Read the displayed session code aloud while recording.
4. The result shows the video score, audio score, spoken-code match and a final PASS / FAIL.

## API

All `/analyze/*` routes need `Authorization: Bearer <token>` from `/auth/login`.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Status |
| POST | `/auth/login`, `/auth/logout` | Sign in and out |
| GET | `/auth/me` | Current user |
| POST | `/analyze/video` | `.mp4 .avi .mov` |
| POST | `/analyze/audio` | `.wav .mp3 .flac` |
| POST | `/analyze/live-verification` | `.webm` clip + `session_code` |

Interactive docs: `/docs`.

## Structure

```
app/            main.py, auth.py, config.py, ui/ (login, dashboard, css, js)
agent/          decision engine, explanations, policy rules
inference/      video and audio inference, live pipeline, code verifier
preprocessing/  video loading, frame sampling, normalization
face_detection/ detection and alignment
security/       integrity checks
models/         model weights
```
