import os
import subprocess
import re
import time
from pathlib import Path

def convert_mega_link(link):
    """Convert new-style Mega links to old format compatible with megadl."""
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
    """Download from Mega using megadl (no --verbose)."""
    print(f"⬇️ Downloading from Mega: {link}")
    converted = convert_mega_link(link)
    if converted != link:
        print(f"   🔄 Converted to: {converted}")
    os.makedirs(dest_dir, exist_ok=True)
    
    # Without --verbose – some versions show progress by default
    cmd = f'megadl --path "{dest_dir}" "{converted}"'
    print(f"   🔧 Running: {cmd}")
    
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    output_lines = []
    start_time = time.time()
    last_progress = ""
    
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
            print(f"\n⚠️ Mega quota limit reached. Stopping.")
            process.kill()
            return None
        
        # Try to extract percentage from lines like "Downloaded 10%"
        percent_match = re.search(r'(\d+)%', line)
        if percent_match:
            percent = int(percent_match.group(1))
            elapsed = time.time() - start_time
            # Speed/ETA are not easy without verbose, but we show percentage
            print(f"\r   📥 Downloading: {percent}%  |  Time: {elapsed:.0f}s", end='')
            last_progress = line
        elif line and "error" not in line.lower():
            # If no percentage, just print the line (maybe progress bar style)
            if not line.startswith("--") and not line.startswith("["):
                print(f"   {line}")
    
    print()  # newline after progress
    
    if process.returncode != 0:
        print(f"❌ megadl failed with code {process.returncode}")
        for line in output_lines[-5:]:
            print(f"   {line}")
        return None
    
    all_items = [p for p in Path(dest_dir).iterdir() if not p.name.startswith('.')]
    if not all_items:
        print("❌ No files/folders downloaded.")
        return None
    
    print(f"📁 Downloaded {len(all_items)} item(s): {[p.name for p in all_items]}")
    return all_items[0] if len(all_items) == 1 else all_items[0]