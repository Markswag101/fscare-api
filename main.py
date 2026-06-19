from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import os

from database import get_db, init_db, Request, RequestItem
from schemas import RequestCreate, RequestOut, ItemOut, ActionRequest, MessageResponse
from email_service import (
    notify_fscare_new_request,
    notify_hospital_status_update,
    notify_hospital_submission_confirmed,
)

app = FastAPI(
    title="FS Care Drug Request API",
    description="Backend for the First Sterling Pharmacy drug request portal",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve portal from static/
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
    return {"message": "FS Care API is running. Portal file not found."}


def _generate_id(db: Session) -> str:
    count = db.query(Request).count()
    return f"REQ-{str(count + 1).zfill(3)}"


def _build_request_out(req: Request, db: Session) -> RequestOut:
    items = db.query(RequestItem).filter(RequestItem.request_id == req.id).all()
    return RequestOut(
        id=req.id,
        hospital=req.hospital,
        contact=req.contact,
        email=req.email,
        phone=req.phone or "",
        priority=req.priority,
        notes=req.notes or "",
        status=req.status,
        admin_note=req.admin_note or "",
        date_submitted=req.date_submitted,
        date_actioned=req.date_actioned,
        items=[ItemOut(name=i.name, qty=i.qty, unit=i.unit, category=i.category) for i in items],
    )


# ─── Hospital Routes ───────────────────────────────────────────────────────────

@app.post("/requests", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def submit_request(payload: RequestCreate, db: Session = Depends(get_db)):
    req_id = _generate_id(db)
    req = Request(
        id=req_id,
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
        db.add(RequestItem(
            request_id=req_id,
            name=item.name,
            qty=item.qty,
            unit=item.unit,
            category=item.category,
        ))
    db.commit()

    items_list = [{"name": i.name, "qty": i.qty, "unit": i.unit, "category": i.category}
                  for i in payload.items]
    notify_fscare_new_request(req_id, payload.hospital, payload.contact,
                               payload.email, payload.priority, items_list, payload.notes or "")
    notify_hospital_submission_confirmed(payload.email, payload.hospital,
                                          payload.contact, req_id, items_list)
    return MessageResponse(
        message="Request submitted successfully. FS Care has been notified.",
        request_id=req_id
    )


@app.get("/requests/hospital/{email}", response_model=List[RequestOut])
def get_hospital_requests(email: str, db: Session = Depends(get_db)):
    reqs = db.query(Request).filter(Request.email == email)\
             .order_by(Request.date_submitted.desc()).all()
    return [_build_request_out(r, db) for r in reqs]


@app.get("/requests/{req_id}", response_model=RequestOut)
def get_request(req_id: str, db: Session = Depends(get_db)):
    req = db.query(Request).filter(Request.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return _build_request_out(req, db)


# ─── Admin Routes ──────────────────────────────────────────────────────────────

@app.get("/admin/requests", response_model=List[RequestOut])
def admin_get_all(db: Session = Depends(get_db)):
    reqs = db.query(Request).order_by(Request.date_submitted.desc()).all()
    return [_build_request_out(r, db) for r in reqs]


@app.patch("/admin/requests/{req_id}/action", response_model=MessageResponse)
def admin_action(req_id: str, payload: ActionRequest, db: Session = Depends(get_db)):
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


@app.get("/admin/stats")
def admin_stats(db: Session = Depends(get_db)):
    return {
        "total":          db.query(Request).count(),
        "pending":        db.query(Request).filter(Request.status == "pending").count(),
        "processing":     db.query(Request).filter(Request.status == "processing").count(),
        "fulfilled":      db.query(Request).filter(Request.status == "fulfilled").count(),
        "cancelled":      db.query(Request).filter(Request.status == "cancelled").count(),
        "urgent_pending": db.query(Request).filter(
            Request.priority == "urgent", Request.status == "pending").count(),
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "FS Care Drug Request API"}
