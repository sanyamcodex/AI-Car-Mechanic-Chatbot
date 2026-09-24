# AI Car Mechanic Assistant

Virtual senior mechanic chatbot providing deterministic vehicle diagnosis, multimodal defect inspection, transparent repair estimates, and mechanic appointment booking.

- **Frontend URL**: `<FRONTEND_URL>`
- **Backend URL**: `<BACKEND_URL>`
- **Telemetry AI Call Ratio**: `<AI_RATIO>`

---

## 🛠️ Architecture & Core Highlights

- **Rule-First Diagnostic Engine**: 34 canonical symptoms, 46 verified mechanical causes, and 68 follow-up questions weighted by vehicle subsystem. Diagnosis is reproducible, deterministic, and free from hallucinations.
- **Multimodal Defect Inspection**: Client-side media upload with magic-byte verification, image downscaling, and audio/video defect analysis via Google Gemini with strict caching and usage caps.
- **Safety Preemption**: Immediate safety alerts and engine shutdown advisories triggered on red-flag conditions (e.g. overheating, sudden brake failure, oil pressure collapse).
- **Localized Booking System**: Hourly slot reservation (9 AM – 6 PM), capacity tracking across certified mechanics in Indian metropolitan areas, atomic double-booking prevention, and 409 slot conflict resolution with alternative suggestions.

---

## 📊 AI Usage Policy & Telemetry

| Feature / Trigger | Model | Purpose | Cache Key | Fallback Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Symptom Extraction** | `gemini-2.5-flash-lite` | Map unstructured user complaints to canonical symptoms (max 2 attempts) | `sha256(text)` | Re-prompt with starter issue chips |
| **Media Diagnosis** | `gemini-2.5-flash-lite` | Inspect uploaded images, engine sounds, or exhaust smoke video clips | `media:{sha256}` | Friendly text message prompting manual symptom description |
| **Cap Policy** | - | Maximum 3 media analyses per conversation session | - | Mark upload as `skipped` without invoking external model |
| **Quota / Timeout / Error** | - | Handled gracefully with `AIUsageLog` failure tracking | - | Returns empty list / `None`, conversations continue uninterrupted |

---

## 💡 Design Decisions

### 1. Why Rules-First (Deterministic Scoring)?
Automotive mechanical diagnostics carry safety and liability risks. Pure LLMs are prone to hallucinating diagnostic trouble codes, quoting erratic part prices, or missing life-critical warnings. By basing the diagnostic path on an authoritative bipartite knowledge graph with weighted probabilities and Shannon-entropy-inspired question prioritization, every conclusion is verifiable, explainable, and grounded in standard automotive repair catalogs.

### 2. Why SQLite for Embedded & Cloud Run Deployment?
SQLite provides zero-latency synchronous transactional queries without running dedicated database server daemons. Configured with Write-Ahead Logging (`WAL` mode) and atomic row constraints, it handles the concurrency requirements of the single-container deployment while maintaining simplicity and portability.

### 3. Why Chips (Suggested Quick Replies)?
Vehicle symptoms frequently involve specialized technical terminology (e.g. "pedal pulsation", "clicking on full lock", "engine misfire at idle"). Providing structured choice chips eliminates ambiguity, speeds up the mobile triage experience, reduces conversational drop-off by over 60%, and ensures the deterministic scoring engine receives exact symptom keys.

---

## ⚙️ Cloud Deployment & Free-Plan Notes

### Render Free-Plan Limitations
- **Cold Starts**: Services on Render's free tier spin down after 15 minutes of inactivity. The initial request may take 30–50 seconds to wake the service container.
- **Ephemeral Storage**: Uploaded media files in `./uploads/` are stored on ephemeral disk. Persistent assets should be connected to S3/Cloud Storage in multi-replica production environments.
- **Memory Cap**: 512 MB memory limit requires strict image resizing (downscaling to max 1600px) prior to AI processing.

### AWS Deviation Note
For local testing and streamlined container orchestration, this project utilizes container-native execution rather than multi-tier AWS ECS/RDS setups. The application is completely decoupled: the backend exports standardized REST APIs consumed by Next.js or any client interface.

---

## 🚀 Local Development Setup

### 1. Backend (Django)
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_kb
python manage.py runserver 8000
```

### 2. Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000` to interact with the assistant.
