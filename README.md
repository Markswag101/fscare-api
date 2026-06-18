# FS Care Drug Request API

Backend API for the **First Sterling Pharmacy** drug request portal. Hospitals submit requests for drugs and medical supplies; FS Care reviews, actions, and notifies hospitals by email at every step.

---

## Tech stack

- **FastAPI** — API framework
- **SQLAlchemy** — ORM
- **PostgreSQL** (Railway) or **SQLite** (local dev)
- **SMTP (Gmail)** — email notifications
- **Railway** — deployment

---

## Quick start (local)

### 1. Clone and install

```bash
git clone https://github.com/Markswag101/fscare-api.git
cd fscare-api
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`. For local dev you only need the SQLite line (no PostgreSQL required):

```env
DATABASE_URL=sqlite:///./fscare.db
SMTP_USER=yourgmail@gmail.com
SMTP_PASS=your_app_password
FSCARE_EMAIL=info@fscare.ng
```

> **Gmail App Password:** Google Account → Security → 2-Step Verification → App Passwords → create one for "Mail".

### 3. Run

```bash
uvicorn app.main:app --reload
```

API is live at `http://localhost:8000`
Docs at `http://localhost:8000/docs`

---

## Deploy to Railway

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "FS Care API"
git remote add origin https://github.com/Markswag101/fscare-api.git
git push -u origin main
```

### 2. Create Railway project

1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. Select your repo
3. Add a **PostgreSQL** plugin (Railway → New → Database → PostgreSQL)
4. Railway auto-injects `DATABASE_URL` — no need to copy it manually

### 3. Set environment variables

In Railway → your service → Variables, add:

| Variable | Value |
|---|---|
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | `yourgmail@gmail.com` |
| `SMTP_PASS` | `your_app_password` |
| `FSCARE_EMAIL` | `info@fscare.ng` |

Railway auto-adds `DATABASE_URL` from the PostgreSQL plugin.

### 4. Deploy

Railway deploys automatically on every push to `main`. Check `/health` to confirm it's up.

---

## API reference

### Hospital endpoints

#### Submit a request
`POST /requests`

```json
{
  "hospital": "Island General Hospital",
  "contact": "Dr. Adeyemi Bello",
  "email": "adeyemi@igh.ng",
  "phone": "08012345678",
  "priority": "urgent",
  "notes": "Ward replenishment needed urgently",
  "items": [
    { "name": "Amoxicillin 500mg", "qty": 200, "unit": "Tablets", "category": "Antibiotics" },
    { "name": "IV Normal Saline", "qty": 50, "unit": "Bottles", "category": "IV Fluids" }
  ]
}
```

Response:
```json
{
  "message": "Request submitted successfully. FS Care has been notified.",
  "request_id": "REQ-001"
}
```

Triggers:
- ✉️ Email to **FS Care** with full request details
- ✉️ Confirmation email to the **hospital**

---

#### Track requests by email
`GET /requests/hospital/{email}`

Returns all requests submitted from that email address.

---

#### Get single request
`GET /requests/{req_id}`

---

### Admin endpoints

#### Get all requests
`GET /admin/requests`

Returns all requests ordered by newest first.

---

#### Action a request
`PATCH /admin/requests/{req_id}/action`

```json
{
  "status": "fulfilled",
  "admin_note": "Items dispatched via courier. ETA 2 working days. Please acknowledge receipt."
}
```

Status options: `pending` | `processing` | `fulfilled` | `cancelled`

Triggers:
- ✉️ Email to the **hospital** with new status + admin note

---

#### Stats dashboard
`GET /admin/stats`

```json
{
  "total": 12,
  "pending": 3,
  "processing": 2,
  "fulfilled": 6,
  "cancelled": 1,
  "urgent_pending": 1
}
```

---

## Email flow

```
Hospital submits request
       │
       ├──► FS Care admin email (new request alert + full item list)
       └──► Hospital confirmation email (request received + ref ID)

FS Care actions request
       │
       └──► Hospital email (status update + admin note)
```

---

## Connecting the frontend

Update your portal's API calls to point to your Railway URL:

```javascript
const API_BASE = "https://fscare-api.up.railway.app";

// Submit request
await fetch(`${API_BASE}/requests`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(formData)
});

// Admin: get all
await fetch(`${API_BASE}/admin/requests`);

// Admin: action
await fetch(`${API_BASE}/admin/requests/${id}/action`, {
  method: "PATCH",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ status, admin_note })
});
```

---

## Project structure

```
fscare-api/
├── app/
│   ├── __init__.py
│   ├── main.py          # Routes and app setup
│   ├── database.py      # SQLAlchemy models + DB connection
│   ├── schemas.py       # Pydantic request/response models
│   └── email_service.py # SMTP email notifications with HTML templates
├── .env.example
├── requirements.txt
├── Procfile
├── railway.json
└── README.md
```
