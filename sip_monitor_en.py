"""
Script for monitoring the availability of SIP devices (phones, gateways)
by periodically sending SIP OPTIONS requests.

Main features:
- Cyclic sending of SIP OPTIONS requests to a list of target IP addresses.
- Uses separate sockets and threads for each request for
  parallel checking and proper response handling.
- Tracks the status of each device ('ok', 'failed', 'unknown') and
  the time of the last status change.
- Generates and sends a summary email report (interval controlled by REPORT_INTERVAL_SECONDS) with a list
  of unavailable ('failed') devices and the duration of their unavailability.
- Supports sending email via SMTP with TLS/authentication or without it.
- Configurable parameters:
    - List of target IP addresses (`TARGET_IPS`)
    - Local IP address for sending (`SOURCE_IP`)
    - Source and destination ports (`SOURCE_PORT`, `TARGET_PORT`)
    - Check interval (`INTERVAL`)
    - Response timeout (`RECEIVE_TIMEOUT`)
    - SMTP server parameters and credentials for email notifications
      (it is recommended to use environment variables for the password).

Dependencies:
- Python 3 standard libraries
- python-dotenv (for .env support)
- requests (for Telegram notifications)

Usage:
1. Set parameters in the "Settings" and "Mail Settings" sections.
   Be sure to specify the correct `SOURCE_IP` and configure SMTP parameters
   if email notifications are enabled (`ENABLE_EMAIL_ALERTS = True`).
   For security, use the SMTP_USER and SMTP_PASS environment variables
   for SMTP login and password.
2. Run the script: python sip_monitor_en.py
3. To stop, press Ctrl+C.

"""
import socket
import time
import uuid
import threading
from email_utils import send_email_alert
from telegram_utils import send_telegram_alert
import os

# --- Settings ---
TARGET_IPS = ["172.16.31.144", "192.168.13.101"]
SOURCE_IP = "192.168.1.100" # <-- SPECIFY YOUR IP! Example
SOURCE_PORT = 5084     # Local port for sending (can be changed)
TARGET_PORT = 5060     # Standard SIP port
INTERVAL = 10          # Sending interval in seconds
USER_AGENT = "Python SIP Monitor"
RECEIVE_TIMEOUT = 2    # Response waiting time in seconds
REPORT_INTERVAL_SECONDS = int(os.environ.get("REPORT_INTERVAL_SECONDS", 3600))  # Default: 3600 seconds (1 hour)
ENABLE_EMAIL_ALERTS = True   # Set to True to enable email notifications
ENABLE_TELEGRAM_ALERTS = True  # Set to True to enable Telegram notifications
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

# --- /Settings ---

# Now we store a dictionary of dictionaries: {'ip': {'state': 'unknown'/'ok'/'failed', 'since': timestamp}}
phone_status = {}

def create_options_message(target_ip, target_port, source_ip, source_port):
    """Creates a SIP OPTIONS text message."""
    call_id = str(uuid.uuid4())
    branch = "z9hG4bK" + str(uuid.uuid4())[:8]
    tag = str(uuid.uuid4())[:8]

    message = (
        f"OPTIONS sip:monitor@{target_ip}:{target_port} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {source_ip}:{source_port};branch={branch};rport\r\n"
        f"Max-Forwards: 70\r\n"
        f"From: <sip:monitor@{source_ip}:{source_port}>;tag={tag}\r\n"
        f"To: <sip:monitor@{target_ip}:{target_port}>\r\n"
        f"Contact: <sip:monitor@{source_ip}:{source_port}>\r\n"
        f"Call-ID: {call_id}\r\n"
        f"CSeq: 1 OPTIONS\r\n"
        f"User-Agent: {USER_AGENT}\r\n"
        f"Accept: application/sdp\r\n"
        f"Content-Length: 0\r\n"
        f"\r\n"
    )
    return message.encode('utf-8')

def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def send_options(target_ip, source_ip_actual):
    """Sends OPTIONS, waits for response, updates the global phone status."""
    global phone_status # Declare that we will use and modify the global variable
    options_message_str = create_options_message(target_ip, TARGET_PORT, source_ip_actual, SOURCE_PORT).decode('utf-8')
    options_message_bytes = options_message_str.encode('utf-8')

    debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] === Sending to {target_ip}:{TARGET_PORT} (from {source_ip_actual}:{SOURCE_PORT} in headers) ===")
    debug_print(options_message_str.strip())
    debug_print(f"========================================")

    sock = None
    current_run_status = 'unknown' # Status for this particular run

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(options_message_bytes, (target_ip, TARGET_PORT))
        debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Packet sent to {target_ip}. Waiting for response ({RECEIVE_TIMEOUT}s)...")

        sock.settimeout(RECEIVE_TIMEOUT)
        try:
            data, addr = sock.recvfrom(2048)
            debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Received response from {addr} for request to {target_ip}")
            debug_print(f"--- Raw data ({len(data)} bytes) ---")
            try:
                 debug_print(data.decode('utf-8', errors='replace'))
            except Exception:
                 debug_print(data)
            debug_print(f"------------------------------------")

            if addr[0] == target_ip:
                try:
                    response = data.decode('utf-8', errors='ignore')
                    status_line = response.splitlines()[0] if response else "EMPTY RESPONSE"
                    if "SIP/2.0 200 OK" in status_line:
                        debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Status: 200 OK from {target_ip}")
                        current_run_status = 'ok'
                    else:
                        debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Status: Not 200 OK from {target_ip}. First line: {status_line}")
                        current_run_status = 'failed'
                except IndexError:
                     debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error: Could not parse response from {target_ip}")
                     current_run_status = 'failed'
                except Exception as parse_e:
                     debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error processing response from {target_ip}: {parse_e}")
                     current_run_status = 'failed'
            else:
                 debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] WARNING: Response from {addr[0]} received on socket waiting for {target_ip}")
                 current_run_status = 'failed'

        except socket.timeout:
            debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Status: No response from {target_ip} (timeout)")
            current_run_status = 'failed'
        except Exception as e:
            debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error receiving/processing response from {target_ip}: {e}")
            current_run_status = 'failed'

    except socket.gaierror as e:
        debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] DNS Error: Could not resolve name or address {target_ip}: {e}")
        current_run_status = 'failed'
    except OSError as e:
         debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Socket error sending/creating for {target_ip}: {e}")
         current_run_status = 'failed'
    except Exception as e:
        debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Unknown error sending/receiving OPTIONS for {target_ip}: {e}")
        current_run_status = 'failed'
    finally:
        if sock:
            sock.close()

    # --- Update status in global dictionary ---
    previous_status_info = phone_status.get(target_ip, {'state': 'unknown', 'since': None})
    previous_state = previous_status_info['state']

    if current_run_status != previous_state:
        # Record new status and the time it was set
        new_timestamp = time.time()
        debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] STATUS CHANGE: {target_ip} changed from '{previous_state}' to '{current_run_status}' at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(new_timestamp))}.")
        phone_status[target_ip] = {'state': current_run_status, 'since': new_timestamp}
    # If status didn't change, do nothing with phone_status

def notify_alert(subject, body, telegram_message=None):
    """
    Sends alert notifications according to enabled channels (email/telegram).
    """
    if ENABLE_EMAIL_ALERTS:
        send_email_alert(subject, body)
    if ENABLE_TELEGRAM_ALERTS and telegram_message:
        send_telegram_alert(telegram_message)

def monitor_loop():
    """Main monitoring loop with report sending."""
    global phone_status # Declare for initialization
    # Initialize status dictionary on start
    phone_status = {ip: {'state': 'unknown', 'since': None} for ip in TARGET_IPS}
    debug_print(f"Status initialization: {phone_status}")
    # Add variable for last report time
    last_report_time = time.time()

    source_ip_actual = SOURCE_IP
    if source_ip_actual == "0.0.0.0" or source_ip_actual == "ВАШ_ЛОКАЛЬНЫЙ_IP": # Check in case IP not replaced
        debug_print("Warning: SOURCE_IP not set or left as '0.0.0.0'. Trying autodetection...")
        try:
            temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_sock.connect(("8.8.8.8", 80))
            source_ip_actual = temp_sock.getsockname()[0]
            debug_print(f"Automatically determined source IP address: {source_ip_actual}")
            temp_sock.close()
        except OSError as e:
            debug_print(f"Could not automatically determine source IP address: {e}. Will use '0.0.0.0'.")
            debug_print("This may lead to the wrong network interface being chosen.")
            source_ip_actual = "0.0.0.0"

    debug_print(f"Monitor started. Source IP for SIP headers: {source_ip_actual}:{SOURCE_PORT}")
    debug_print(f"Target IPs: {', '.join(TARGET_IPS)}")
    debug_print(f"Interval: {INTERVAL} seconds")
    debug_print("-" * 30)

    try:
        while True:
            threads = []
            start_time = time.time()

            for target_ip in TARGET_IPS:
                # We use global phone_status, so don't pass it in args
                thread = threading.Thread(target=send_options, args=(target_ip, source_ip_actual))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            elapsed_time = time.time() - start_time
            wait_time = max(0, INTERVAL - elapsed_time)
            debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Check cycle completed in {elapsed_time:.2f}s.")
            debug_print(f"Current statuses: {phone_status}") # Output updated statuses

            # --- Report logic ---
            current_time = time.time()
            if current_time - last_report_time >= REPORT_INTERVAL_SECONDS:
                debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Checking for report (interval {REPORT_INTERVAL_SECONDS}s)...")
                failed_phones_report_lines = []
                for ip, status_info in phone_status.items():
                    if status_info['state'] == 'failed':
                        failed_since = status_info['since']
                        if failed_since:
                            duration_seconds = current_time - failed_since
                            # Format duration
                            m, s = divmod(duration_seconds, 60)
                            h, m = divmod(m, 60)
                            duration_str = f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
                            failed_since_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(failed_since))
                            failed_phones_report_lines.append(f"- {ip}: unavailable since {failed_since_str} (duration: {duration_str})")
                        else:
                             failed_phones_report_lines.append(f"- {ip}: unavailable (exact failure time unknown)")

                if failed_phones_report_lines:
                    debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Unavailable phones detected. Sending report...")
                    subject = f"SIP Monitor Report: Unavailable phones ({time.strftime('%Y-%m-%d %H:%M')})"
                    body = "The following SIP phones are currently unavailable:\n\n" + "\n".join(failed_phones_report_lines) + "\n\nThe monitor continues to run."
                    telegram_msg = f"SIP Monitor: Unavailable phones:\n" + "\n".join(failed_phones_report_lines)
                    notify_alert(subject, body, telegram_message=telegram_msg)
                else:
                     debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] All monitored phones are available. Report not required.")

                last_report_time = current_time # Update last report time

            # --- /Report logic ---

            debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Waiting {wait_time:.2f}s until next check cycle...")
            debug_print("-" * 30)
            if wait_time > 0:
                time.sleep(wait_time)

    except KeyboardInterrupt:
        debug_print("\nStopping monitor...")

def send_telegram_alert(message):
    """
    Sends a notification message to a Telegram chat using the Telegram Bot API.
    This function is now imported from telegram_utils.py.
    Configure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in telegram_utils.py or via environment variables.
    """
    pass  # The actual implementation is in telegram_utils.py

def send_email_alert(subject, body):
    """
    Sends an email alert via SMTP.
    This function is now imported from the email_utils.py module.
    Please configure all SMTP/email settings in email_utils.py.
    Supports sending with or without TLS/authentication, depending on configuration and credentials.
    """
    pass  # The actual implementation is in email_utils.py

if __name__ == "__main__":
    monitor_loop()
