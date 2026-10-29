# 🛡️ Finguard AI – Deepfake Edge Agent

### Autonomous Edge AI System for Deepfake Detection & Forensic Analysis

---

## 📌 Overview

**Finguard AI** is a secure, edge-optimized deepfake detection platform built for high-stakes identity verification and forensic analysis. It performs **real-time and batch deepfake detection** on video and audio media using a **FastAPI inference backend** and an **HTML/CSS/JavaScript forensic dashboard**, enabling secure authentication, audit logging, and live liveness verification—without relying on continuous cloud inference.

---

## 🚀 Key Capabilities

### 🔎 Multi‑Modal Deepfake Detection

* **Video Analysis**: Frame-by-frame inference using **Xception-based CNNs**, face alignment, and temporal score aggregation for robust video-level verdicts.
* **Audio Analysis**: Signal- and heuristic-based detection to identify synthetic voice artifacts and tampering.

### 🧪 Forensic Dashboard (HTML, CSS, JS)

* **Secure Role-Based Login** with cryptographic authentication for administrators.
* **Batch Media Uploads** for offline and online analysis.
* **Explainability Engine** generating human-readable reports including **Verdict**, **Risk Level**, and **Confidence Score**.

### 🔴 Live Verification Portal

* **Real-Time Biometric Streaming**: Secure WebRTC-based video and audio streaming for live agent verification.
* **Challenge–Response Liveness Check**: Dynamically generated **Session Codes** that must be spoken aloud to verify presence.
* **Environment Fingerprinting**: Detection of automation and spoofing indicators including **WebDrivers, rooted devices, virtual machines, spyware**, and abnormal hardware concurrency cores.

### 🤖 Autonomous Agent Logic

* **Decision Engine**: Produces final verdicts (**REAL / DEEPFAKE**) based on confidence thresholds and policy rules.
* **Integrity Validation**: Verifies media authenticity and integrity before inference.

---

## 🗂️ Project Structure

```
Project/
├── app/
│   ├── main.py                 # FastAPI backend entry point
│   ├── config.py               # System configuration
│   └── ui/
│       ├── index.html          # Dashboard markup (Bootstrap 5)
│       ├── css/styles.css      # Styles
│       └── js/app.js           # Frontend logic and API calls
├── agent/
│   ├── decision_engine.py      # Autonomous verdict logic
│   ├── explanation_engine.py   # Explainable AI reports
│   └── policy_rules.py         # Confidence & risk thresholds
├── inference/
│   ├── deepfake_infer.py       # Video model inference
│   ├── audio_infer.py          # Audio analysis
│   ├── model_loader.py         # PyTorch model loader
│   └── temporal_aggregation.py # Frame-to-video score aggregation
├── preprocessing/
│   ├── video_loader.py         # Media I/O
│   ├── frame_sampler.py        # Frame extraction
│   ├── face_detector.py        # Face detection (OpenCV / MTCNN)
│   └── normalization.py        # Input normalization
├── security/
│   ├── integrity_check.py      # Media integrity verification
│   └── otp_utils.py            # OTP & cryptographic utilities
├── app_logging/
│   └── event_logger.py         # System & forensic logs
└── requirements.txt            # Python dependencies
```

---

## 🛠️ Installation & Setup

### ✅ Prerequisites

* Python **3.8+**
* Google **Firebase Project** (Firestore enabled)

### 1️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 2️⃣ Firebase Configuration

To enable user management and audit logging:

1. Generate a `serviceAccountKey.json` from the **Firebase Console**.
2. Place it at:

```
app/ui/serviceAccountKey.json
```

### 3️⃣ Model Weights

Place your trained model weights (e.g., `deepfake_model.pth`) in the `models/` directory before running inference.

---

## Running the System

The backend serves both the API and the HTML/CSS/JS dashboard, so a single process is enough.

```bash
pip install -r requirements.txt
python -m app.main
```

Open **http://localhost:8000** in a browser and sign in.

Default credentials are `admin` / `1234`. Change them before any real use:

```bash
FINGUARD_USER=operator FINGUARD_PASSWORD='a-strong-passphrase' python -m app.main
```

`SESSION_TTL_SECONDS` (default 3600) controls session length. `/analyze/*` requires a valid session token.

* Dashboard: `http://localhost:8000/`
* Health check: `http://localhost:8000/health`
* Interactive API docs: `http://localhost:8000/docs`

### Frontend layout

```
app/ui/
├── index.html      # Animated login page
├── dashboard.html  # Analysis dashboard
├── css/styles.css  # Black and white theme (dark and light)
└── js/             # common.js, login.js, dashboard.js
```

To develop the frontend separately (for example with VS Code Live Server), open `app/ui/index.html`
from any static server. The script falls back to `http://localhost:8000` for API calls, and CORS is
already enabled on the backend. Set `window.FINGUARD_API_BASE` before loading `app.js` to point it elsewhere.

---

## 🔴 Live Verification Workflow

1. Log in to the dashboard (default: `admin / 1234`).
2. Navigate to **Live Mode**.
3. Grant webcam & microphone permissions.

**Verification Layers**:

* **Biometric Stream**: Real-time video & audio analysis.
* **Session Code Liveness Test**: User must verbally repeat the displayed alphanumeric code.
* **Security Status Scan**:
  * Hardware core validation
  * WebDriver / bot detection
  * Browser fingerprint verification

---

## 🔌 API Endpoints

| Method | Endpoint         | Description                                |
| ------ | ---------------- | ------------------------------------------ |
| GET    | `/health`        | System health & runtime status             |
| POST   | `/analyze/video` | Video deepfake analysis (.mp4, .avi, .mov) |
| POST   | `/analyze/audio` | Audio authenticity analysis (.wav, .mp3)   |

---

## 🗄️ Firestore Database Architecture

### 🆔 Secure Identity Code (SIC)

* **Purpose**: Short cryptographic identifier for authorized users.
* **Format**: 6‑character alphanumeric (`A–Z, 0–9`).

```json
{ "Name": "John Doe", "SIC": "A7X92B" }
```

### 👔 Employee Records

* Corporate employee tracking using standardized IDs.

```json
{ "Name": "Jane Smith", "ID": "EMP402" }
```

### 🔐 Encrypted Secrets Vault

* Stores sensitive values (masked in UI, stored securely).

```json
{ "Key": "API_MASTER_KEY", "Value": "******" }
```

### 📝 Audit Reports (Forensic Trail)

* Immutable logs generated after every analysis.

```json
{
  "ReportID": "REP-XYZ123",
  "Timestamp": "2025-10-27 14:30:00",
  "Filename": "suspect_video.mp4",
  "MediaType": "Video",
  "Verdict": "DEEPFAKE",
  "Confidence": "98.5%",
  "RiskLevel": "CRITICAL",
  "Details": "Face artifacts detected"
}
```

---

## ⚡ Live Synchronization

* **Real-Time Updates** using Firestore streams.
* **Optimized State Caching** with Streamlit `session_state` to reduce database reads.

---

## 🔐 Cryptographic Security Architecture

### 🔑 SHA‑256 Token Hashing

* OTPs are **never stored in plaintext**.
* One‑way hashing ensures breach‑resistant authentication.

```python
hashlib.sha256(otp.encode()).hexdigest()
```

### ⏱️ Ephemeral Session Expiry

* Strict **400‑second TTL** for all session tokens.
* Automatic rejection of expired or replayed credentials.

### 🧾 Media Integrity Verification

* Cryptographic checksums validate files before AI inference.
* Prevents tampering during upload or transit.

---

## 🧠 Built for High‑Trust Environments

Finguard AI is designed for **banks, fintechs, KYC providers, and digital forensics teams** requiring real‑time, explainable, and tamper‑resistant deepfake detection at the edge.

---

### ⭐ If you find this project useful, consider starring the repository.
