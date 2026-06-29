import os
import json
import sys

# Try to import Colab's drive module; if not available, set a flag
try:
    from google.colab import drive
    IN_COLAB = True
except ImportError:
    IN_COLAB = False
    drive = None

# ---- CONFIG AND SESSION PATHS ----
# If in Colab, use Drive paths; else use local paths
if IN_COLAB:
    CONFIG_PATH = "/content/drive/MyDrive/telegram_uploader_config.json"
    SESSION_PATH = "/content/drive/MyDrive/my_userbot.session"
else:
    CONFIG_PATH = "telegram_uploader_config.json"
    SESSION_PATH = "my_userbot.session"

def mount_drive():
    """Mount Google Drive only if running in Colab."""
    if not IN_COLAB:
        print("ℹ️ Not in Colab. Using local files for config and session.")
        return
    if not os.path.exists("/content/drive/MyDrive"):
        print("📁 Mounting Google Drive...")
        drive.mount('/content/drive')
    else:
        print("✅ Google Drive already mounted.")

def load_config():
    """Load saved config from Drive or local."""
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        print("✅ Config loaded.")
        return config
    except FileNotFoundError:
        print("⚠️ No saved config found. First-time setup required.")
        return None
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None

def save_config(api_id, api_hash, phone_number):
    """Save config to Drive or local."""
    config = {
        "api_id": api_id,
        "api_hash": api_hash,
        "phone_number": phone_number
    }
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)
        print("✅ Config saved successfully!")
        return True
    except Exception as e:
        print(f"❌ Error saving config: {e}")
        return False

def get_credentials():
    """
    Main function to get credentials.
    If config exists, load silently.
    Else ask user, save, and return.
    """
    mount_drive()  # Safe even if not in Colab
    config = load_config()
    
    if config:
        api_id = config.get("api_id")
        api_hash = config.get("api_hash")
        phone_number = config.get("phone_number")
        if api_id and api_hash and phone_number:
            print("🔐 Using saved credentials.")
            return api_id, api_hash, phone_number, True
        else:
            print("⚠️ Config file is incomplete. Re-enter credentials.")
    
    # First-time setup
    print("\n🆕 First-time setup! Please enter your credentials (will be saved):")
    api_id = input("Telegram API ID: ").strip()
    api_hash = input("Telegram API Hash: ").strip()
    phone_number = input("Your phone number (with country code, e.g., +919876543210): ").strip()
    
    if not api_id.isdigit() or not api_hash or not phone_number:
        print("❌ Invalid credentials. Please try again.")
        return get_credentials()
    
    if save_config(api_id, api_hash, phone_number):
        print("💾 Credentials saved permanently!")
    else:
        print("⚠️ Could not save config. Will ask again next time.")
    
    return api_id, api_hash, phone_number, False