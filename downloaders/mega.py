import os
import subprocess
import re
import time
from pathlib import Path

def convert_mega_link(link):
    """Convert new-style Mega links to old format for megadl."""
    link = link.strip()
    # Folder: https://mega.nz/folder/ABC#xyz → https://mega.nz/#F!ABC!xyz
    match = re.match(r'https?://mega\.nz/folder/([^#]+)#(.+)', link)
    if match:
        return f"https://mega.nz/#F!{match.group(1)}!{match.group(2)}"
    # File: https://mega.nz/file/ABC#xyz → https://mega.nz/#!ABC!xyz
    match = re.match(r'https?://mega\.nz/file/([^#]+)#(.+)', link)
    if match:
        return f"https://mega.nz/#!{match.group(1)}!{match.group(2)}"
    return link

async def download_from_mega(link, dest_dir):
    """
    Mega downloader:
    - For files: uses mega.py library (fast, reliable)
    - For folders: falls back to megadl (without --verbose)
    """
    print(f"⬇️ Downloading from Mega: {link}")
    os.makedirs(dest_dir, exist_ok=True)
    
    # ----- Try mega.py library first (works well for files) -----
    try:
        from mega import Mega
        mega = Mega()
        m = mega.login_anonymous()
        if m is not None:
            node = m.get_node_from_link(link)
            if node is not None:
                node_type = node.get('type')
                # Type 0 = file, Type 1 = folder
                if node_type == 0:
                    # ----- FILE: download using mega.py -----
                    file_name = node.get('name')
                    dest_path = os.path.join(dest_dir, file_name)
                    print(f"   📄 Downloading file: {file_name} (using mega.py)")
                    start_time = time.time()
                    
                    def progress_callback(current, total):
                        percent = (current / total) * 100
                        elapsed = time.time() - start_time
                        speed = current / elapsed if elapsed > 0 else 0
                        speed_str = f"{speed/(1024**2):.2f} MB/s" if speed > 1024**2 else f"{speed/1024:.2f} KB/s"
                        if speed > 0:
                            remaining = (total - current) / speed
                            eta = time.strftime("%H:%M:%S", time.gmtime(remaining))
                        else:
                            eta = "calculating..."
                        print(f"\r   📥 Downloading: {percent:.1f}% | Speed: {speed_str} | ETA: {eta}    ", end='')
                    
                    m.download_node(node, dest_path, progress_callback)
                    print()
                    print(f"   ✅ File downloaded: {file_name}")
                    return Path(dest_path)
                else:
                    # ----- FOLDER: use megadl (mega.py folder support is unreliable) -----
                    print(f"   📂 Folder detected. Using megadl for reliability.")
                    # fall through to megadl
            else:
                print("   ⚠️ Could not get node. Falling back to megadl.")
        else:
            print("   ⚠️ Anonymous login failed. Falling back to megadl.")
    except Exception as e:
        print(f"   ⚠️ mega.py error: {e}. Falling back to megadl.")
    
    # ----- Fallback: megadl (for folders or if mega.py fails) -----
    converted = convert_mega_link(link)
    if converted != link:
        print(f"   🔄 Converted to: {converted}")
    
    # No --verbose (to avoid version issues)
    cmd = f'megadl --path "{dest_dir}" "{converted}"'
    print(f"   🔧 Running megadl: {cmd}")
    
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
        # Show progress if any (some megadl versions output %)
        if "%" in line:
            print(f"\r   📥 {line}", end='')
        elif "Downloaded" in line and "MB" in line:
            print(f"\r   📥 {line}", end='')
    
    print()
    if process.returncode != 0:
        print(f"❌ megadl failed with code {process.returncode}")
        # Print last lines for debugging
        for line in output_lines[-5:]:
            print(f"   {line}")
        return None
    
    all_items = [p for p in Path(dest_dir).iterdir() if not p.name.startswith('.')]
    if not all_items:
        print("❌ No files/folders downloaded.")
        return None
    
    print(f"📁 Downloaded {len(all_items)} item(s).")
    return all_items[0] if len(all_items) == 1 else all_items[0]