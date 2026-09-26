# AI Car Mechanic Assistant

Virtual senior mechanic chatbot providing deterministic vehicle diagnosis, multimodal defect inspection, transparent repair estimates, and mechanic appointment booking.

- **Frontend**: `<YOUR_VERCEL_URL>.vercel.app`
- **Backend**: `<YOUR_AWS_ELB_OR_EC2_URL>`
- **API docs**: `docs/API.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Postman collection**: `docs/postman_collection.json`

---

## Architecture

```
Next.js 14 (React, strict TS)  :3000
        │  fetch / XHR
        │  NEXT_PUBLIC_API_URL
        ▼
Django 5 + DRF                 :8000
  ├─ apps/chat        POST /api/chat/        deterministic engine turn
  ├─ apps/uploads     POST /api/upload/      magic-byte + sha256 + PIL
  ├─ apps/diagnosis   POST /api/diagnosis/   KB scoring
  ├─ apps/booking     POST /api/booking/     slot + idempotency
  │                   GET  /api/booking/{id}/ receipt
  ├─ apps/core        GET  /api/health/ /api/history/ /api/stats/
  └─ engine/          flow · domain_gate · scoring · safety
        │
        ├── SQLite (WAL)   conversations · messages · uploads · diagnoses · bookings
        └── Google Gemini  gemini-2.5-flash-lite  (gated · cached · capped · graceful-off)
```

**Runtime flow**: text or media → domain gate → (Gemini extract, only if needed) → deterministic KB scoring → follow-up question or diagnosis → service estimate → booking → DB-backed history.

---

## Features

| Feature | Implementation |
|---|---|
| **Text chat** | Domain gate (greeting / restart / yes / idk / no / other) → engine turn |
| **Starter chips** | 6 canonical symptoms; exact keys feed the engine, no terminology ambiguity |
| **Follow-ups** | 68 questions; highest Shannon-entropy question asked next |
| **Safety preemption** | Immediate shutdown advisory on overheating, brake failure, oil pressure collapse |
| **Image / audio / video upload** | `filetype` + magic bytes, size caps (5/10/20 MB), PIL downscale >1024 px, sha256 |
| **Diagnosis** | Top cause + confidence %, ranked alternatives, service recommendation with ₹ estimate + duration |
| **Booking** | Hourly slots 9 AM–6 PM, city-scoped mechanic assignment, UniqueConstraint conflict → 409 + alternatives, idempotent replay |
| **History** | DB-backed; survives refresh; full session restore from `/api/conversations/{id}/` |
| **Receipt** | `GET /api/booking/{id}/` → dedicated receipt page |

---

## API Reference

All responses use a JSON envelope. Errors: `{ "code", "message", "fields" }`.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/chat/` | Evaluate a turn. Body: `{ text?, client_msg_id, symptoms?, upload_ids? }`. Returns `{ conversation_id, state, messages }` (bot replies only; client renders its own user bubble). Idempotent per `client_msg_id`. |
| `POST` | `/api/upload/` | Multipart upload. Returns `{ id, kind, mime_type, size_bytes, sha256, analysis_status }`. |
| `POST` | `/api/diagnosis/` | `{ conversation_id }` → `{ top_cause, confidence, ranked_causes, service_estimate }`. |
| `POST` | `/api/booking/` | `{ conversation_id, diagnosis_id, customer_name, phone, city, scheduled_at, idempotency_key }` → `201` always (replay returns same booking). |
| `GET` | `/api/booking/{id}/` | Receipt data for a confirmed booking. |
| `GET` | `/api/history/` | List of conversations with status + latest activity. |
| `GET` | `/api/conversations/{id}/` | Full conversation: messages + diagnosis + booking. |
| `GET` | `/api/stats/` | Telemetry counters. |
| `GET` | `/api/health/` | Liveness + DB check → `{ "status": "ok", "db": true }`. |

---

## AI Usage Policy

| Trigger | Model | Cache key | Cap | Fallback |
|---|---|---|---|---|
| Symptom extraction (free text) | `gemini-2.5-flash-lite` | `sha256("extract:{text}")` | 2 attempts per turn | Re-prompt with starter chips |
| Media analysis | `gemini-2.5-flash-lite` | `media:{sha256}` | 3 per conversation | Friendly prompt to describe manually; upload marked `skipped` |
| Quota / timeout / error | — | — | — | `AIUsageLog` failure row; conversation continues uninterrupted |

When `AI_ENABLED=0` or `GEMINI_API_KEY` is absent, the app is fully functional via starter chips and manual symptom description.

---

## Design Decisions

1. **Rules-first deterministic engine** — Automotive diagnostics carry safety and liability risk. The bipartite Symptom↔Cause graph with weighted probabilities produces reproducible, explainable conclusions. Gemini is used only to map unstructured input into the graph.
2. **SQLite (WAL)** — Zero-daemon, synchronous transactions, sufficient for single-instance deployment. `PRAGMA journal_mode=WAL` + `busy_timeout=5000` handle concurrency.
3. **Starter chips** — Eliminate terminology ambiguity, speed mobile triage, and ensure the engine receives exact symptom keys.

---

## Project Structure

```
.
├── backend/
│   ├── config/            settings · urls · wsgi
│   ├── apps/
│   │   ├── chat/          turn evaluation, services, idempotency
│   │   ├── uploads/       validators · services · views
│   │   ├── diagnosis/     KB scoring endpoint
│   │   ├── booking/       slots · mechanics · idempotency
│   │   ├── core/          errors · ai_client · cache · usage log
│   │   └── kb/            symptoms · causes · follow-ups · services
│   ├── engine/
│   │   ├── flow.py        state machine (INTAKE → … → CONFIRMED)
│   │   ├── domain_gate.py intent regex (greeting/restart/yes/idk/no/other)
│   │   ├── scoring.py     bipartite graph scoring
│   │   ├── safety.py      red-flag preemption
│   │   ├── extract.py     Gemini symptom extraction wrapper
│   │   └── templates.py   canned bot messages
│   ├── tests/             pytest suite (engine · APIs · uploads · booking)
│   ├── manage.py
│   ├── requirements.txt
│   └── start.sh           migrate + seed_kb + gunicorn
├── frontend/
│   ├── app/               Next.js App Router (page · booking/[id] · layout)
│   ├── components/        ChatApp · Composer · MessageBubble · BookingModal · Recorder · HistoryDrawer
│   ├── lib/               api client · types · constants
│   ├── public/
│   └── package.json
├── docs/
│   ├── API.md
│   ├── ARCHITECTURE.md
│   └── postman_collection.json
── render.yaml            (alternative Render deployment)
── vercel.json            Vercel frontend config
└── README.md
```

---

## Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_kb
python manage.py runserver 8000
```

Verify: `curl http://localhost:8000/api/health/` → `{"status":"ok","db":true}`.

### Frontend

```bash
cd frontend
cp .env.example .env.local        # edit NEXT_PUBLIC_API_URL if needed
npm install
npm run dev
```

Open `http://localhost:3000`.

### Environment Variables

**Backend** (`backend/.env` or process env):

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | *(must set in prod)* | Django signing |
| `DEBUG` | `1` | `0` in production |
| `ALLOWED_HOSTS` | `*` | Comma-separated; set to your domain in prod |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated frontend origins |
| `CORS_ALLOWED_ORIGIN_REGEXES` | `^https://.*\.vercel\.app$` | Regex for Vercel preview domains |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | `dj-database-url` format |
| `MEDIA_ROOT` | `backend/media` | Uploaded files directory |
| `AI_ENABLED` | `1` | `0` to disable Gemini entirely |
| `GEMINI_API_KEY` | *(empty)* | Google AI Studio key |
| `GEMINI_MODEL` | `gemini-2.5-flash-lite` | Model name |

**Frontend** (`frontend/.env.local`):

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend base URL (inlined at build/dev start) |

### Testing

```bash
cd backend
python -m pytest -q                 # 43 tests: engine · APIs · uploads · booking · history
cd frontend
npm run build                       # strict TS · no `any` · 4 routes
```

---

## Production Deployment

Target: **Django backend on AWS EC2 (free-tier eligible) + SQLite + nginx + gunicorn**, **Next.js frontend on Vercel**.

### 1. Launch EC2 Instance

- AWS Console → EC2 → Launch instance
- AMI: Ubuntu 22.04 LTS (free-tier eligible)
- Instance type: `t2.micro`
- Storage: 30 GB gp3 (free tier)
- Security group: inbound TCP 22 (SSH), TCP 80 (HTTP), TCP 443 (HTTPS)
- Key pair: download `.pem`

```bash
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>
```

### 2. Install Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv python3-pip nginx git

# Clone the repo
git clone <YOUR_REPO_URL> ~/app
cd ~/app
```

### 3. Backend Setup (SQLite + Migrations + Seed)

```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create production env file
cat > .env <<EOF
DJANGO_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
DEBUG=0
ALLOWED_HOSTS=<EC2_PUBLIC_IP>,<YOUR_ELB_DNS>,localhost
CORS_ALLOWED_ORIGINS=https://<YOUR_VERCEL_SUBDOMAIN>.vercel.app
CORS_ALLOWED_ORIGIN_REGEXES=^https://.*\.vercel\.app$
CSRF_TRUSTED_ORIGINS=https://<YOUR_VERCEL_SUBDOMAIN>.vercel.app
DATABASE_URL=sqlite:////home/ubuntu/app/backend/db.sqlite3
MEDIA_ROOT=/home/ubuntu/app/backend/media
AI_ENABLED=1
GEMINI_API_KEY=<YOUR_GEMINI_KEY>
GEMINI_MODEL=gemini-2.5-flash-lite
EOF

python manage.py migrate
python manage.py seed_kb
python manage.py collectstatic --noinput
```

SQLite is appropriate for single-instance deployment. For multi-replica, replace `DATABASE_URL` with a PostgreSQL RDS endpoint.

### 4. Gunicorn Systemd Service

```bash
sudo tee /etc/systemd/system/mechanic-backend.service <<EOF
[Unit]
Description=AI Car Mechanic Django Backend
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/app/backend
EnvironmentFile=/home/ubuntu/app/backend/.env
ExecStart=/home/ubuntu/app/backend/venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2 --timeout 90
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now mechanic-backend
```

### 5. nginx Reverse Proxy + HTTPS

```bash
sudo tee /etc/nginx/sites-available/mechanic <<'EOF'
server {
    listen 80;
    server_name <YOUR_ELB_DNS_OR_IP>;

    client_max_body_size 25M;

    location /static/ {
        alias /home/ubuntu/app/backend/staticfiles/;
    }
    location /media/ {
        alias /home/ubuntu/app/backend/media/;
    }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/mechanic /etc/nginx/sites-enabled/mechanic
sudo nginx -t && sudo systemctl reload nginx
```

For HTTPS, attach an ACM certificate to an Application Load Balancer in front of the instance, or use Certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d <YOUR_DOMAIN>
```

`SECURE_PROXY_SSL_HEADER` is already configured in `settings.py` to trust `X-Forwarded-Proto` from the ALB/nginx.

### 6. Backend Health & API Verification

```bash
# Liveness
curl -s http://localhost:8000/api/health/
# → {"status":"ok","db":true}

# CORS preflight from Vercel origin
curl -s -X OPTIONS http://localhost:8000/api/chat/ \
  -H "Origin: https://<YOUR_VERCEL_SUBDOMAIN>.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" -D - -o /dev/null \
  | grep -i access-control-allow-origin

# End-to-end chat round-trip
curl -s -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"text":"brakes squealing","client_msg_id":"probe-1"}'
```

All three must succeed before proceeding.

### 7. Vercel Frontend Deployment

```bash
# In the repo root
vercel --prod
```

Or connect the repo in the Vercel dashboard:
- **Framework Preset**: Next.js
- **Root Directory**: `frontend`
- **Build Command**: `npm run build`
- **Output Directory**: `.next`
- **Environment Variable**: `NEXT_PUBLIC_API_URL=https://<YOUR_AWS_DOMAIN>` (must match the live backend — Vercel inlines this at build time)

`vercel.json` in the repo root already configures the framework, install, build, and output directory.

### 8. End-to-End Verification

From the deployed Vercel URL:

1. Page loads with 6 starter chips
2. Click **Brake noise** → vehicle question → follow-ups → diagnosis card (Worn Brake Pads ~73%) with service estimate
3. Click **Book Certified Mechanic** → modal → fill details → pick slot → **Booking Confirmed** with mechanic name + time
4. Open **View Receipt** → receipt page renders from `GET /api/booking/{id}/`
5. Open **📜 History** → prior session listed; clicking restores full conversation
6. Attach an image → upload succeeds (201); with `AI_ENABLED=1` + key, analysis runs; without key, upload persists with `analysis_status=skipped`
7. Browser console: **zero errors**, **zero CORS failures**
8. Network tab: all API calls target the AWS backend domain

---

## Alternative: Render Deployment

`render.yaml` in the repo root deploys the backend to Render's free tier. Note: Render free-tier services spin down after 15 min of inactivity (30–50 s cold start), and `./media/` is ephemeral — connect S3 for persistent uploads in production.

---

## Docs

- [API reference](docs/API.md)
- [Architecture & ERD](docs/ARCHITECTURE.md)
- [Postman collection](docs/postman_collection.json)
