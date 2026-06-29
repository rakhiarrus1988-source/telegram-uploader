import os
import json
import time
import asyncio
from pathlib import Path
from mega import Mega

# ----- Google Drive path for progress file -----
PROGRESS_FILE = "/content/drive/MyDrive/mega_download_progress.json"

async def download_from_mega(link, dest_dir):
    """
    Download Mega folder with resume support.
    Progress saved to Google Drive.
    """
    print(f"⬇️ Downloading from Mega: {link}")
    os.makedirs(dest_dir, exist_ok=True)
    
    # Mount drive if not already (handled by drive_config)
    # Ensure drive is mounted (assume already done)
    
    # ----- 1. Load progress if exists -----
    progress = load_progress()
    completed_files = progress.get("completed", []) if progress else []
    folder_id = progress.get("folder_id") if progress else None
    
    # ----- 2. Login to Mega -----
    try:
        mega = Mega()
        m = mega.login_anonymous()
        if m is None:
            print("❌ Anonymous login failed.")
            return None
    except Exception as e:
        print(f"❌ Mega login error: {e}")
        return None
    
    # ----- 3. Get node from link -----
    try:
        node = m.get_node_from_link(link)
        if node is None:
            print("❌ Could not get node from link.")
            return None
    except Exception as e:
        print(f"❌ Error getting node: {e}")
        return None
    
    node_type = node.get('type')  # 0=file, 1=folder
    current_folder_id = node.get('id')
    
    # If folder id changed (different link), reset progress
    if folder_id and folder_id != current_folder_id:
        print("⚠️ Folder ID changed. Resetting progress.")
        completed_files = []
        progress = None
    elif not folder_id:
        completed_files = []
    
    # Update folder id in progress
    progress = progress or {}
    progress['folder_id'] = current_folder_id
    
    if node_type == 0:
        # ----- Single file (no resume needed, but we can handle) -----
        file_name = node.get('name')
        dest_path = os.path.join(dest_dir, file_name)
        if os.path.exists(dest_path) and os.path.getsize(dest_path) == node.get('size'):
            print(f"   ✅ File already downloaded: {file_name}")
            return Path(dest_path)
        # Download file (similar to before)
        return await download_file_node(m, node, dest_dir)
    
    elif node_type == 1:
        # ----- Folder -----
        folder_name = node.get('name')
        folder_path = os.path.join(dest_dir, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # Get all files recursively
        all_files = get_all_files(m, node)
        total = len(all_files)
        print(f"   📂 Folder: {folder_name} - {total} files total.")
        
        # Filter out already completed
        remaining = [f for f in all_files if f['name'] not in completed_files]
        if not remaining:
            print("   ✅ All files already downloaded!")
            # Cleanup progress file
            delete_progress()
            return Path(folder_path)
        
        print(f"   📥 {len(remaining)} files remaining to download.")
        
        # Download each remaining file
        for idx, file_node in enumerate(remaining, start=1):
            file_name = file_node['name']
            print(f"\n   📄 [{idx}/{len(remaining)}] Downloading: {file_name}")
            
            success = await download_file_node(m, file_node, folder_path)
            if success:
                completed_files.append(file_name)
                save_progress(completed_files, current_folder_id)
                print(f"   ✅ Completed: {file_name}")
            else:
                # Download failed (quota or other error)
                print(f"   ❌ Failed to download: {file_name}")
                print(f"   💾 Progress saved. Run again to resume.")
                # Save progress and exit
                save_progress(completed_files, current_folder_id)
                return None  # stop further processing
        
        # All files downloaded successfully
        print(f"\n   ✅ Folder fully downloaded: {folder_name}")
        # Delete progress file and cleanup
        delete_progress()
        return Path(folder_path)
    
    else:
        print(f"❌ Unknown node type: {node_type}")
        return None

def get_all_files(m, node):
    """Recursively get all file nodes inside a folder."""
    files = []
    try:
        children = m.get_files_in_node(node)
        for child in children:
            if child['type'] == 0:  # file
                files.append(child)
            elif child['type'] == 1:  # subfolder
                sub_node = m.get_node_by_id(child['id'])
                files.extend(get_all_files(m, sub_node))
    except Exception as e:
        print(f"   ⚠️ Error getting files: {e}")
    return files

async def download_file_node(m, node, dest_dir):
    """Download a single file node with quota handling and retries."""
    file_name = node.get('name')
    dest_path = os.path.join(dest_dir, file_name)
    
    # Check if already exists and size matches
    if os.path.exists(dest_path):
        expected_size = node.get('size')
        actual_size = os.path.getsize(dest_path)
        if expected_size and actual_size == expected_size:
            print(f"      ✅ Already downloaded: {file_name}")
            return True
    
    # Download with retry on quota error
    max_retries = 3
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            def progress_callback(current, total):
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
            
            m.download_node(node, dest_path, progress_callback)
            print()  # newline
            print(f"      ✅ Downloaded: {file_name}")
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "509" in error_msg or "quota" in error_msg:
                print(f"      ⚠️ Quota exceeded. Retrying after 60 seconds... (attempt {attempt+1}/{max_retries})")
                await asyncio.sleep(60)
                continue
            else:
                print(f"      ❌ Error downloading {file_name}: {e}")
                return False
    print(f"      ❌ Failed after {max_retries} attempts.")
    return False

def load_progress():
    """Load progress from Google Drive JSON file."""
    try:
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"⚠️ Could not load progress: {e}")
        return None

def save_progress(completed_files, folder_id):
    """Save progress to Google Drive."""
    data = {
        "completed": completed_files,
        "folder_id": folder_id,
        "timestamp": time.time()
    }
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"⚠️ Could not save progress: {e}")

def delete_progress():
    """Delete progress file after completion."""
    try:
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
            print("   🧹 Progress file deleted.")
    except Exception as e:
        print(f"⚠️ Could not delete progress: {e}")