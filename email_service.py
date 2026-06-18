import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FSCARE_EMAIL = os.getenv("FSCARE_EMAIL", "info@fscare.ng")
FSCARE_NAME = "FS Care — First Sterling Pharmacy"


def _send(to: str, subject: str, html: str):
    """Send an email. Silently logs on failure so the API never crashes."""
    if not SMTP_USER or not SMTP_PASS:
        print(f"[EMAIL SKIPPED] No SMTP credentials. Would send to {to}: {subject}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{FSCARE_NAME} <{SMTP_USER}>"
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to, msg.as_string())
        print(f"[EMAIL SENT] {subject} → {to}")
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")


def _base_template(title: str, body: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: Arial, sans-serif; color: #333; background: #f5f5f5; margin: 0; padding: 0; }}
  .wrapper {{ max-width: 600px; margin: 32px auto; background: #fff; border-radius: 8px; overflow: hidden; border: 1px solid #e0e0e0; }}
  .header {{ background: #185FA5; padding: 20px 28px; }}
  .header h1 {{ color: #fff; margin: 0; font-size: 18px; font-weight: 600; }}
  .header p {{ color: #B5D4F4; margin: 4px 0 0; font-size: 13px; }}
  .body {{ padding: 24px 28px; }}
  .body h2 {{ font-size: 16px; color: #185FA5; margin: 0 0 12px; }}
  .body p {{ font-size: 14px; line-height: 1.6; margin: 0 0 12px; }}
  .items-table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px; }}
  .items-table th {{ background: #E6F1FB; color: #0C447C; text-align: left; padding: 8px 10px; }}
  .items-table td {{ padding: 8px 10px; border-bottom: 1px solid #eee; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 100px; font-size: 12px; font-weight: 600; }}
  .badge-pending {{ background: #FAEEDA; color: #854F0B; }}
  .badge-processing {{ background: #E6F1FB; color: #185FA5; }}
  .badge-fulfilled {{ background: #EAF3DE; color: #3B6D11; }}
  .badge-cancelled {{ background: #FCEBEB; color: #A32D2D; }}
  .badge-urgent {{ background: #FCEBEB; color: #A32D2D; }}
  .note-box {{ background: #E6F1FB; border-left: 3px solid #185FA5; padding: 12px 16px; border-radius: 0 6px 6px 0; margin: 16px 0; font-size: 13px; }}
  .footer {{ background: #f9f9f9; padding: 14px 28px; font-size: 12px; color: #888; border-top: 1px solid #eee; }}
  .btn {{ display: inline-block; background: #185FA5; color: #fff; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-size: 14px; font-weight: 600; margin: 8px 0; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>&#x2665; FS Care — Drug Request Portal</h1>
    <p>First Sterling Pharmacy</p>
  </div>
  <div class="body">
    <h2>{title}</h2>
    {body}
  </div>
  <div class="footer">
    This is an automated message from the FS Care Drug Request Portal. Do not reply directly to this email.
  </div>
</div>
</body>
</html>
"""


def notify_fscare_new_request(req_id: str, hospital: str, contact: str,
                               hospital_email: str, priority: str,
                               items: list, notes: str):
    """Email FS Care when a new request comes in."""
    priority_badge = f'<span class="badge badge-urgent">&#9888; URGENT</span>' if priority == "urgent" else ""
    items_rows = "".join(
        f"<tr><td>{it['name']}</td><td>{it['qty']}</td><td>{it['unit']}</td><td>{it['category']}</td></tr>"
        for it in items
    )
    notes_section = f'<div class="note-box"><strong>Hospital notes:</strong> {notes}</div>' if notes else ""

    body = f"""
    <p>A new drug request has been submitted and requires your attention. {priority_badge}</p>
    <table style="font-size:14px; width:100%; margin-bottom:12px;">
      <tr><td style="color:#666; padding:4px 0; width:140px;">Request ID</td><td><strong>{req_id}</strong></td></tr>
      <tr><td style="color:#666; padding:4px 0;">Hospital</td><td>{hospital}</td></tr>
      <tr><td style="color:#666; padding:4px 0;">Contact</td><td>{contact}</td></tr>
      <tr><td style="color:#666; padding:4px 0;">Hospital Email</td><td><a href="mailto:{hospital_email}">{hospital_email}</a></td></tr>
    </table>
    <table class="items-table">
      <thead><tr><th>Item</th><th>Qty</th><th>Unit</th><th>Category</th></tr></thead>
      <tbody>{items_rows}</tbody>
    </table>
    {notes_section}
    <p>Log in to the FS Care Admin portal to review and action this request.</p>
    """
    _send(
        to=FSCARE_EMAIL,
        subject=f"[{'URGENT ' if priority == 'urgent' else ''}New Request] {req_id} — {hospital}",
        html=_base_template(f"New request from {hospital}", body)
    )


def notify_hospital_status_update(hospital_email: str, hospital: str,
                                   contact: str, req_id: str,
                                   new_status: str, admin_note: str, items: list):
    """Email the hospital when FS Care updates their request status."""
    status_map = {
        "processing": ("Your request is being processed", "badge-processing"),
        "fulfilled": ("Your request has been fulfilled", "badge-fulfilled"),
        "cancelled": ("Your request has been cancelled", "badge-cancelled"),
        "pending": ("Your request status has been updated", "badge-pending"),
    }
    title_text, badge_class = status_map.get(new_status, ("Request updated", "badge-pending"))
    status_badge = f'<span class="badge {badge_class}">{new_status.capitalize()}</span>'
    items_rows = "".join(
        f"<tr><td>{it['name']}</td><td>{it['qty']}</td><td>{it['unit']}</td></tr>"
        for it in items
    )
    note_section = f'<div class="note-box"><strong>Message from FS Care:</strong><br>{admin_note}</div>' if admin_note else ""

    body = f"""
    <p>Dear {contact},</p>
    <p>Your drug request <strong>{req_id}</strong> from <strong>{hospital}</strong> has been updated.</p>
    <table style="font-size:14px; width:100%; margin-bottom:12px;">
      <tr><td style="color:#666; padding:4px 0; width:140px;">New Status</td><td>{status_badge}</td></tr>
      <tr><td style="color:#666; padding:4px 0;">Request ID</td><td>{req_id}</td></tr>
    </table>
    <table class="items-table">
      <thead><tr><th>Item</th><th>Qty</th><th>Unit</th></tr></thead>
      <tbody>{items_rows}</tbody>
    </table>
    {note_section}
    <p>Log in to the hospital portal to track your request or submit a new one.</p>
    """
    _send(
        to=hospital_email,
        subject=f"[FS Care] Request {req_id} — {new_status.capitalize()}",
        html=_base_template(title_text, body)
    )


def notify_hospital_submission_confirmed(hospital_email: str, hospital: str,
                                          contact: str, req_id: str, items: list):
    """Confirmation email to hospital after they submit a request."""
    items_rows = "".join(
        f"<tr><td>{it['name']}</td><td>{it['qty']}</td><td>{it['unit']}</td><td>{it['category']}</td></tr>"
        for it in items
    )
    body = f"""
    <p>Dear {contact},</p>
    <p>Thank you — your drug request has been received by FS Care. We will review and respond as soon as possible.</p>
    <table style="font-size:14px; width:100%; margin-bottom:12px;">
      <tr><td style="color:#666; padding:4px 0; width:140px;">Request ID</td><td><strong>{req_id}</strong></td></tr>
      <tr><td style="color:#666; padding:4px 0;">Hospital</td><td>{hospital}</td></tr>
      <tr><td style="color:#666; padding:4px 0;">Status</td><td><span class="badge badge-pending">Pending</span></td></tr>
    </table>
    <table class="items-table">
      <thead><tr><th>Item</th><th>Qty</th><th>Unit</th><th>Category</th></tr></thead>
      <tbody>{items_rows}</tbody>
    </table>
    <p>Please keep your request ID <strong>{req_id}</strong> for reference. You will receive an email update when FS Care actions your request.</p>
    """
    _send(
        to=hospital_email,
        subject=f"[FS Care] Request Received — {req_id}",
        html=_base_template("Request submitted successfully", body)
    )
