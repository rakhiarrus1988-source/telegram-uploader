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
# 1. SETUP FUNCTIONS
# ------------------------------------------------------------
def setup_java_megabasterd():
    if os.path.exists(MEGABASTERD_JAR):
        return True
    print("📦 Downloading MegaBasterd CLI...")
    url = "https://github.com/tonikelz/MegaBasterd/releases/download/v4.8.2/MegaBasterd.jar"
    try:
        # Use wget instead of requests (more reliable in Colab)
        subprocess.run(f"wget -O {MEGABASTERD_JAR} {url}", shell=True, check=True)
        print("✅ MegaBasterd downloaded.")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def setup_tor_privoxy():
    """Start Tor + Privoxy with proper daemon handling."""
    subprocess.run("sudo apt-get update -qq", shell=True)
    subprocess.run("sudo apt-get install -y tor privoxy -qq", shell=True)

    # Write Privoxy config
    privoxy_conf = """
    forward-socks5t   /               127.0.0.1:9050 .
    listen-address  127.0.0.1:8118
    """
    with open("/tmp/privoxy.conf", "w") as f:
        f.write(privoxy_conf)

    # Start Tor (daemon mode)
    subprocess.run("sudo service tor start", shell=True)
    # Start Privoxy with config
    subprocess.run(f"sudo privoxy /tmp/privoxy.conf", shell=True)
    time.sleep(5)
    
    # Verify proxies are running
    result = subprocess.run("curl -x http://127.0.0.1:8118 http://check.torproject.org/api/ip -s", shell=True, capture_output=True, text=True)
    if "IsTor" in result.stdout:
        print("✅ Tor + Privoxy ready (HTTP proxy on 8118).")
    else:
        print("⚠️ Proxy may not be working. Trying fallback...")
        return False
    return True

def renew_tor_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 9051))
        s.send(b"AUTHENTICATE \"\"\r\nSIGNAL NEWNYM\r\n")
        time.sleep(2)
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

    # Setup Java + MegaBasterd + Tor/Privoxy
    if not setup_java_megabasterd():
        print("❌ MegaBasterd setup failed.")
        return None
    if not setup_tor_privoxy():
        print("⚠️ Proxy setup failed. Trying without proxy...")
        proxy_arg = []
    else:
        proxy_arg = ["-proxy", "127.0.0.1:8118"]

    # Load progress
    progress = load_progress()
    completed_files = progress.get("completed", []) if progress else []
    folder_id = progress.get("folder_id") if progress else None

    # Build MegaBasterd command
    cmd = [
        "java", "-jar", MEGABASTERD_JAR,
        "-headless",
        *proxy_arg,
        f"-download={link}",
        f"-output={dest_dir}",
        "-resume"
    ]

    print(f"   🔧 Running: {' '.join(cmd)}")
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
        print(f"   DEBUG: {line}")  # Temporary debug

        # Quota detection
        if "quota" in line.lower() or "509" in line:
            print("\n   ⚠️ Quota hit! Renewing IP...")
            quota_hit = True
            renew_tor_ip()
            process.kill()
            break

        # Progress parsing
        percent_match = re.search(r'(\d+)%', line)
        if percent_match:
            pct = int(percent_match.group(1))
            elapsed = time.time() - start_time
            print(f"\r   📥 Downloading: {pct}% | Time: {elapsed:.0f}s", end='')

    print()  # newline

    if quota_hit:
        print("   🔄 Resuming after IP change...")
        await asyncio.sleep(5)
        return await download_from_mega(link, dest_dir)

    if process.returncode != 0:
        print(f"❌ MegaBasterd failed (code {process.returncode})")
        # Print last 5 lines for debugging
        for line in output_lines[-5:]:
            print(f"   {line}")
        return None

    # Find downloaded items
    items = [p for p in Path(dest_dir).iterdir() if not p.name.startswith('.')]
    if not items:
        print("❌ No files downloaded.")
        return None

    print(f"📁 Downloaded {len(items)} item(s).")
    return items[0] if len(items) == 1 else items[0]

# ------------------------------------------------------------
# 3. HELPER FUNCTIONS
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