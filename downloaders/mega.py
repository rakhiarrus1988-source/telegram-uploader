import os
import json
import time
import subprocess
import re
import signal
import asyncio
import requests
from pathlib import Path

PROGRESS_FILE = "/content/drive/MyDrive/mega_download_progress.json"

# ------------------------------------------------------------
# 1. INSTALL JAVA & MEGABASTERD CLI
# ------------------------------------------------------------
def setup_java_megabasterd():
    """Install Java and download MegaBasterd CLI JAR."""
    # Install Java if not present
    subprocess.run("sudo apt-get update -qq", shell=True)
    subprocess.run("sudo apt-get install -y default-jre wget -qq", shell=True)

    # Download MegaBasterd JAR (latest release)
    jar_path = "/tmp/MegaBasterd.jar"
    if not os.path.exists(jar_path):
        print("📦 Downloading MegaBasterd CLI...")
        # GitHub release URL (replace with latest version)
        url = "https://github.com/tonikelz/MegaBasterd/releases/download/v4.8.2/MegaBasterd.jar"
        try:
            r = requests.get(url, stream=True)
            with open(jar_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("✅ MegaBasterd downloaded.")
        except Exception as e:
            print(f"❌ Failed to download MegaBasterd: {e}")
            return False
    return True

def setup_tor_polipo():
    """Install and start Tor + Polipo."""
    subprocess.run("sudo apt-get install -y tor polipo -qq", shell=True)

    polipo_conf = """
    socksParentProxy = localhost:9050
    socksProxyType = socks5
    proxyAddress = 0.0.0.0
    proxyPort = 8123
    """
    with open("/tmp/polipo.conf", "w") as f:
        f.write(polipo_conf)

    subprocess.Popen("sudo tor --RunAsDaemon 1", shell=True)
    subprocess.Popen(f"sudo polipo -c /tmp/polipo.conf", shell=True)
    time.sleep(5)
    print("✅ Tor and Polipo running (HTTP proxy on port 8123).")

def renew_tor_ip():
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 9051))
        s.send(b"AUTHENTICATE \"\"\r\nSIGNAL NEWNYM\r\n")
        time.sleep(1)
        s.close()
        print("   🔄 Tor IP renewed.")
        return True
    except Exception as e:
        print(f"   ⚠️ Tor renewal failed: {e}")
        return False

# ------------------------------------------------------------
# 2. MEGA DOWNLOADER USING MEGABASTERD CLI
# ------------------------------------------------------------
async def download_from_mega(link, dest_dir):
    print(f"⬇️ Downloading from Mega: {link}")
    os.makedirs(dest_dir, exist_ok=True)

    # Setup Java + MegaBasterd, Tor/Polipo
    if not setup_java_megabasterd():
        return None
    setup_tor_polipo()

    # Load progress (folder ID)
    progress = load_progress()
    completed_files = progress.get("completed", []) if progress else []
    folder_id = progress.get("folder_id") if progress else None

    # MegaBasterd command
    jar_path = "/tmp/MegaBasterd.jar"
    # Proxy: Polipo on port 8123
    proxy = "http://localhost:8123"
    # Output directory
    out_dir = dest_dir

    # Build command: java -jar MegaBasterd.jar -headless -proxy ... -download ...
    cmd = [
        "java", "-jar", jar_path,
        "-headless",
        f"-proxy={proxy}",
        f"-download={link}",
        f"-output={out_dir}",
        "-resume"  # enable resume
    ]

    print(f"   🔧 Running MegaBasterd CLI with Tor proxy...")
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

        # Detect quota error (MegaBasterd prints "Quota exceeded" or "509")
        if "quota" in line.lower() or "509" in line:
            print("\n   ⚠️ Quota limit reached. Renewing Tor IP...")
            quota_hit = True
            renew_tor_ip()
            process.kill()
            break

        # Show progress (MegaBasterd outputs percentage like "Progress: 45%")
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
        # Recursively call to resume (progress file will handle)
        return await download_from_mega(link, dest_dir)

    if process.returncode != 0:
        print(f"❌ MegaBasterd failed with code {process.returncode}")
        return None

    # Find downloaded items
    all_items = [p for p in Path(dest_dir).iterdir() if not p.name.startswith('.')]
    if not all_items:
        print("❌ No files downloaded.")
        return None

    print(f"📁 Downloaded {len(all_items)} item(s).")
    return all_items[0] if len(all_items) == 1 else all_items[0]

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