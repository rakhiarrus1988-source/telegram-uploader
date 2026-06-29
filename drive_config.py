import os
import json
import sys
from google.colab import drive

# ------------------- CONFIG FILE PATH ON DRIVE -------------------
CONFIG_PATH = "/content/drive/MyDrive/telegram_uploader_config.json"
SESSION_PATH = "/content/drive/MyDrive/my_userbot.session"

def mount_drive():
    """Mount Google Drive (only once per session)."""
    if not os.path.exists("/content/drive/MyDrive"):
        print("📁 Mounting Google Drive...")
        drive.mount('/content/drive')
    else:
        print("✅ Google Drive already mounted.")

def load_config():
    """Load saved config from Drive. Returns dict or None."""
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        print("✅ Config loaded from Drive.")
        return config
    except FileNotFoundError:
        print("⚠️ No saved config found. First-time setup required.")
        return None
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None

def save_config(api_id, api_hash, phone_number):
    """Save config to Drive for future runs."""
    config = {
        "api_id": api_id,
        "api_hash": api_hash,
        "phone_number": phone_number
    }
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)
        print("✅ Config saved to Drive successfully!")
        return True
    except Exception as e:
        print(f"❌ Error saving config: {e}")
        return False

def get_credentials():
    """
    Main function to get credentials.
    If config exists on Drive, load silently.
    Else ask user, save, and return.
    """
    mount_drive()
    config = load_config()
    
    if config:
        # ----- SILENT MODE: Use saved credentials -----
        api_id = config.get("api_id")
        api_hash = config.get("api_hash")
        phone_number = config.get("phone_number")
        if api_id and api_hash and phone_number:
            print("🔐 Using saved credentials from Drive.")
            return api_id, api_hash, phone_number, True
        else:
            print("⚠️ Config file is incomplete. Re-enter credentials.")
    
    # ----- FIRST-TIME SETUP: Ask user -----
    print("\n🆕 First-time setup! Please enter your credentials (will be saved to Drive):")
    api_id = input("Telegram API ID: ").strip()
    api_hash = input("Telegram API Hash: ").strip()
    phone_number = input("Your phone number (with country code, e.g., +919876543210): ").strip()
    
    # Validate
    if not api_id.isdigit() or not api_hash or not phone_number:
        print("❌ Invalid credentials. Please try again.")
        return get_credentials()  # Recursively ask again
    
    # Save to Drive
    if save_config(api_id, api_hash, phone_number):
        print("💾 Credentials saved to Drive permanently!")
    else:
        print("⚠️ Could not save config. Will ask again next time.")
    
    return api_id, api_hash, phone_number, False