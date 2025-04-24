import os
import requests
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def send_telegram_alert(message):
    """
    Sends a notification message to a Telegram chat using the Telegram Bot API.
    Configure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in the .env file for security.
    Example usage:
        send_telegram_alert("Device is unavailable!")
    """
    debug_print(f"[DEBUG][TELEGRAM] Called send_telegram_alert with message: {message}")
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    debug_print(f"[DEBUG][TELEGRAM] TELEGRAM_BOT_TOKEN set: {bool(TELEGRAM_BOT_TOKEN)}, TELEGRAM_CHAT_ID set: {bool(TELEGRAM_CHAT_ID)}")

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID or TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN" or TELEGRAM_CHAT_ID == "YOUR_CHAT_ID":
        debug_print("[DEBUG][TELEGRAM] Bot token or chat ID not set. Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in the .env file.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        debug_print(f"[DEBUG][TELEGRAM] Sending POST to {url} with payload: {payload}")
        response = requests.post(url, data=payload, timeout=10)
        debug_print(f"[DEBUG][TELEGRAM] Response code: {response.status_code}, text: {response.text}")
        if response.status_code == 200:
            print("[TELEGRAM] Notification sent successfully.")
        else:
            print(f"[TELEGRAM] Failed to send notification: {response.text}")
    except Exception as e:
        print(f"[TELEGRAM] Exception occurred: {e}")

if __name__ == "__main__":
    debug_print("[DEBUG][TELEGRAM] Running telegram_utils.py as a script. Sending test message...")
    send_telegram_alert("This is a test message from telegram_utils.py. If you received this, Telegram notifications are working.")
