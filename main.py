import os
import sys
import asyncio
import shutil
from pathlib import Path

from utils import ensure_dependencies
ensure_dependencies()

from telethon import TelegramClient
from downloaders import download_from_mega, download_from_mediafire, download_from_terabox
from uploader import process_downloaded_item
from drive_config import get_credentials, SESSION_PATH

async def main():
    print("\n🔥 HUMAN-LIKE TELEGRAM UPLOAD BOT 🔥")
    api_id, api_hash, phone_number, config_loaded = get_credentials()
    if not api_id or not api_hash or not phone_number:
        print("❌ Invalid credentials. Exiting.")
        return
    
    print("\nKis source se file/folder laani hai?")
    print("1. Mega\n2. MediaFire\n3. Terabox")
    source_choice = input("Option (1/2/3): ").strip()
    while source_choice not in ['1','2','3']:
        source_choice = input("❌ Invalid! Choose 1, 2, or 3: ").strip()
    source_map = {'1':'mega', '2':'mediafire', '3':'terabox'}
    source = source_map[source_choice]
    
    item_type = input("\nKya upload karna hai? (File='1', Folder='2'): ").strip()
    while item_type not in ['1','2']:
        item_type = input("❌ Invalid! Enter '1' for file, '2' for folder: ").strip()
    is_folder = (item_type == '2')
    
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
    
    download_dir = "downloads_temp"
    os.makedirs(download_dir, exist_ok=True)
    
    print("\n[3/4] Telegram Client connect ho raha hai...")
    client = TelegramClient(SESSION_PATH, int(api_id), api_hash, connection_retries=5)
    
    async with client:
        if not await client.is_user_authorized():
            print(f"📱 First-time login. Sending code to {phone_number}...")
            await client.send_code_request(phone_number)
            code = input("Enter the Telegram OTP code you received: ").strip()
            await client.sign_in(phone_number, code)
            print("✅ Logged in successfully!")
        else:
            print("✅ Already logged in (session found).")
        
        await client.get_me()
        print("[4/4] Process shuru...")
        
        for idx, link in enumerate(links, start=1):
            print(f"\n🔄 Processing {idx}/{len(links)} from {source}...")
            if source == 'mega':
                downloaded = await download_from_mega(link, download_dir)
            elif source == 'mediafire':
                downloaded = await download_from_mediafire(link, download_dir)
            else:
                downloaded = await download_from_terabox(link, download_dir)
            
            if downloaded is None:
                print(f"❌ Failed to download {link}. Skipping...")
                continue
            
            all_items = [p for p in Path(download_dir).iterdir() if not p.name.startswith('.')]
            if is_folder and not downloaded.is_dir() and len(all_items) > 1:
                print(f"⚠️ Multiple files downloaded. Treating entire download_dir as a folder.")
                downloaded = Path(download_dir)
                is_folder = True
            elif is_folder and not downloaded.is_dir() and len(all_items) == 1:
                print("⚠️ You said folder but only one file downloaded. Processing as file.")
                is_folder = False
            elif not is_folder and downloaded.is_dir():
                print("⚠️ You said file but received a folder. Processing as folder.")
                is_folder = True
            
            caption = f"Uploaded from {source.capitalize()}! 🚀"
            if is_folder:
                caption += f"\nFolder: {downloaded.name}"
            else:
                caption += f"\nFile: {downloaded.name}"
            
            await process_downloaded_item(client, downloaded, is_folder, caption)
        
        shutil.rmtree(download_dir, ignore_errors=True)
        print("\n🎉 Sab kuch upload ho gaya! 🎉")

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except RuntimeError:
        asyncio.run(main())