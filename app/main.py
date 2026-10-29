from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import tempfile
import os
import asyncio
import time
from contextlib import asynccontextmanager

# Core pipeline imports
from preprocessing.video_loader import load_video
from preprocessing.frame_sampler import sample_frames
from preprocessing.normalization import normalize_frames
from face_detection.face_detector import detect_faces
from inference.deepfake_infer import run_inference
from inference.temporal_aggregation import aggregate_predictions
from agent.decision_engine import make_decision
from agent.explanation_engine import generate_explanation

# System utilities
from app.config import settings
from app_logging.event_logger import log_event
from security.integrity_check import verify_input_integrity
from app import auth
from inference.live_pipeline import live_video_score, extract_wav


def _warm_up():
    """Load both models and run one dummy forward pass so the first real request is fast."""
    import torch
    from inference.model_loader import get_model_loader
    loader = get_model_loader()
    size = settings.FACE_IMAGE_SIZE
    with torch.no_grad():
        if loader.get_video_model() is not None:
            loader.get_video_model()(torch.zeros(1, 3, size, size, device=loader.get_device()))
        if loader.get_audio_model() is not None:
            loader.get_audio_model()(torch.zeros(1, 3, 224, 224, device=loader.get_device()))
    log_event("MODELS_WARMED_UP", {})


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        await run_in_threadpool(_warm_up)
    except Exception as e:  # never block startup on warm-up
        log_event("WARMUP_FAILED", {"error": str(e)})
    yield


app = FastAPI(
    title="Deepfake Edge Agent",
    description="Autonomous Edge AI System for Deepfake Detection",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS (allows the dashboard to be opened from a different origin during development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "mode": settings.RUNTIME_MODE,
        "device": settings.DEVICE
    }


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/login")
def auth_login(body: LoginRequest, request: Request):
    return auth.login(body.username, body.password, auth.client_ip(request))


@app.get("/auth/me")
def auth_me(user: str = Depends(auth.require_auth)):
    return {"username": user}


@app.post("/auth/logout")
def auth_logout(request: Request, user: str = Depends(auth.require_auth)):
    auth.logout(request.headers["authorization"].split(" ", 1)[1])
    return {"status": "signed_out"}


@app.post("/analyze/video")
async def analyze_video(file: UploadFile = File(...), user: str = Depends(auth.require_auth)):
    """
    Core autonomous pipeline:
    Input → Preprocessing → Inference → Decision → Explanation → Logging
    """

    if not file.filename.lower().endswith((".mp4", ".avi", ".mov")):
        raise HTTPException(status_code=400, detail="Unsupported video format")

    try:
        # Save video temporarily (edge-safe)
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
            tmp.write(await file.read())
            video_path = tmp.name

        # Step 0: Integrity & security check
        verify_input_integrity(video_path)

        log_event("VIDEO_RECEIVED", {"file": file.filename})

        # Step 1: Load video
        video = load_video(video_path)

        # Step 2: Frame sampling
        frames = sample_frames(video)

        # Step 3: Normalization
        frames = normalize_frames(frames)

        # Step 4: Face detection & alignment
        raw_faces = detect_faces(frames)
        from face_detection.face_aligner import align_faces
        face_batches = align_faces(raw_faces)

        

        if len(face_batches) == 0:
            raise HTTPException(status_code=422, detail="No faces detected")

        # Step 5: Deepfake inference (frame-level)
        predictions = run_inference(face_batches)

        # Step 6: Temporal aggregation (video-level)
        raw_val = aggregate_predictions(predictions)
        # FORCE TO FLOAT IMMEDIATELY
        aggregated_score = float(raw_val) 

        # Step 7: Agent decision logic
        # Ensure decision engine gets a float
        decision = make_decision(aggregated_score)

        # Step 8: Explanation generation
        # Use the guaranteed numeric score
        explanation = generate_explanation(
            decision["verdict"],
            float(aggregated_score),
            
            decision["risk_level"]
        )

        # Step 9: Logging & feedback hook
        log_event(
            "ANALYSIS_COMPLETE",
            {
                "score": float(aggregated_score), # No rounding here to be safe
                "decision": decision
            }
        )

        return {
            "filename": file.filename,
            "deepfake_score": float(aggregated_score),
            "decision": decision,
            "explanation": explanation
        }
        

    except HTTPException:
        raise

    except Exception as e:
        log_event("PIPELINE_ERROR", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Internal processing error")

    finally:
        if os.path.exists(video_path):
            os.remove(video_path)



# ---------------------------------------------------------------------------
# Helpers shared by the audio and live-verification routes
# ---------------------------------------------------------------------------
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # keep in sync with the dashboard's 50 MB limit


async def _save_upload(file: UploadFile, allowed_ext: tuple) -> str:
    """Validate an uploaded file and write it to a temp path. Caller must delete it."""
    name = (file.filename or "").lower()
    if not name.endswith(allowed_ext):
        raise HTTPException(status_code=400, detail="Unsupported file format")
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 50 MB edge limit")
    suffix = os.path.splitext(name)[1] or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        return tmp.name


def _video_score(video_path: str) -> float:
    """Video pipeline: load -> sample -> normalise -> detect faces -> infer -> aggregate."""
    from face_detection.face_aligner import align_faces

    video = load_video(video_path)
    frames = normalize_frames(sample_frames(video))
    face_batches = align_faces(detect_faces(frames))
    if len(face_batches) == 0:
        raise HTTPException(status_code=422, detail="No faces detected")
    return float(aggregate_predictions(run_inference(face_batches)))


def _audio_score(audio_path: str) -> float:
    try:
        from inference.audio_infer import run_audio_inference
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Audio dependencies missing ({e.name}). Run: pip install -r requirements.txt",
        )
    return float(run_audio_inference(audio_path))


def _remove(*paths):
    for p in paths:
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


@app.post("/analyze/audio")
async def analyze_audio(file: UploadFile = File(...), user: str = Depends(auth.require_auth)):
    """Audio deepfake analysis. Returns the same JSON shape as /analyze/video."""
    path = await _save_upload(file, (".wav", ".mp3", ".flac"))
    try:
        verify_input_integrity(path)
        log_event("AUDIO_RECEIVED", {"file": file.filename})

        score = await run_in_threadpool(_audio_score, path)
        decision = make_decision(score, media_type="audio")
        explanation = generate_explanation(decision["verdict"], score, decision["risk_level"])

        log_event("ANALYSIS_COMPLETE", {"media": "audio", "score": score, "decision": decision})
        return {
            "filename": file.filename,
            "deepfake_score": score,
            "decision": decision,
            "explanation": explanation,
        }
    except HTTPException:
        raise
    except Exception as e:
        log_event("PIPELINE_ERROR", {"route": "audio", "error": str(e)})
        raise HTTPException(status_code=500, detail="Internal processing error")
    finally:
        _remove(path)


def _live_verdict(score: float, fake_threshold: float) -> str:
    """Live verdict: DEEPFAKE only when the model is confident, otherwise REAL."""
    return "DEEPFAKE" if score >= fake_threshold else "REAL"


@app.post("/analyze/live-verification")
async def analyze_live_verification(
    file: UploadFile = File(...),
    session_code: str = Form(...),
    user: str = Depends(auth.require_auth),
):
    """
    Live liveness check. The dashboard records a short webcam clip (.webm) while the
    person reads a 6-digit session code aloud. We score the video, score the audio,
    and check that the spoken code matches. The three checks are independent, so they
    run concurrently, and the audio is extracted from the clip only once.
    """
    path = await _save_upload(file, (".webm", ".mp4", ".mov", ".avi"))
    wav = None
    try:
        t0 = time.perf_counter()
        verify_input_integrity(path)
        log_event("LIVE_SESSION_RECEIVED", {"file": file.filename})

        try:
            from inference.code_verifier import extract_code_from_audio
        except ImportError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Speech dependencies missing ({e.name}). Run: pip install -r requirements.txt",
            )

        # One audio extraction, shared by the audio model and the speech check.
        wav = await run_in_threadpool(extract_wav, path)
        audio_src = wav or path
        t_audio = time.perf_counter()

        # return_exceptions: wait for every worker so temp files are not deleted under them.
        results = await asyncio.gather(
            run_in_threadpool(live_video_score, path),
            run_in_threadpool(_audio_score, audio_src),
            run_in_threadpool(extract_code_from_audio, audio_src, session_code),
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, BaseException):
                raise r
        (v_score, v_meta), a_score, code = results
        t_done = time.perf_counter()

        v_verdict = _live_verdict(v_score, settings.LIVE_VIDEO_FAKE_THRESHOLD)
        a_verdict = _live_verdict(a_score, settings.LIVE_AUDIO_FAKE_THRESHOLD)

        # PASS only if neither stream is confidently fake and the spoken code matches.
        passed = (
            v_verdict == "REAL"
            and a_verdict == "REAL"
            and code.get("code_match") is True
        )

        result = {
            "scores": {
                "video": {"score": v_score, "verdict": v_verdict},
                "audio": {"score": a_score, "verdict": a_verdict},
                "code": code,
            },
            "final_verdict": "PASS" if passed else "FAIL",
            "timing_ms": {
                "audio_extract": round((t_audio - t0) * 1000),
                "analysis": round((t_done - t_audio) * 1000),
                "total": round((t_done - t0) * 1000),
                "video": v_meta["ms"],
            },
        }
        log_event("LIVE_VERIFICATION_COMPLETE", {
            "final_verdict": result["final_verdict"], "timing_ms": result["timing_ms"],
        })
        return result
    except HTTPException:
        raise
    except Exception as e:
        log_event("PIPELINE_ERROR", {"route": "live", "error": str(e)})
        raise HTTPException(status_code=500, detail="Internal processing error")
    finally:
        _remove(path, wav)


# Serve the HTML/CSS/JS dashboard from the same origin as the API.
# This must stay after all API routes so that it only handles unmatched paths.
app.mount(
    "/",
    StaticFiles(directory=str(settings.FRONTEND_DIR), html=True),
    name="frontend"
)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )