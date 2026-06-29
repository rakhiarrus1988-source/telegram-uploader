import os
import json
from google.colab import drive

CONFIG_PATH = "/content/drive/MyDrive/telegram_uploader_config.json"
SESSION_PATH = "/content/drive/MyDrive/my_userbot.session"

def mount_drive():
    if not os.path.exists("/content/drive/MyDrive"):
        print("📁 Mounting Google Drive...")
        drive.mount('/content/drive')
    else:
        print("✅ Google Drive already mounted.")

def load_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except:
        return None

def save_config(api_id, api_hash, phone_number):
    data = {"api_id": api_id, "api_hash": api_hash, "phone_number": phone_number}
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except:
        return False

def get_credentials():
    mount_drive()
    config = load_config()
    if config:
        api_id = config.get("api_id")
        api_hash = config.get("api_hash")
        phone_number = config.get("phone_number")
        if api_id and api_hash and phone_number:
            print("🔐 Loaded credentials from Drive.")
            return api_id, api_hash, phone_number, True
    print("\n🆕 First-time setup – enter credentials (will be saved to Drive):")
    api_id = input("Telegram API ID: ").strip()
    api_hash = input("Telegram API Hash: ").strip()
    phone_number = input("Phone number (with country code, e.g., +919876543210): ").strip()
    if not api_id.isdigit() or not api_hash or not phone_number:
        print("❌ Invalid. Try again.")
        return get_credentials()
    save_config(api_id, api_hash, phone_number)
    return api_id, api_hash, phone_number, False