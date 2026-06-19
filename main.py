from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import os, uuid

from database import get_db, init_db, Request, RequestItem, Hospital
from schemas import (
    HospitalRegister, LoginRequest, TokenResponse,
    RequestCreate, RequestOut, ItemOut,
    ActionRequest, MessageResponse, HospitalOut,
)
from auth import (
    hash_password, verify_password, create_token,
    get_current_user, require_admin, require_hospital,
)
from email_service import (
    notify_fscare_new_request,
    notify_hospital_status_update,
    notify_hospital_submission_confirmed,
    notify_fscare_new_registration,
    notify_hospital_approved,
)

ADMIN_EMAIL    = os.getenv("ADMIN_EMAIL", "admin@fscare.ng")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "fscare2026admin")

app = FastAPI(title="FS Care Drug Request API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/", include_in_schema=False)
def serve_portal():
    index = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"message": "FS Care API running"}


# ── Auth Routes ───────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=MessageResponse, status_code=201)
def register_hospital(payload: HospitalRegister, db: Session = Depends(get_db)):
    existing = db.query(Hospital).filter(Hospital.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hospital = Hospital(
        id=str(uuid.uuid4()),
        name=payload.name,
        email=payload.email,
        phone=payload.phone or "",
        address=payload.address or "",
        password_hash=hash_password(payload.password),
        approved=False,
    )
    db.add(hospital)
    db.commit()
    notify_fscare_new_registration(hospital.name, hospital.email, hospital.phone, hospital.address)
    return MessageResponse(message="Registration submitted. FS Care will review and approve your account.")


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    # Admin login
    if payload.email == ADMIN_EMAIL:
        if payload.password != ADMIN_PASSWORD:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_token({"role": "admin", "email": ADMIN_EMAIL})
        return TokenResponse(access_token=token, role="admin", name="FS Care Admin")

    # Hospital login
    hospital = db.query(Hospital).filter(Hospital.email == payload.email).first()
    if not hospital or not verify_password(payload.password, hospital.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not hospital.approved:
        raise HTTPException(status_code=403, detail="Your account is pending approval by FS Care")
    token = create_token({"role": "hospital", "hospital_id": hospital.id, "email": hospital.email})
    return TokenResponse(access_token=token, role="hospital", name=hospital.name, approved=hospital.approved)


# ── Hospital Routes ───────────────────────────────────────────────────────────

@app.post("/requests", response_model=MessageResponse, status_code=201)
def submit_request(
    payload: RequestCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Allow both authenticated hospitals and admin to submit
    req_id = f"REQ-{str(db.query(Request).count() + 1).zfill(3)}"
    req = Request(
        id=req_id,
        hospital_id=current_user.get("hospital_id"),
        hospital=payload.hospital,
        contact=payload.contact,
        email=payload.email,
        phone=payload.phone or "",
        priority=payload.priority,
        notes=payload.notes or "",
        status="pending",
    )
    db.add(req)
    db.flush()
    for item in payload.items:
        db.add(RequestItem(request_id=req_id, name=item.name,
                           qty=item.qty, unit=item.unit, category=item.category))
    db.commit()
    items_list = [{"name": i.name, "qty": i.qty, "unit": i.unit, "category": i.category}
                  for i in payload.items]
    notify_fscare_new_request(req_id, payload.hospital, payload.contact,
                               payload.email, payload.priority, items_list, payload.notes or "")
    notify_hospital_submission_confirmed(payload.email, payload.hospital,
                                          payload.contact, req_id, items_list)
    return MessageResponse(message="Request submitted. FS Care has been notified.", request_id=req_id)


@app.get("/requests/mine", response_model=List[RequestOut])
def get_my_requests(
    db: Session = Depends(get_db),
    hospital: Hospital = Depends(require_hospital),
):
    reqs = db.query(Request).filter(Request.hospital_id == hospital.id)\
             .order_by(Request.date_submitted.desc()).all()
    return [_build_out(r, db) for r in reqs]


# ── Admin Routes ──────────────────────────────────────────────────────────────

@app.get("/admin/requests", response_model=List[RequestOut])
def admin_get_all(db: Session = Depends(get_db), _=Depends(require_admin)):
    return [_build_out(r, db) for r in db.query(Request).order_by(Request.date_submitted.desc()).all()]


@app.patch("/admin/requests/{req_id}/action", response_model=MessageResponse)
def admin_action(req_id: str, payload: ActionRequest,
                 db: Session = Depends(get_db), _=Depends(require_admin)):
    req = db.query(Request).filter(Request.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    req.status = payload.status
    req.admin_note = payload.admin_note or ""
    req.date_actioned = datetime.utcnow()
    db.commit()
    items = db.query(RequestItem).filter(RequestItem.request_id == req_id).all()
    items_list = [{"name": i.name, "qty": i.qty, "unit": i.unit} for i in items]
    notify_hospital_status_update(req.email, req.hospital, req.contact,
                                   req_id, payload.status, payload.admin_note or "", items_list)
    return MessageResponse(message=f"Request {req_id} updated to '{payload.status}'. Hospital notified.")


@app.get("/admin/hospitals", response_model=List[HospitalOut])
def admin_get_hospitals(db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(Hospital).order_by(Hospital.date_registered.desc()).all()


@app.patch("/admin/hospitals/{hospital_id}/approve", response_model=MessageResponse)
def admin_approve_hospital(hospital_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    hospital.approved = True
    db.commit()
    notify_hospital_approved(hospital.email, hospital.name)
    return MessageResponse(message=f"{hospital.name} approved successfully.")


@app.delete("/admin/hospitals/{hospital_id}", response_model=MessageResponse)
def admin_reject_hospital(hospital_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    db.delete(hospital)
    db.commit()
    return MessageResponse(message="Hospital registration rejected and removed.")


@app.get("/admin/stats")
def admin_stats(db: Session = Depends(get_db), _=Depends(require_admin)):
    return {
        "total":           db.query(Request).count(),
        "pending":         db.query(Request).filter(Request.status == "pending").count(),
        "processing":      db.query(Request).filter(Request.status == "processing").count(),
        "fulfilled":       db.query(Request).filter(Request.status == "fulfilled").count(),
        "cancelled":       db.query(Request).filter(Request.status == "cancelled").count(),
        "urgent_pending":  db.query(Request).filter(Request.priority == "urgent", Request.status == "pending").count(),
        "hospitals_total": db.query(Hospital).count(),
        "hospitals_pending": db.query(Hospital).filter(Hospital.approved == False).count(),
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "FS Care Drug Request API v2"}


# ── Helper ────────────────────────────────────────────────────────────────────
def _build_out(req: Request, db: Session) -> RequestOut:
    items = db.query(RequestItem).filter(RequestItem.request_id == req.id).all()
    return RequestOut(
        id=req.id, hospital=req.hospital, contact=req.contact,
        email=req.email, phone=req.phone or "", priority=req.priority,
        notes=req.notes or "", status=req.status, admin_note=req.admin_note or "",
        date_submitted=req.date_submitted, date_actioned=req.date_actioned,
        items=[ItemOut(name=i.name, qty=i.qty, unit=i.unit, category=i.category) for i in items],
    )
