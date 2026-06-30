import os
import json
import time
import subprocess
import socket
import asyncio
import requests
import re
from pathlib import Path

PROGRESS_FILE = "/content/drive/MyDrive/mega_download_progress.json"
MEGABASTERD_JAR = "/tmp/MegaBasterd.jar"

# ------------------------------------------------------------
# 1. SETUP: Java + MegaBasterd JAR + Tor + Privoxy
# ------------------------------------------------------------
def setup_java_megabasterd():
    """Download MegaBasterd JAR if not present."""
    if os.path.exists(MEGABASTERD_JAR):
        return True
    print("📦 Downloading MegaBasterd CLI...")
    url = "https://github.com/tonikelz/MegaBasterd/releases/download/v4.8.2/MegaBasterd.jar"
    try:
        r = requests.get(url, stream=True)
        with open(MEGABASTERD_JAR, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print("✅ MegaBasterd downloaded.")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def setup_tor_privoxy():
    """Start Tor + Privoxy."""
    subprocess.run("sudo apt-get update -qq", shell=True)
    subprocess.run("sudo apt-get install -y tor privoxy -qq", shell=True)

    privoxy_conf = """
    forward-socks5t   /               127.0.0.1:9050 .
    listen-address  0.0.0.0:8118
    """
    with open("/tmp/privoxy.conf", "w") as f:
        f.write(privoxy_conf)

    subprocess.Popen("sudo tor --RunAsDaemon 1", shell=True)
    subprocess.Popen(f"sudo privoxy --no-daemon /tmp/privoxy.conf", shell=True)
    time.sleep(5)
    print("✅ Tor + Privoxy ready (HTTP proxy on 8118).")

def renew_tor_ip():
    """Get fresh IP from Tor."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 9051))
        s.send(b"AUTHENTICATE \"\"\r\nSIGNAL NEWNYM\r\n")
        time.sleep(1)
        s.close()
        print("   🔄 Tor IP renewed.")
        return True
    except Exception as e:
        print(f"   ⚠️ Renewal failed: {e}")
        return False

# ------------------------------------------------------------
# 2. MEGA DOWNLOAD VIA MEGABASTERD CLI
# ------------------------------------------------------------
async def download_from_mega(link, dest_dir):
    print(f"⬇️ Downloading from Mega: {link}")
    os.makedirs(dest_dir, exist_ok=True)

    # Setup once per session
    if not setup_java_megabasterd():
        return None
    setup_tor_privoxy()

    # Load progress (folder ID + completed files)
    progress = load_progress()
    completed_files = progress.get("completed", []) if progress else []
    folder_id = progress.get("folder_id") if progress else None

    # Build MegaBasterd command
    cmd = [
        "java", "-jar", MEGABASTERD_JAR,
        "-headless",
        "-proxy=http://127.0.0.1:8118",
        f"-download={link}",
        f"-output={dest_dir}",
        "-resume"
    ]

    print("   🔧 Running MegaBasterd CLI...")
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    output_lines = []
    quota_hit = False
    start_time = time.time()

    while True:
        line = process.stdout.readline()
        if not line:
            if process.poll() is not None:
                break
            continue
        line = line.strip()
        output_lines.append(line)

        # Quota detection
        if "quota" in line.lower() or "509" in line:
            print("\n   ⚠️ Quota hit! Renewing IP...")
            quota_hit = True
            renew_tor_ip()
            process.kill()
            break

        # Progress: e.g., "Progress: 45%"
        if "progress" in line.lower() and "%" in line:
            pct_match = re.search(r'(\d+)%', line)
            if pct_match:
                pct = int(pct_match.group(1))
                elapsed = time.time() - start_time
                print(f"\r   📥 Downloading: {pct}% | Time: {elapsed:.0f}s", end='')

    print()  # newline

    if quota_hit:
        print("   🔄 Resuming after IP change...")
        await asyncio.sleep(3)
        return await download_from_mega(link, dest_dir)   # recursive resume

    if process.returncode != 0:
        print(f"❌ MegaBasterd failed (code {process.returncode})")
        return None

    # Find downloaded items
    items = [p for p in Path(dest_dir).iterdir() if not p.name.startswith('.')]
    if not items:
        print("❌ No files downloaded.")
        return None

    print(f"📁 Downloaded {len(items)} item(s).")
    return items[0] if len(items) == 1 else items[0]

# ------------------------------------------------------------
# 3. HELPER FUNCTIONS (Progress)
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