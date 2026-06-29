import os
import json
import time
import asyncio
import subprocess
from pathlib import Path
from mega import Mega
from .proxy_manager import ProxyManager

PROGRESS_FILE = "/content/drive/MyDrive/mega_download_progress.json"

async def download_from_mega(link, dest_dir):
    print(f"⬇️ Downloading from Mega: {link}")
    os.makedirs(dest_dir, exist_ok=True)
    
    # Load progress from Drive
    progress = load_progress()
    completed_files = progress.get("completed", []) if progress else []
    folder_id = progress.get("folder_id") if progress else None
    
    # Get working proxies
    proxy_mgr = ProxyManager(max_proxies=10, timeout=5)
    proxies = proxy_mgr.get_working_proxies(limit=5)
    
    for proxy_url in proxies:
        try:
            if proxy_url:
                print(f"\n   🔄 Using proxy: {proxy_url}")
                m = Mega().login_anonymous(proxies={'http': proxy_url, 'https': proxy_url})
            else:
                print(f"\n   🔄 Trying without proxy (fallback)")
                m = Mega().login_anonymous()
            
            if m is None:
                print("   ⚠️ Login failed. Trying next...")
                continue
            
            node = m.get_node_from_link(link)
            if node is None:
                print("   ⚠️ Could not get node. Trying next...")
                continue
            
            node_type = node.get('type')  # 0=file, 1=folder
            current_folder_id = node.get('id')
            
            # Reset progress if folder ID changed
            if folder_id and folder_id != current_folder_id:
                print("   ⚠️ Folder ID changed. Resetting progress.")
                completed_files = []
            elif not folder_id:
                completed_files = []
            
            # ----- FILE -----
            if node_type == 0:
                file_name = node.get('name')
                dest_path = os.path.join(dest_dir, file_name)
                print(f"   📄 Downloading file: {file_name}")
                success = await download_file_with_progress(m, node, dest_path)
                if success:
                    return Path(dest_path)
                else:
                    continue
            
            # ----- FOLDER -----
            elif node_type == 1:
                folder_name = node.get('name')
                folder_path = os.path.join(dest_dir, folder_name)
                os.makedirs(folder_path, exist_ok=True)
                
                all_files = get_all_files(m, node)
                total = len(all_files)
                if total == 0:
                    print("   ⚠️ Folder is empty.")
                    return None
                
                remaining = [f for f in all_files if f['name'] not in completed_files]
                if not remaining:
                    print("   ✅ All files already downloaded!")
                    delete_progress()
                    return Path(folder_path)
                
                print(f"   📂 Folder: {folder_name} - {len(remaining)}/{total} files remaining")
                
                success_count = 0
                for idx, file_node in enumerate(remaining, start=1):
                    file_name = file_node['name']
                    print(f"\n   📄 [{idx}/{len(remaining)}] Downloading: {file_name}")
                    dest_path = os.path.join(folder_path, file_name)
                    success = await download_file_with_progress(m, file_node, dest_path)
                    if success:
                        completed_files.append(file_name)
                        save_progress(completed_files, current_folder_id)
                        success_count += 1
                    else:
                        print(f"   ❌ Failed to download: {file_name}")
                        break
                else:
                    print(f"\n   ✅ Folder fully downloaded: {folder_name}")
                    delete_progress()
                    return Path(folder_path)
                
                if success_count < len(remaining):
                    print(f"   ⚠️ Only {success_count}/{len(remaining)} files downloaded. Trying next proxy...")
                    continue
            else:
                print(f"❌ Unknown node type: {node_type}")
                return None
                
        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "509" in error_msg:
                print(f"   ⚠️ Quota exceeded. Trying next proxy...")
            else:
                print(f"   ⚠️ Proxy error: {e}")
            continue
    
    # ----- FALLBACK: megadl (with progress) -----
    print("\n   🔧 All proxies failed. Trying megadl fallback...")
    return await fallback_megadl(link, dest_dir)


async def download_file_with_progress(m, node, dest_path):
    """Download a single file with real-time progress bar."""
    file_name = node.get('name')
    expected_size = node.get('size')
    
    # Check if already exists
    if os.path.exists(dest_path) and expected_size:
        if os.path.getsize(dest_path) == expected_size:
            print(f"      ✅ Already downloaded: {file_name}")
            return True
    
    try:
        start_time = time.time()
        last_update = 0
        
        def progress_callback(current, total):
            nonlocal last_update
            if time.time() - last_update > 0.3:
                percent = (current / total) * 100
                elapsed = time.time() - start_time
                speed = current / elapsed if elapsed > 0 else 0
                
                if speed > 1024**2:
                    speed_str = f"{speed/(1024**2):.2f} MB/s"
                elif speed > 1024:
                    speed_str = f"{speed/1024:.2f} KB/s"
                else:
                    speed_str = f"{speed:.2f} B/s"
                
                if speed > 0:
                    remaining = (total - current) / speed
                    eta = time.strftime("%H:%M:%S", time.gmtime(remaining))
                else:
                    eta = "calculating..."
                
                print(f"\r      📥 Downloading: {percent:.1f}% | Speed: {speed_str} | ETA: {eta}    ", end='')
                last_update = time.time()
        
        # Download with progress
        m.download_node(node, dest_path, progress_callback)
        print()  # newline after progress bar
        print(f"      ✅ Downloaded: {file_name}")
        return True
        
    except Exception as e:
        error_msg = str(e).lower()
        if "quota" in error_msg or "509" in error_msg:
            print(f"      ⚠️ Quota exceeded.")
        else:
            print(f"      ❌ Error downloading {file_name}: {e}")
        return False


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


async def fallback_megadl(link, dest_dir):
    """Fallback to megadl with progress parsing."""
    print("   🔧 Using megadl fallback...")
    
    # Convert link format if needed (optional)
    import re
    converted = link
    match = re.match(r'https?://mega\.nz/folder/([^#]+)#(.+)', link)
    if match:
        converted = f"https://mega.nz/#F!{match.group(1)}!{match.group(2)}"
        print(f"   🔄 Converted to: {converted}")
    
    cmd = f'megadl --path "{dest_dir}" "{converted}"'
    print(f"   🔧 Running: {cmd}")
    
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    output_lines = []
    while True:
        line = process.stdout.readline()
        if not line:
            if process.poll() is not None:
                break
            continue
        line = line.strip()
        output_lines.append(line)
        # Show progress if any
        if "%" in line or "Downloaded" in line:
            print(f"\r   📥 {line}", end='')
    
    print()
    if process.returncode != 0:
        print(f"❌ megadl failed with code {process.returncode}")
        for line in output_lines[-5:]:
            print(f"   {line}")
        return None
    
    all_items = [p for p in Path(dest_dir).iterdir() if not p.name.startswith('.')]
    if not all_items:
        print("❌ No files/folders downloaded.")
        return None
    
    print(f"📁 Downloaded {len(all_items)} item(s).")
    return all_items[0] if len(all_items) == 1 else all_items[0]


def load_progress():
    try:
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def save_progress(completed_files, folder_id):
    data = {"completed": completed_files, "folder_id": folder_id, "timestamp": time.time()}
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except:
        pass

def delete_progress():
    try:
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
    except:
        pass