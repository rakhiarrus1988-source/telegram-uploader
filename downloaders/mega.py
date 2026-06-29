import os
import subprocess
import re
import time
from pathlib import Path

async def download_from_mega(link, dest_dir):
    """Download from Mega with real-time progress and speed."""
    print(f"⬇️ Downloading from Mega: {link}")
    os.makedirs(dest_dir, exist_ok=True)
    
    cmd = f'megadl --verbose --path "{dest_dir}" "{link}"'
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Regex to parse progress: e.g., "Downloaded 123.45 MB of 456.78 MB (27%)"
    pattern = r'Downloaded ([\d.]+) ([\w]+) of ([\d.]+) ([\w]+) \((\d+)%\)'
    total_size = None
    last_percent = 0
    start_time = time.time()
    
    while True:
        line = process.stdout.readline()
        if not line:
            if process.poll() is not None:
                break
            continue
        
        line = line.strip()
        # Print raw verbose lines (optional, can be commented)
        # print(f"   MEGA: {line}")
        
        match = re.search(pattern, line)
        if match:
            downloaded = float(match.group(1))
            downloaded_unit = match.group(2)
            total = float(match.group(3))
            total_unit = match.group(4)
            percent = int(match.group(5))
            
            # Convert to bytes for speed calculation
            def to_bytes(value, unit):
                units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
                return value * units.get(unit.upper(), 1)
            
            downloaded_bytes = to_bytes(downloaded, downloaded_unit)
            total_bytes = to_bytes(total, total_unit)
            elapsed = time.time() - start_time
            speed = downloaded_bytes / elapsed if elapsed > 0 else 0
            
            # Format speed
            if speed > 1024**2:
                speed_str = f"{speed/(1024**2):.2f} MB/s"
            elif speed > 1024:
                speed_str = f"{speed/1024:.2f} KB/s"
            else:
                speed_str = f"{speed:.2f} B/s"
            
            # ETA
            if speed > 0:
                remaining = (total_bytes - downloaded_bytes) / speed
                eta = time.strftime("%H:%M:%S", time.gmtime(remaining))
            else:
                eta = "calculating..."
            
            # Print progress bar (overwrites same line)
            print(f"\r   📥 Downloading: {percent}%  |  Speed: {speed_str}  |  ETA: {eta}    ", end='')
            last_percent = percent
        
        # Check for error messages
        if "quota" in line.lower() or "limit" in line.lower():
            print(f"\n⚠️ Mega quota limit reached. Download stopped.")
            process.kill()
            return None
    
    print()  # newline after progress
    
    if process.returncode != 0:
        print(f"❌ Mega download failed with code {process.returncode}")
        return None
    
    all_items = [p for p in Path(dest_dir).iterdir() if not p.name.startswith('.')]
    if not all_items:
        print("❌ No files/folders downloaded.")
        return None
    
    print(f"📁 Downloaded {len(all_items)} item(s).")
    return all_items[0] if len(all_items) == 1 else all_items[0]