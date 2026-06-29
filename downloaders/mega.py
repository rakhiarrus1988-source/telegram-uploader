
import os
import subprocess
import re
import time
from pathlib import Path

def convert_mega_link(link):
    """
    Convert new-style Mega links to old format compatible with megadl.
    New folder:  https://mega.nz/folder/ABC123#xyz...
    Old folder:  https://mega.nz/#F!ABC123!xyz...
    New file:    https://mega.nz/file/ABC123#xyz...
    Old file:    https://mega.nz/#!ABC123!xyz...
    """
    link = link.strip()
    # Folder conversion
    match = re.match(r'https?://mega\.nz/folder/([^#]+)#(.+)', link)
    if match:
        folder_id = match.group(1)
        key = match.group(2)
        return f"https://mega.nz/#F!{folder_id}!{key}"
    # File conversion
    match = re.match(r'https?://mega\.nz/file/([^#]+)#(.+)', link)
    if match:
        file_id = match.group(1)
        key = match.group(2)
        return f"https://mega.nz/#!{file_id}!{key}"
    # Already old format or unknown
    return link

async def download_from_mega(link, dest_dir):
    """
    Download from Mega using megadl.
    Converts link to old format automatically.
    Shows real-time progress if verbose output is available.
    """
    print(f"⬇️ Downloading from Mega: {link}")
    
    # Convert link
    converted = convert_mega_link(link)
    if converted != link:
        print(f"   🔄 Converted to: {converted}")
    
    # Create destination directory
    os.makedirs(dest_dir, exist_ok=True)
    
    # Build command – use --verbose for progress
    cmd = f'megadl --verbose --path "{dest_dir}" "{converted}"'
    print(f"   🔧 Running: {cmd}")
    
    # Start process
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Regex to parse progress: "Downloaded 123.45 MB of 456.78 MB (27%)"
    progress_pattern = re.compile(r'Downloaded ([\d.]+) ([\w]+) of ([\d.]+) ([\w]+) \((\d+)%\)')
    output_lines = []
    start_time = time.time()
    last_percent = -1
    
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
            print(f"\n⚠️ Mega quota limit reached or connection limit. Stopping.")
            process.kill()
            return None
        
        # Try to parse progress
        match = progress_pattern.search(line)
        if match:
            downloaded = float(match.group(1))
            unit = match.group(2)
            total = float(match.group(3))
            total_unit = match.group(4)
            percent = int(match.group(5))
            
            elapsed = time.time() - start_time
            # Convert to bytes for speed calculation (approx)
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
            downloaded_bytes = to_bytes(downloaded, unit)
            total_bytes = to_bytes(total, total_unit)
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
            
            # Print progress on same line
            print(f"\r   📥 Downloading: {percent}% | Speed: {speed_str} | ETA: {eta}    ", end='')
            last_percent = percent
    
    print()  # Newline after progress bar
    
    # Check return code
    if process.returncode != 0:
        print(f"❌ megadl failed with code {process.returncode}")
        # Print last few lines for debugging
        for line in output_lines[-5:]:
            print(f"   {line}")
        return None
    
    # Find downloaded items
    all_items = [p for p in Path(dest_dir).iterdir() if not p.name.startswith('.')]
    if not all_items:
        print("❌ No files/folders downloaded.")
        return None
    
    print(f"📁 Downloaded {len(all_items)} item(s): {[p.name for p in all_items]}")
    
    # Return the first item (if multiple, main.py will treat as virtual folder)
    return all_items[0] if len(all_items) == 1 else all_items[0]