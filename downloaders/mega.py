import os
import subprocess
import re
import time
from pathlib import Path

async def download_from_mega(link, dest_dir):
    """
    Download from Mega using MEGAcmd (mega-get) – works with new format links.
    """
    print(f"⬇️ Downloading from Mega: {link}")
    os.makedirs(dest_dir, exist_ok=True)
    
    # ---------- STEP 1: Install MEGAcmd ----------
    try:
        subprocess.run("mega-get --version", shell=True, capture_output=True, check=True)
        print("✅ MEGAcmd already installed.")
    except:
        print("📦 Installing MEGAcmd...")
        subprocess.run("sudo apt-get update", shell=True, capture_output=True)
        subprocess.run("sudo apt-get install megacmd -y", shell=True, capture_output=True)
    
    # ---------- STEP 2: Anonymous Login (for public links) ----------
    login_check = subprocess.run("mega-whoami", shell=True, capture_output=True, text=True)
    if "Login session" not in login_check.stdout and "anonymous" not in login_check.stdout.lower():
        print("🔑 Logging in anonymously for public links...")
        subprocess.run("mega-login anonymous", shell=True, capture_output=True, text=True)
    
    # ---------- STEP 3: Download using mega-get (supports new format) ----------
    # Use original link – MEGAcmd handles both new and old formats
    cmd = f'mega-get "{link}" "{dest_dir}"'
    print(f"   🔧 Running: {cmd}")
    
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    start_time = time.time()
    output_lines = []
    last_percent = 0
    
    # ---------- STEP 4: Real-time progress parsing ----------
    while True:
        line = process.stdout.readline()
        if not line:
            if process.poll() is not None:
                break
            continue
        
        line = line.strip()
        output_lines.append(line)
        
        # Parse progress: "Downloading filename 45.6 MB / 102.3 MB (44%)"
        match = re.search(r'([\d.]+) ([\w]+) / ([\d.]+) ([\w]+) \((\d+)%\)', line)
        if match:
            downloaded = float(match.group(1))
            downloaded_unit = match.group(2)
            total = float(match.group(3))
            total_unit = match.group(4)
            percent = int(match.group(5))
            
            elapsed = time.time() - start_time
            # Convert to bytes (approx)
            def to_bytes(value, unit):
                unit = unit.upper()
                if unit == 'B':
                    return value
                elif unit == 'KB':
                    return value * 1024
                elif unit == 'MB':
                    return value * 1024**2
                elif unit == 'GB':
                    return value * 1024**3
                return value
            
            downloaded_bytes = to_bytes(downloaded, downloaded_unit)
            total_bytes = to_bytes(total, total_unit)
            speed = downloaded_bytes / elapsed if elapsed > 0 else 0
            
            if speed > 1024**2:
                speed_str = f"{speed/(1024**2):.2f} MB/s"
            elif speed > 1024:
                speed_str = f"{speed/1024:.2f} KB/s"
            else:
                speed_str = f"{speed:.2f} B/s"
            
            if speed > 0:
                remaining = (total_bytes - downloaded_bytes) / speed
                eta = time.strftime("%H:%M:%S", time.gmtime(remaining))
            else:
                eta = "calculating..."
            
            # Print progress on same line
            print(f"\r   📥 Downloading: {percent}% | Speed: {speed_str} | ETA: {eta}    ", end='')
            last_percent = percent
        
        # Catch errors
        if "error" in line.lower() or "failed" in line.lower():
            print(f"\n⚠️ Error detected: {line}")
            process.kill()
            return None
    
    print()  # Newline after progress
    
    # ---------- STEP 5: Check result ----------
    if process.returncode != 0:
        print(f"❌ MEGAcmd download failed with code {process.returncode}")
        # Print last few lines of output for debugging
        for line in output_lines[-5:]:
            print(f"   {line}")
        return None
    
    # ---------- STEP 6: Find downloaded items ----------
    all_items = [p for p in Path(dest_dir).iterdir() if not p.name.startswith('.')]
    if not all_items:
        print("❌ No files/folders downloaded.")
        return None
    
    print(f"📁 Downloaded {len(all_items)} item(s): {[p.name for p in all_items]}")
    
    # If multiple items, return the first (main.py will treat as virtual folder)
    return all_items[0] if len(all_items) == 1 else all_items[0]