

def notify_fscare_new_registration(name: str, email: str, phone: str, address: str):
    """Alert FS Care when a new hospital registers."""
    body = f"""
    <p>A new hospital has registered on the FS Care portal and is awaiting approval.</p>
    <table style="font-size:14px;width:100%;margin-bottom:12px">
      <tr><td style="color:#666;padding:4px 0;width:140px">Hospital</td><td><strong>{name}</strong></td></tr>
      <tr><td style="color:#666;padding:4px 0">Email</td><td><a href="mailto:{email}">{email}</a></td></tr>
      <tr><td style="color:#666;padding:4px 0">Phone</td><td>{phone or '—'}</td></tr>
      <tr><td style="color:#666;padding:4px 0">Address</td><td>{address or '—'}</td></tr>
    </table>
    <p>Log in to the FS Care Admin portal to approve or reject this registration.</p>"""
    _send(FSCARE_EMAIL, f"[New Registration] {name} — Awaiting Approval",
          _base(f"New hospital registration: {name}", body))


def notify_hospital_approved(hospital_email: str, hospital_name: str):
    """Tell the hospital their account has been approved."""
    body = f"""
    <p>Dear {hospital_name},</p>
    <p>Your registration on the FS Care Drug Request Portal has been <strong>approved</strong>.</p>
    <p>You can now log in and start submitting drug requests directly to FS Care.</p>
    <div class="note">
      Visit the portal, click <strong>Login</strong>, and use the email and password you registered with.
    </div>
    <p>Welcome to FS Care!</p>"""
    _send(hospital_email, "[FS Care] Your account has been approved ✓",
          _base("Account Approved — Welcome to FS Care!", body))
