import os
import subprocess
import re
import time
from pathlib import Path

def convert_mega_link(link):
    """
    Convert new-style Mega links to old format compatible with megadl.
    
    New format (folder):  https://mega.nz/folder/ABC123#xyz...
    Old format (folder):  https://mega.nz/#F!ABC123!xyz...
    
    New format (file):    https://mega.nz/file/ABC123#xyz...
    Old format (file):    https://mega.nz/#!ABC123!xyz...
    """
    # Folder link conversion
    match = re.match(r'https?://mega\.nz/folder/([^#]+)#(.+)', link)
    if match:
        folder_id = match.group(1)
        key = match.group(2)
        return f"https://mega.nz/#F!{folder_id}!{key}"
    
    # File link conversion
    match = re.match(r'https?://mega\.nz/file/([^#]+)#(.+)', link)
    if match:
        file_id = match.group(1)
        key = match.group(2)
        return f"https://mega.nz/#!{file_id}!{key}"
    
    # Already old format? Keep as is.
    return link

async def download_from_mega(link, dest_dir):
    """
    Download from Mega with real-time progress, speed, and ETA.
    Automatically converts new-style Mega links to old format.
    """
    print(f"⬇️ Downloading from Mega: {link}")
    
    # Convert link if needed
    converted_link = convert_mega_link(link)
    if converted_link != link:
        print(f"   🔄 Link converted to: {converted_link}")
    
    os.makedirs(dest_dir, exist_ok=True)
    
    # Use --verbose to get progress lines
    cmd = f'megadl --verbose --path "{dest_dir}" "{converted_link}"'
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Regex to parse progress: "Downloaded 123.45 MB of 456.78 MB (27%)"
    pattern = r'Downloaded ([\d.]+) ([\w]+) of ([\d.]+) ([\w]+) \((\d+)%\)'
    last_percent = 0
    start_time = time.time()
    
    # Keep track of output for debugging
    output_lines = []
    
    while True:
        line = process.stdout.readline()
        if not line:
            if process.poll() is not None:
                break
            continue
        
        line = line.strip()
        output_lines.append(line)
        
        # Check for quota/limit errors
        if "quota" in line.lower() or "limit" in line.lower():
            print(f"\n⚠️ Mega quota limit reached or connection limit. Download stopped.")
            process.kill()
            return None
        
        # Parse progress
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
            
            # Overwrite same line
            print(f"\r   📥 Downloading: {percent}%  |  Speed: {speed_str}  |  ETA: {eta}    ", end='')
            last_percent = percent
    
    print()  # newline after progress
    
    # Check return code
    if process.returncode != 0:
        print(f"❌ Mega download failed with code {process.returncode}")
        # Print last few lines of output for debugging
        for line in output_lines[-5:]:
            print(f"   {line}")
        return None
    
    # Find downloaded items
    all_items = [p for p in Path(dest_dir).iterdir() if not p.name.startswith('.')]
    if not all_items:
        print("❌ No files/folders downloaded.")
        return None
    
    print(f"📁 Downloaded {len(all_items)} item(s): {[p.name for p in all_items]}")
    
    # Return the first item (if multiple, main.py will handle as virtual folder)
    return all_items[0] if len(all_items) == 1 else all_items[0]