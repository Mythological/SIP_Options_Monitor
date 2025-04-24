import smtplib
import time
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

# --- Email settings (shared, from .env) ---
ENABLE_EMAIL_ALERTS = True # Set to False to disable alerts
SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USERNAME = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASS")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def send_email_alert(subject, body):
    import smtplib
    from email.mime.text import MIMEText
    import os

    debug_print("[DEBUG][EMAIL] SMTP_SERVER:", SMTP_SERVER)
    debug_print("[DEBUG][EMAIL] SMTP_PORT:", SMTP_PORT)
    debug_print("[DEBUG][EMAIL] SENDER_EMAIL:", SENDER_EMAIL)
    debug_print("[DEBUG][EMAIL] RECIPIENT_EMAIL:", RECIPIENT_EMAIL)
    debug_print("[DEBUG][EMAIL] SMTP_USERNAME:", SMTP_USERNAME)
    debug_print("[DEBUG][EMAIL] SMTP_PASSWORD set:", bool(SMTP_PASSWORD))

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL

    try:
        if SMTP_PASSWORD and SMTP_PASSWORD != "" and SMTP_USERNAME:
            debug_print("[DEBUG][EMAIL] Using TLS and authentication mode.")
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(SENDER_EMAIL, [RECIPIENT_EMAIL], msg.as_string())
        else:
            debug_print("[DEBUG][EMAIL] Using plain SMTP mode (no auth, no TLS).")
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.sendmail(SENDER_EMAIL, [RECIPIENT_EMAIL], msg.as_string())
        debug_print(f'[EMAIL][DEBUG] Email notification sent! Subject: {subject}')
    except Exception as e:
        debug_print(f'[EMAIL][ERROR] Failed to send email: {e}')

if __name__ == "__main__":
    debug_print("[DEBUG][EMAIL] Running email_utils.py as a script. Sending test email...")
    send_email_alert("Test Email from SIP Monitor", "This is a test email from email_utils.py. If you received this, email notifications are working.")
