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
from controls import get_user_action, save_control_state, load_control_state

async def main():
    print("\n🔥 HUMAN-LIKE TELEGRAM UPLOAD BOT 🔥")
    
    # ---- CREDENTIALS (Auto from Drive) ----
    api_id, api_hash, phone_number, _ = get_credentials()
    if not api_id or not api_hash or not phone_number:
        print("❌ Invalid credentials.")
        return
    
    # ---- SOURCE ----
    print("\nKis source se laani hai?")
    print("1. Mega\n2. MediaFire\n3. Terabox")
    src = input("Option (1/2/3): ").strip()
    while src not in ['1','2','3']:
        src = input("❌ Invalid: ").strip()
    src_map = {'1':'mega','2':'mediafire','3':'terabox'}
    source = src_map[src]
    
    # ---- FILE OR FOLDER ----
    typ = input("\nFile='1', Folder='2': ").strip()
    while typ not in ['1','2']:
        typ = input("❌ Invalid: ").strip()
    is_folder = (typ == '2')
    
    # ---- LINKS ----
    links = []
    if is_folder:
        link = input("\nFolder link: ").strip()
        links.append(link)
    else:
        try:
            cnt = int(input("Kitni files? (Max 10): ").strip())
            if cnt < 1 or cnt > 10:
                print("❌ 1-10 range.")
                return
        except:
            print("❌ Invalid number.")
            return
        for i in range(cnt):
            links.append(input(f"File {i+1}/{cnt}: ").strip())
    
    download_dir = "downloads_temp"
    os.makedirs(download_dir, exist_ok=True)
    
    # ---- TELEGRAM CLIENT ----
    print("\n[3/4] Connecting to Telegram...")
    client = TelegramClient(SESSION_PATH, int(api_id), api_hash, connection_retries=5)
    
    async with client:
        if not await client.is_user_authorized():
            print(f"📱 Sending code to {phone_number}...")
            await client.send_code_request(phone_number)
            code = input("Enter OTP code: ").strip()
            await client.sign_in(phone_number, code)
            print("✅ Logged in.")
        else:
            print("✅ Already logged in.")
        
        await client.get_me()
        print("[4/4] Processing started...")
        
        all_success = True
        failed_links = []
        current_idx = 0
        
        state = load_control_state()
        if state and state.get('links') == links and state.get('source') == source:
            current_idx = state.get('index', 0)
            print(f"ℹ️ Resuming from link {current_idx+1}/{len(links)}")
        
        while current_idx < len(links):
            link = links[current_idx]
            print(f"\n🔄 Processing {current_idx+1}/{len(links)}")
            print(f"   Link: {link}")
            
            action = await get_user_action("▶️ Enter to continue, 's' skip, 'b' back, 'q' quit: ")
            if action == 'quit':
                print("⏹️ Quitting. Progress saved.")
                save_control_state(data={'index': current_idx, 'links': links, 'source': source})
                break
            elif action == 'skip':
                print(f"⏭️ Skipping.")
                current_idx += 1
                continue
            elif action == 'back':
                if current_idx > 0:
                    current_idx -= 1
                    print(f"⏪ Going back to {current_idx+1}")
                continue
            
            # DOWNLOAD
            if source == 'mega':
                downloaded = await download_from_mega(link, download_dir)
            elif source == 'mediafire':
                downloaded = await download_from_mediafire(link, download_dir)
            else:
                downloaded = await download_from_terabox(link, download_dir)
            
            if downloaded is None:
                print(f"❌ Failed. Skipping.")
                all_success = False
                failed_links.append(link)
                current_idx += 1
                continue
            
            all_items = [p for p in Path(download_dir).iterdir() if not p.name.startswith('.')]
            if is_folder and not downloaded.is_dir() and len(all_items) > 1:
                downloaded = Path(download_dir)
                is_folder = True
            elif is_folder and not downloaded.is_dir() and len(all_items) == 1:
                is_folder = False
            elif not is_folder and downloaded.is_dir():
                is_folder = True
            
            caption = f"Uploaded from {source.capitalize()}! 🚀"
            if is_folder:
                caption += f"\nFolder: {downloaded.name}"
            else:
                caption += f"\nFile: {downloaded.name}"
            
            await process_downloaded_item(client, downloaded, is_folder, caption)
            
            current_idx += 1
            save_control_state(data={'index': current_idx, 'links': links, 'source': source})
        
        # ---- CLEANUP ----
        if all_success and os.path.exists(download_dir):
            if not any(Path(download_dir).iterdir()):
                shutil.rmtree(download_dir, ignore_errors=True)
                print("🧹 Temp folder cleaned.")
        if current_idx >= len(links) and os.path.exists('control_state.json'):
            os.remove('control_state.json')
            print("🧹 Control state removed.")
        print("\n🎉 Process completed!")

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except RuntimeError:
        asyncio.run(main())