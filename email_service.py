import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
FSCARE_EMAIL     = os.getenv("FSCARE_EMAIL", "info@fscare.ng")
FROM_ADDRESS     = os.getenv("FROM_ADDRESS", "")
FSCARE_NAME      = "FS Care"


def _send(to, subject, html):
    if not SENDGRID_API_KEY or not FROM_ADDRESS:
        print(f"[EMAIL SKIPPED] {subject} -> {to}")
        return
    try:
        msg = Mail(from_email=(FROM_ADDRESS, FSCARE_NAME), to_emails=to, subject=subject, html_content=html)
        res = SendGridAPIClient(SENDGRID_API_KEY).send(msg)
        print(f"[EMAIL SENT] {subject} -> {to}" if res.status_code in (200,201,202) else f"[EMAIL ERROR] {res.status_code}")
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")


def _base(title, body):
    return f"""<html><body style="font-family:Arial,sans-serif;background:#f5f5f5">
<div style="max-width:600px;margin:32px auto;background:#fff;border-radius:8px;border:1px solid #e0e0e0">
<div style="background:#185FA5;padding:20px 28px"><h1 style="color:#fff;margin:0;font-size:18px">FS Care Portal</h1><p style="color:#B5D4F4;margin:4px 0 0;font-size:13px">First Sterling Pharmacy</p></div>
<div style="padding:24px 28px"><h2 style="color:#185FA5;font-size:16px;margin:0 0 12px">{title}</h2>{body}</div>
<div style="background:#f9f9f9;padding:14px 28px;font-size:12px;color:#888;border-top:1px solid #eee">Automated message from FS Care Drug Request Portal.</div>
</div></body></html>"""


def notify_fscare_new_request(req_id, hospital, contact, hospital_email, priority, items, notes):
    urg = "<b style='color:#A32D2D'>⚠ URGENT</b>" if priority == "urgent" else ""
    rows = "".join(f"<tr><td style='padding:7px 10px;border-bottom:1px solid #eee'>{i['name']}</td><td style='padding:7px 10px;border-bottom:1px solid #eee'>{i['qty']}</td><td style='padding:7px 10px;border-bottom:1px solid #eee'>{i['unit']}</td><td style='padding:7px 10px;border-bottom:1px solid #eee'>{i['category']}</td></tr>" for i in items)
    note_sec = f"<div style='background:#E6F1FB;border-left:3px solid #185FA5;padding:12px;margin:16px 0;font-size:13px'><b>Notes:</b> {notes}</div>" if notes else ""
    body = f"<p>New drug request needs attention. {urg}</p><table style='width:100%;font-size:14px;margin-bottom:12px'><tr><td style='color:#666;padding:4px 0;width:130px'>Request ID</td><td><b>{req_id}</b></td></tr><tr><td style='color:#666;padding:4px 0'>Hospital</td><td>{hospital}</td></tr><tr><td style='color:#666;padding:4px 0'>Contact</td><td>{contact}</td></tr><tr><td style='color:#666;padding:4px 0'>Email</td><td>{hospital_email}</td></tr></table><table style='width:100%;border-collapse:collapse;font-size:13px;margin:16px 0'><thead><tr style='background:#E6F1FB'><th style='text-align:left;padding:8px 10px'>Item</th><th style='text-align:left;padding:8px 10px'>Qty</th><th style='text-align:left;padding:8px 10px'>Unit</th><th style='text-align:left;padding:8px 10px'>Category</th></tr></thead><tbody>{rows}</tbody></table>{note_sec}<p>Log in to FS Care Admin portal to action this request.</p>"
    _send(FSCARE_EMAIL, f"[{'URGENT ' if priority=='urgent' else ''}New Request] {req_id} - {hospital}", _base(f"New request from {hospital}", body))


def notify_hospital_submission_confirmed(hospital_email, hospital, contact, req_id, items):
    rows = "".join(f"<tr><td style='padding:7px 10px;border-bottom:1px solid #eee'>{i['name']}</td><td style='padding:7px 10px;border-bottom:1px solid #eee'>{i['qty']}</td><td style='padding:7px 10px;border-bottom:1px solid #eee'>{i['unit']}</td></tr>" for i in items)
    body = f"<p>Dear {contact},</p><p>Your drug request has been received by FS Care and will be reviewed shortly.</p><table style='width:100%;font-size:14px;margin-bottom:12px'><tr><td style='color:#666;padding:4px 0;width:130px'>Request ID</td><td><b>{req_id}</b></td></tr><tr><td style='color:#666;padding:4px 0'>Hospital</td><td>{hospital}</td></tr><tr><td style='color:#666;padding:4px 0'>Status</td><td><span style='background:#FAEEDA;color:#854F0B;padding:2px 8px;border-radius:100px;font-size:12px;font-weight:600'>Pending</span></td></tr></table><table style='width:100%;border-collapse:collapse;font-size:13px;margin:16px 0'><thead><tr style='background:#E6F1FB'><th style='text-align:left;padding:8px 10px'>Item</th><th style='text-align:left;padding:8px 10px'>Qty</th><th style='text-align:left;padding:8px 10px'>Unit</th></tr></thead><tbody>{rows}</tbody></table><p>Keep your reference ID <b>{req_id}</b>. You will receive an email when FS Care updates your request.</p>"
    _send(hospital_email, f"[FS Care] Request Received - {req_id}", _base("Request submitted successfully", body))


def notify_hospital_status_update(hospital_email, hospital, contact, req_id, new_status, admin_note, items):
    titles = {"processing":"Your request is being processed","fulfilled":"Your request has been fulfilled","cancelled":"Your request has been cancelled","pending":"Your request status was updated"}
    rows = "".join(f"<tr><td style='padding:7px 10px;border-bottom:1px solid #eee'>{i['name']}</td><td style='padding:7px 10px;border-bottom:1px solid #eee'>{i['qty']}</td><td style='padding:7px 10px;border-bottom:1px solid #eee'>{i['unit']}</td></tr>" for i in items)
    note_sec = f"<div style='background:#E6F1FB;border-left:3px solid #185FA5;padding:12px;margin:16px 0;font-size:13px'><b>Message from FS Care:</b><br>{admin_note}</div>" if admin_note else ""
    body = f"<p>Dear {contact},</p><p>Your request <b>{req_id}</b> from <b>{hospital}</b> has been updated to <b>{new_status}</b>.</p><table style='width:100%;border-collapse:collapse;font-size:13px;margin:16px 0'><thead><tr style='background:#E6F1FB'><th style='text-align:left;padding:8px 10px'>Item</th><th style='text-align:left;padding:8px 10px'>Qty</th><th style='text-align:left;padding:8px 10px'>Unit</th></tr></thead><tbody>{rows}</tbody></table>{note_sec}"
    _send(hospital_email, f"[FS Care] Request {req_id} - {new_status.capitalize()}", _base(titles.get(new_status, "Request updated"), body))


def notify_fscare_new_registration(name, email, phone, address):
    body = f"<p>A new hospital has registered and is awaiting approval.</p><table style='width:100%;font-size:14px;margin-bottom:12px'><tr><td style='color:#666;padding:4px 0;width:130px'>Hospital</td><td><b>{name}</b></td></tr><tr><td style='color:#666;padding:4px 0'>Email</td><td>{email}</td></tr><tr><td style='color:#666;padding:4px 0'>Phone</td><td>{phone or '-'}</td></tr><tr><td style='color:#666;padding:4px 0'>Address</td><td>{address or '-'}</td></tr></table><p>Log in to the FS Care Admin portal to approve or reject.</p>"
    _send(FSCARE_EMAIL, f"[New Registration] {name} - Awaiting Approval", _base(f"New hospital: {name}", body))


def notify_hospital_approved(hospital_email, hospital_name):
    body = f"<p>Dear {hospital_name},</p><p>Your registration on the FS Care Drug Request Portal has been <b>approved</b>.</p><p>You can now log in and start submitting drug requests to FS Care.</p><div style='background:#E6F1FB;border-left:3px solid #185FA5;padding:12px;margin:16px 0;font-size:13px'>Visit the portal and sign in with your registered email and password.</div><p>Welcome to FS Care!</p>"
    _send(hospital_email, "[FS Care] Your account has been approved", _base("Account Approved - Welcome!", body))
