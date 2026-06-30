import os
import json
import time
import subprocess
import socket
import asyncio
from pathlib import Path
from mega import Mega

PROGRESS_FILE = "/content/drive/MyDrive/mega_download_progress.json"

# ------------------------------------------------------------
# 1. SETUP TOR + PRIVOXY
# ------------------------------------------------------------
def setup_tor_privoxy():
    """Install Tor and Privoxy, start both services."""
    subprocess.run("sudo apt-get update -qq", shell=True)
    subprocess.run("sudo apt-get install -y tor privoxy -qq", shell=True)

    # Configure Privoxy to forward to Tor SOCKS5
    privoxy_config = """
    forward-socks5t   /               127.0.0.1:9050 .
    listen-address  0.0.0.0:8118
    """
    with open("/tmp/privoxy.conf", "w") as f:
        f.write(privoxy_config)

    # Start Tor
    subprocess.Popen("sudo tor --RunAsDaemon 1", shell=True)
    # Start Privoxy with custom config
    subprocess.Popen(f"sudo privoxy --no-daemon /tmp/privoxy.conf", shell=True)

    time.sleep(5)  # Wait for services to initialize
    print("✅ Tor running (SOCKS5 on port 9050)")
    print("✅ Privoxy running (HTTP proxy on port 8118)")

def renew_tor_ip():
    """Send NEWNYM signal to Tor for a fresh IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 9051))
        s.send(b"AUTHENTICATE \"\"\r\nSIGNAL NEWNYM\r\n")
        time.sleep(1)
        s.close()
        print("   🔄 Tor IP renewed.")
        return True
    except Exception as e:
        print(f"   ⚠️ IP renewal failed: {e}")
        return False

# ------------------------------------------------------------
# 2. DOWNLOAD WITH MEGA.PY + PRIVOXY (HTTP PROXY)
# ------------------------------------------------------------
async def download_from_mega(link, dest_dir):
    print(f"⬇️ Downloading from Mega: {link}")
    os.makedirs(dest_dir, exist_ok=True)

    # Setup Tor + Privoxy
    setup_tor_privoxy()

    # Load progress
    progress = load_progress()
    completed_files = progress.get("completed", []) if progress else []
    folder_id = progress.get("folder_id") if progress else None

    # Use Privoxy HTTP proxy (port 8118)
    proxy_dict = {
        'http': 'http://127.0.0.1:8118',
        'https': 'http://127.0.0.1:8118'
    }

    try:
        # Login via Privoxy proxy
        m = Mega().login_anonymous(proxies=proxy_dict)
        if m is None:
            print("❌ Failed to login via Privoxy. Trying without proxy...")
            m = Mega().login_anonymous()
            if m is None:
                return None

        # Get node
        node = m.get_node_from_link(link)
        if node is None:
            print("❌ Could not get node.")
            return None

        node_type = node.get('type')
        current_folder_id = node.get('id')

        if folder_id and folder_id != current_folder_id:
            completed_files = []
        elif not folder_id:
            completed_files = []

        # ----- FILE -----
        if node_type == 0:
            fname = node.get('name')
            dest = os.path.join(dest_dir, fname)
            print(f"   📄 Downloading file: {fname}")
            ok = await download_file_with_progress(m, node, dest)
            if ok:
                return Path(dest)
            else:
                return None

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

            for idx, fnode in enumerate(remaining, start=1):
                fname = fnode['name']
                print(f"\n   📄 [{idx}/{len(remaining)}] Downloading: {fname}")
                dest = os.path.join(folder_path, fname)
                ok = await download_file_with_progress(m, fnode, dest)
                if ok:
                    completed_files.append(fname)
                    save_progress(completed_files, current_folder_id)
                else:
                    # Check if quota error
                    if "quota" in str(ok).lower() or "509" in str(ok):
                        print("   ⚠️ Quota hit! Renewing Tor IP...")
                        renew_tor_ip()
                        await asyncio.sleep(3)
                        # Restart download from beginning (progress saved)
                        return await download_from_mega(link, dest_dir)
                    else:
                        print(f"   ❌ Failed to download {fname}")
                        return None
            else:
                print(f"\n   ✅ Folder fully downloaded: {folder_name}")
                delete_progress()
                return Path(folder_path)

        else:
            print(f"❌ Unknown node type: {node_type}")
            return None

    except Exception as e:
        if "quota" in str(e).lower() or "509" in str(e):
            print("   ⚠️ Quota hit. Renewing Tor IP and retrying...")
            renew_tor_ip()
            await asyncio.sleep(3)
            return await download_from_mega(link, dest_dir)
        else:
            print(f"❌ Download error: {e}")
            return None

# ------------------------------------------------------------
# 3. HELPER: DOWNLOAD FILE WITH PROGRESS
# ------------------------------------------------------------
async def download_file_with_progress(m, node, dest_path):
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
        if "quota" in str(e).lower() or "509" in str(e):
            print(f"      ⚠️ Quota exceeded.")
            return "quota"
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
    except:
        pass
    return files

# ------------------------------------------------------------
# 4. PROGRESS HELPERS
# ------------------------------------------------------------
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