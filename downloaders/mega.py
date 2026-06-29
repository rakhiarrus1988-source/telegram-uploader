import os
import asyncio
import time
from pathlib import Path
from async_mega import Mega
from async_mega.errors import MegaError

async def download_from_mega(link, dest_dir):
    """
    Download from Mega using async-mega library.
    Works with both file and folder links (new or old format).
    Shows real-time progress.
    """
    print(f"⬇️ Downloading from Mega: {link}")
    os.makedirs(dest_dir, exist_ok=True)
    
    try:
        # Create Mega client (anonymous login – works for public links)
        client = Mega()
        await client.login_anonymous()
        print("   🔑 Logged in anonymously.")
    except Exception as e:
        print(f"   ⚠️ Anonymous login failed: {e}")
        # Try without login (some public links work)
        client = Mega()
    
    try:
        # Get file/folder node from link
        node = await client.get_node_from_link(link)
        node_type = node['type']  # 0 = file, 1 = folder
        
        if node_type == 0:
            # ----- Single File -----
            file_name = node['name']
            dest_path = os.path.join(dest_dir, file_name)
            print(f"   📄 Downloading file: {file_name}")
            
            # Download with progress
            start_time = time.time()
            last_update = 0
            
            def progress_callback(current, total):
                nonlocal last_update
                if time.time() - last_update > 0.5:
                    percent = (current / total) * 100
                    elapsed = time.time() - start_time
                    speed = current / elapsed if elapsed > 0 else 0
                    speed_str = f"{speed/(1024**2):.2f} MB/s" if speed > 1024**2 else f"{speed/1024:.2f} KB/s"
                    if speed > 0:
                        remaining = (total - current) / speed
                        eta = time.strftime("%H:%M:%S", time.gmtime(remaining))
                    else:
                        eta = "calculating..."
                    print(f"\r   📥 Downloading: {percent:.1f}% | Speed: {speed_str} | ETA: {eta}    ", end='')
                    last_update = time.time()
            
            await client.download_node(node, dest_dir, callback=progress_callback)
            print()  # newline after progress
            print(f"   ✅ File downloaded: {file_name}")
            return Path(dest_path)
        
        elif node_type == 1:
            # ----- Folder -----
            folder_name = node['name']
            folder_path = os.path.join(dest_dir, folder_name)
            print(f"   📂 Downloading folder: {folder_name}")
            
            # Get all files in folder (recursive)
            files = await client.get_files_in_node(node)
            total_files = len(files)
            print(f"   📁 Found {total_files} file(s) in folder.")
            
            for idx, file_node in enumerate(files, start=1):
                file_name = file_node['name']
                print(f"\n   📄 [{idx}/{total_files}] Downloading: {file_name}")
                
                # Download each file with progress
                start_time = time.time()
                last_update = 0
                
                def progress_callback(current, total):
                    nonlocal last_update
                    if time.time() - last_update > 0.5:
                        percent = (current / total) * 100
                        elapsed = time.time() - start_time
                        speed = current / elapsed if elapsed > 0 else 0
                        speed_str = f"{speed/(1024**2):.2f} MB/s" if speed > 1024**2 else f"{speed/1024:.2f} KB/s"
                        if speed > 0:
                            remaining = (total - current) / speed
                            eta = time.strftime("%H:%M:%S", time.gmtime(remaining))
                        else:
                            eta = "calculating..."
                        print(f"\r      📥 Downloading: {percent:.1f}% | Speed: {speed_str} | ETA: {eta}    ", end='')
                        last_update = time.time()
                
                await client.download_node(file_node, folder_path, callback=progress_callback)
                print()  # newline after progress
                print(f"      ✅ Downloaded: {file_name}")
            
            print(f"\n   ✅ Folder downloaded: {folder_name} (Total: {total_files} files)")
            return Path(folder_path)
        
        else:
            print(f"❌ Unknown node type: {node_type}")
            return None
    
    except MegaError as e:
        print(f"❌ Mega error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None