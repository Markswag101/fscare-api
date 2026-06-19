"""
Email via SendGrid HTTP API.
Sign up free at https://sendgrid.com — 100 emails/day free forever.
Set SENDGRID_API_KEY in your Railway environment variables.
"""
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
FSCARE_EMAIL     = os.getenv("FSCARE_EMAIL", "info@fscare.ng")
FROM_ADDRESS     = os.getenv("FROM_ADDRESS", "")   # must be a verified sender on SendGrid
FSCARE_NAME      = "FS Care"


def _send(to: str, subject: str, html: str):
    if not SENDGRID_API_KEY:
        print(f"[EMAIL SKIPPED] Set SENDGRID_API_KEY in Railway env vars. Would send: {subject} → {to}")
        return
    if not FROM_ADDRESS:
        print(f"[EMAIL SKIPPED] Set FROM_ADDRESS in Railway env vars (must be verified on SendGrid).")
        return
    try:
        message = Mail(
            from_email=(FROM_ADDRESS, FSCARE_NAME),
            to_emails=to,
            subject=subject,
            html_content=html,
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        res = sg.send(message)
        if res.status_code in (200, 201, 202):
            print(f"[EMAIL SENT] {subject} → {to}")
        else:
            print(f"[EMAIL ERROR] SendGrid {res.status_code}: {res.body}")
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")


def _base(title: str, body: str) -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
body{{font-family:Arial,sans-serif;color:#333;background:#f5f5f5;margin:0;padding:0}}
.w{{max-width:600px;margin:32px auto;background:#fff;border-radius:8px;overflow:hidden;border:1px solid #e0e0e0}}
.hd{{background:#185FA5;padding:20px 28px}}
.hd h1{{color:#fff;margin:0;font-size:18px;font-weight:600}}
.hd p{{color:#B5D4F4;margin:4px 0 0;font-size:13px}}
.bd{{padding:24px 28px}}
.bd h2{{font-size:16px;color:#185FA5;margin:0 0 12px}}
.bd p{{font-size:14px;line-height:1.6;margin:0 0 12px}}
table.it{{width:100%;border-collapse:collapse;margin:16px 0;font-size:13px}}
table.it th{{background:#E6F1FB;color:#0C447C;text-align:left;padding:8px 10px}}
table.it td{{padding:8px 10px;border-bottom:1px solid #eee}}
.badge{{display:inline-block;padding:3px 10px;border-radius:100px;font-size:12px;font-weight:600}}
.pending{{background:#FAEEDA;color:#854F0B}}.processing{{background:#E6F1FB;color:#185FA5}}
.fulfilled{{background:#EAF3DE;color:#3B6D11}}.cancelled{{background:#FCEBEB;color:#A32D2D}}
.note{{background:#E6F1FB;border-left:3px solid #185FA5;padding:12px 16px;border-radius:0 6px 6px 0;margin:16px 0;font-size:13px}}
.ft{{background:#f9f9f9;padding:14px 28px;font-size:12px;color:#888;border-top:1px solid #eee}}
</style></head><body>
<div class="w">
  <div class="hd"><h1>&#x2665; FS Care Portal</h1><p>First Sterling Pharmacy</p></div>
  <div class="bd"><h2>{title}</h2>{body}</div>
  <div class="ft">Automated message from FS Care Drug Request Portal.</div>
</div></body></html>"""


def notify_fscare_new_request(req_id, hospital, contact, hospital_email, priority, items, notes):
    urg = '<span class="badge" style="background:#FCEBEB;color:#A32D2D">⚠ URGENT</span>' if priority == "urgent" else ""
    rows = "".join(f"<tr><td>{i['name']}</td><td>{i['qty']}</td><td>{i['unit']}</td><td>{i['category']}</td></tr>" for i in items)
    note_sec = f'<div class="note"><strong>Hospital notes:</strong> {notes}</div>' if notes else ""
    body = f"""
    <p>A new drug request needs your attention. {urg}</p>
    <table style="font-size:14px;width:100%;margin-bottom:12px">
      <tr><td style="color:#666;padding:4px 0;width:140px">Request ID</td><td><strong>{req_id}</strong></td></tr>
      <tr><td style="color:#666;padding:4px 0">Hospital</td><td>{hospital}</td></tr>
      <tr><td style="color:#666;padding:4px 0">Contact</td><td>{contact}</td></tr>
      <tr><td style="color:#666;padding:4px 0">Email</td><td><a href="mailto:{hospital_email}">{hospital_email}</a></td></tr>
    </table>
    <table class="it">
      <thead><tr><th>Item</th><th>Qty</th><th>Unit</th><th>Category</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>{note_sec}
    <p>Log in to the FS Care Admin portal to review and action this request.</p>"""
    _send(
        FSCARE_EMAIL,
        f"[{'URGENT ' if priority == 'urgent' else ''}New Request] {req_id} — {hospital}",
        _base(f"New request from {hospital}", body)
    )


def notify_hospital_submission_confirmed(hospital_email, hospital, contact, req_id, items):
    rows = "".join(f"<tr><td>{i['name']}</td><td>{i['qty']}</td><td>{i['unit']}</td><td>{i['category']}</td></tr>" for i in items)
    body = f"""
    <p>Dear {contact},</p>
    <p>Your drug request has been received by FS Care and will be reviewed shortly.</p>
    <table style="font-size:14px;width:100%;margin-bottom:12px">
      <tr><td style="color:#666;padding:4px 0;width:140px">Request ID</td><td><strong>{req_id}</strong></td></tr>
      <tr><td style="color:#666;padding:4px 0">Hospital</td><td>{hospital}</td></tr>
      <tr><td style="color:#666;padding:4px 0">Status</td><td><span class="badge pending">Pending</span></td></tr>
    </table>
    <table class="it">
      <thead><tr><th>Item</th><th>Qty</th><th>Unit</th><th>Category</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <p>Keep your reference ID <strong>{req_id}</strong>. You will receive an email when FS Care updates your request.</p>"""
    _send(
        hospital_email,
        f"[FS Care] Request Received — {req_id}",
        _base("Request submitted successfully", body)
    )


def notify_hospital_status_update(hospital_email, hospital, contact, req_id, new_status, admin_note, items):
    titles = {
        "processing": "Your request is being processed",
        "fulfilled":  "Your request has been fulfilled ✓",
        "cancelled":  "Your request has been cancelled",
        "pending":    "Your request status was updated",
    }
    rows = "".join(f"<tr><td>{i['name']}</td><td>{i['qty']}</td><td>{i['unit']}</td></tr>" for i in items)
    note_sec = f'<div class="note"><strong>Message from FS Care:</strong><br>{admin_note}</div>' if admin_note else ""
    body = f"""
    <p>Dear {contact},</p>
    <p>Your request <strong>{req_id}</strong> from <strong>{hospital}</strong> has been updated.</p>
    <table style="font-size:14px;width:100%;margin-bottom:12px">
      <tr><td style="color:#666;padding:4px 0;width:140px">New Status</td><td><span class="badge {new_status}">{new_status.capitalize()}</span></td></tr>
      <tr><td style="color:#666;padding:4px 0">Request ID</td><td>{req_id}</td></tr>
    </table>
    <table class="it">
      <thead><tr><th>Item</th><th>Qty</th><th>Unit</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>{note_sec}
    <p>Log in to the hospital portal to track your request or submit a new one.</p>"""
    _send(
        hospital_email,
        f"[FS Care] Request {req_id} — {new_status.capitalize()}",
        _base(titles.get(new_status, "Request updated"), body)
    )
