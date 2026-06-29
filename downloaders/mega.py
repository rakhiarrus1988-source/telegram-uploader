import os
import json
import time
import subprocess
from pathlib import Path
from mega import Mega
from .proxy_manager import ProxyManager

PROGRESS_FILE = "/content/drive/MyDrive/mega_download_progress.json"

async def download_from_mega(link, dest_dir):
    print(f"⬇️ Downloading from Mega: {link}")
    os.makedirs(dest_dir, exist_ok=True)
    
    # Load progress
    progress = load_progress()
    completed = progress.get("completed", []) if progress else []
    folder_id = progress.get("folder_id") if progress else None
    
    # Get proxies
    pm = ProxyManager()
    proxies = pm.get_working_proxies(limit=5)
    
    for proxy_url in proxies:
        try:
            if proxy_url:
                print(f"\n   🔄 Using proxy: {proxy_url}")
                m = Mega().login_anonymous(proxies={'http': proxy_url, 'https': proxy_url})
            else:
                print(f"\n   🔄 Trying without proxy (fallback)")
                m = Mega().login_anonymous()
            
            if not m:
                print("   ⚠️ Login failed.")
                continue
            
            node = m.get_node_from_link(link)
            if not node:
                print("   ⚠️ Could not get node.")
                continue
            
            node_type = node.get('type')
            curr_folder_id = node.get('id')
            
            if folder_id and folder_id != curr_folder_id:
                print("   ⚠️ Folder ID changed. Resetting progress.")
                completed = []
            elif not folder_id:
                completed = []
            
            # ----- FILE -----
            if node_type == 0:
                fname = node.get('name')
                dest = os.path.join(dest_dir, fname)
                print(f"   📄 Downloading file: {fname}")
                ok = await download_file_node(m, node, dest)
                if ok:
                    return Path(dest)
                else:
                    continue
            
            # ----- FOLDER -----
            elif node_type == 1:
                fname = node.get('name')
                folder_path = os.path.join(dest_dir, fname)
                os.makedirs(folder_path, exist_ok=True)
                
                all_files = get_all_files(m, node)
                total = len(all_files)
                if total == 0:
                    print("   ⚠️ Folder is empty.")
                    return None
                
                remaining = [f for f in all_files if f['name'] not in completed]
                if not remaining:
                    print("   ✅ All files already downloaded!")
                    delete_progress()
                    return Path(folder_path)
                
                print(f"   📂 Folder: {fname} - {len(remaining)}/{total} files remaining")
                
                success_count = 0
                for idx, fnode in enumerate(remaining, start=1):
                    fname2 = fnode['name']
                    print(f"\n   📄 [{idx}/{len(remaining)}] Downloading: {fname2}")
                    dest = os.path.join(folder_path, fname2)
                    ok = await download_file_node(m, fnode, dest)
                    if ok:
                        completed.append(fname2)
                        save_progress(completed, curr_folder_id)
                        success_count += 1
                    else:
                        print(f"   ❌ Failed: {fname2}")
                        break
                else:
                    print(f"\n   ✅ Folder fully downloaded: {fname}")
                    delete_progress()
                    return Path(folder_path)
                
                if success_count < len(remaining):
                    print(f"   ⚠️ Only {success_count}/{len(remaining)} done. Trying next proxy...")
                    continue
            else:
                print(f"❌ Unknown node type: {node_type}")
                return None
                
        except Exception as e:
            if "quota" in str(e).lower() or "509" in str(e):
                print("   ⚠️ Quota exceeded. Trying next proxy...")
            else:
                print(f"   ⚠️ Error: {e}")
            continue
    
    # ----- FALLBACK: megadl (if all proxies fail) -----
    print("\n   🔧 All proxies failed. Trying megadl fallback...")
    return await fallback_megadl(link, dest_dir)

async def download_file_node(m, node, dest_path):
    fname = node.get('name')
    expected = node.get('size')
    if os.path.exists(dest_path) and expected and os.path.getsize(dest_path) == expected:
        print(f"      ✅ Already downloaded: {fname}")
        return True
    try:
        start = time.time()
        def cb(current, total):
            pct = (current/total)*100
            elapsed = time.time() - start
            speed = current/elapsed if elapsed else 0
            spd = f"{speed/(1024**2):.2f} MB/s" if speed > 1024**2 else f"{speed/1024:.2f} KB/s"
            eta = time.strftime("%H:%M:%S", time.gmtime((total-current)/speed)) if speed else "calc..."
            print(f"\r      📥 Downloading: {pct:.1f}% | Speed: {spd} | ETA: {eta}    ", end='')
        m.download_node(node, dest_path, cb)
        print()
        print(f"      ✅ Downloaded: {fname}")
        return True
    except Exception as e:
        if "quota" in str(e).lower():
            print(f"      ⚠️ Quota exceeded.")
        else:
            print(f"      ❌ Error: {e}")
        return False

def get_all_files(m, node):
    files = []
    try:
        children = m.get_files_in_node(node)
        for child in children:
            if child['type'] == 0:
                files.append(child)
            elif child['type'] == 1:
                sub = m.get_node_by_id(child['id'])
                files.extend(get_all_files(m, sub))
    except Exception as e:
        print(f"   ⚠️ Error getting files: {e}")
    return files

async def fallback_megadl(link, dest_dir):
    print("   🔧 Using megadl (without --verbose)")
    import subprocess
    cmd = f'megadl --path "{dest_dir}" "{link}"'
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            line = line.strip()
            if "%" in line or "Downloaded" in line:
                print(f"\r   📥 {line}", end='')
    print()
    if process.returncode != 0:
        print(f"❌ megadl failed with code {process.returncode}")
        return None
    items = [p for p in Path(dest_dir).iterdir() if not p.name.startswith('.')]
    return items[0] if items else None

def load_progress():
    try:
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def save_progress(completed, folder_id):
    data = {"completed": completed, "folder_id": folder_id, "timestamp": time.time()}
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