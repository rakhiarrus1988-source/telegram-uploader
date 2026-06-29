import os
import sys
import asyncio
import shutil
from pathlib import Path

# Ensure dependencies are installed FIRST
from utils import ensure_dependencies
ensure_dependencies()

# Now import Telethon and our modules
from telethon import TelegramClient
from downloaders import download_from_mega, download_from_mediafire, download_from_terabox
from uploader import process_downloaded_item

# (Optional) Google Drive session persistence – for Colab
# from google.colab import drive
# drive.mount('/content/drive')
# SESSION_PATH = '/content/drive/MyDrive/my_userbot.session'

async def main():
    print("\n🔥 HUMAN-LIKE TELEGRAM UPLOAD BOT 🔥")
    
    # ---- 1. INPUT API CREDENTIALS (Runtime) ----
    api_id = input("Apni Telegram API ID dalein: ").strip()
    api_hash = input("Apna Telegram API Hash dalein: ").strip()
    
    if not api_id.isdigit() or not api_hash:
        print("❌ Invalid credentials. API ID should be numeric, API Hash should be non-empty.")
        return
    
    # ---- 2. Source selection ----
    print("\nKis source se file/folder laani hai?")
    print("1. Mega")
    print("2. MediaFire")
    print("3. Terabox")
    source_choice = input("Option (1/2/3): ").strip()
    while source_choice not in ['1','2','3']:
        source_choice = input("❌ Invalid! Choose 1, 2, or 3: ").strip()
    
    source_map = {'1':'mega', '2':'mediafire', '3':'terabox'}
    source = source_map[source_choice]
    
    # ---- 3. File or folder? ----
    item_type = input("\nKya upload karna hai? (File ke liye '1', Folder ke liye '2'): ").strip()
    while item_type not in ['1','2']:
        item_type = input("❌ Invalid! Enter '1' for file, '2' for folder: ").strip()
    is_folder = (item_type == '2')
    
    # ---- 4. Collect links ----
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
    
    # ---- 5. Temp directory ----
    download_dir = "downloads_temp"
    os.makedirs(download_dir, exist_ok=True)
    
    # ---- 6. Connect to Telegram ----
    print("\n[3/4] Telegram Client connect ho raha hai...")
    session_file = "my_userbot"   # or use SESSION_PATH for Drive
    client = TelegramClient(session_file, int(api_id), api_hash, connection_retries=5)
    
    async with client:
        await client.get_me()
        print("[4/4] Process shuru...")
        
        # ---- 7. Process each link ----
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
            
            # ----- FIX: Check if multiple files downloaded (Mega folder case) -----
            all_items = [p for p in Path(download_dir).iterdir() if not p.name.startswith('.')]
            
            # If user said folder, but downloaded is a file AND there are multiple files in download_dir
            # then treat the entire download_dir as a virtual folder
            if is_folder and not downloaded.is_dir() and len(all_items) > 1:
                print(f"⚠️ Multiple files downloaded (not in a subfolder). Treating entire download_dir as a folder.")
                downloaded = Path(download_dir)
                # Also set is_folder to True (already true, but just to be safe)
                is_folder = True
            elif is_folder and not downloaded.is_dir() and len(all_items) == 1:
                # User said folder, but only one file downloaded – treat as single file
                print("⚠️ You said folder but only one file downloaded. Processing as file.")
                is_folder = False
            elif not is_folder and downloaded.is_dir():
                # User said file, but downloaded a folder – treat as folder
                print("⚠️ You said file but received a folder. Processing as folder.")
                is_folder = True
            # If user said folder and downloaded.is_dir() is True, it's already a folder – do nothing.
            
            caption = f"Uploaded from {source.capitalize()}! 🚀"
            if is_folder:
                caption += f"\nFolder: {downloaded.name}"
            else:
                caption += f"\nFile: {downloaded.name}"
            
            await process_downloaded_item(client, downloaded, is_folder, caption)
        
        # ---- 8. Cleanup ----
        shutil.rmtree(download_dir, ignore_errors=True)
        print("\n🎉 Sab kuch upload ho gaya! 🎉")

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except RuntimeError:
        asyncio.run(main())