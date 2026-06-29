import os
import sys
import asyncio
import shutil
from pathlib import Path

# --- Import credentials from config.py ---
try:
    from config import API_ID, API_HASH
except ImportError:
    print("❌ config.py nahi mila! Kripya API_ID aur API_HASH config.py mein define karein.")
    sys.exit(1)

# Ensure dependencies are installed FIRST
from utils import ensure_dependencies
ensure_dependencies()

# Now import Telethon and our modules
from telethon import TelegramClient
from downloaders import download_from_mega, download_from_mediafire, download_from_terabox
from uploader import process_downloaded_item

# ---------- (OPTIONAL) Google Drive session persistence ----------
# If you're running on Colab, uncomment the lines below to save session to Drive.
# from google.colab import drive
# drive.mount('/content/drive')
# SESSION_PATH = '/content/drive/MyDrive/my_userbot.session'
# If not using Drive, use a local session file:
SESSION_NAME = "my_userbot"   # or use config.SESSION_NAME if defined

async def main():
    print("\n🔥 HUMAN-LIKE TELEGRAM UPLOAD BOT 🔥")
    print("✅ Credentials loaded from config.py")
    
    # 1. Get API credentials (now from config)
    api_id = API_ID
    api_hash = API_HASH
    
    # 2. Source selection
    print("\nKis source se file/folder laani hai?")
    print("1. Mega")
    print("2. MediaFire")
    print("3. Terabox")
    source_choice = input("Option (1/2/3): ").strip()
    while source_choice not in ['1','2','3']:
        source_choice = input("❌ Invalid! Choose 1, 2, or 3: ").strip()
    
    source_map = {'1':'mega', '2':'mediafire', '3':'terabox'}
    source = source_map[source_choice]
    
    # 3. File or folder?
    item_type = input("\nKya upload karna hai? (File ke liye '1', Folder ke liye '2'): ").strip()
    while item_type not in ['1','2']:
        item_type = input("❌ Invalid! Enter '1' for file, '2' for folder: ").strip()
    is_folder = (item_type == '2')
    
    # 4. Collect links
    links = []
    if is_folder:
        link = input("\nFolder ka link dalein: ").strip()
        links.append(link)
    else:
        try:
            count = int(input("Kitni files upload karni hain? (Max 10): ").strip())
            if count < 1 or count > 10:
                print("❌ Count must be 1-10.")
                return
        except ValueError:
            print("❌ Invalid number.")
            return
        for i in range(count):
            link = input(f"File link {i+1}/{count}: ").strip()
            links.append(link)
    
    # 5. Create temp directory
    download_dir = "downloads_temp"
    os.makedirs(download_dir, exist_ok=True)
    
    # 6. Connect to Telegram with session persistence
    print("\n[3/4] Telegram Client connect ho raha hai...")
    # If you uncommented the Drive lines, use SESSION_PATH instead
    session_file = SESSION_NAME
    client = TelegramClient(session_file, int(api_id), api_hash, connection_retries=5)
    
    async with client:
        await client.get_me()
        print("[4/4] Process shuru...")
        
        # 7. Download and upload each link
        for idx, link in enumerate(links, start=1):
            print(f"\n🔄 Processing {idx}/{len(links)} from {source}...")
            if source == 'mega':
                downloaded = await download_from_mega(link, download_dir)
            elif source == 'mediafire':
                downloaded = await download_from_mediafire(link, download_dir)
            else:  # terabox
                downloaded = await download_from_terabox(link, download_dir)
            
            if downloaded is None:
                print(f"❌ Failed to download {link}. Skipping...")
                continue
            
            # Determine actual type (folder or file)
            actual_is_folder = downloaded.is_dir()
            # Use user's choice but correct if mismatch
            if is_folder and not actual_is_folder:
                print("⚠️ You said folder but received a file. Processing as file.")
                is_folder = False
            elif not is_folder and actual_is_folder:
                print("⚠️ You said file but received a folder. Processing as folder.")
                is_folder = True
            
            caption = f"Uploaded from {source.capitalize()}! 🚀"
            if is_folder:
                caption += f"\nFolder: {downloaded.name}"
            else:
                caption += f"\nFile: {downloaded.name}"
            
            await process_downloaded_item(client, downloaded, is_folder, caption)
        
        # 8. Cleanup
        shutil.rmtree(download_dir, ignore_errors=True)
        print("\n🎉 Sab kuch upload ho gaya! 🎉")

if __name__ == "__main__":
    # For Colab, we handle asyncio properly
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except RuntimeError:
        asyncio.run(main())