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
    """
    link = link.strip()
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
    
    return link  # Already old format or unknown

async def download_from_mega(link, dest_dir):
    """Download from Mega using megadl (with fallback to MEGAcmd)."""
    print(f"⬇️ Downloading from Mega: {link}")
    converted = convert_mega_link(link)
    print(f"   🔄 Converted: {converted}")
    
    os.makedirs(dest_dir, exist_ok=True)
    
    # Try megadl first
    success = await try_megadl(converted, dest_dir)
    if success:
        return success
    
    # Fallback to MEGAcmd
    print("⚠️ megadl failed, trying MEGAcmd...")
    return await try_megacmd(link, dest_dir)

async def try_megadl(link, dest_dir):
    """Attempt download using megadl with real-time progress."""
    cmd = f'megadl --verbose --path "{dest_dir}" "{link}"'
    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, bufsize=1
    )
    
    pattern = r'Downloaded ([\d.]+) ([\w]+) of ([\d.]+) ([\w]+) \((\d+)%\)'
    start_time = time.time()
    output_lines = []
    
    while True:
        line = process.stdout.readline()
        if not line:
            if process.poll() is not None:
                break
            continue
        line = line.strip()
        output_lines.append(line)
        
        # Quota check
        if "quota" in line.lower() or "limit" in line.lower():
            print(f"\n⚠️ Mega quota limit reached.")
            process.kill()
            return None
        
        match = re.search(pattern, line)
        if match:
            percent = int(match.group(5))
            elapsed = time.time() - start_time
            downloaded = float(match.group(1))
            unit = match.group(2)
            speed = (downloaded * (1024**2 if unit == 'MB' else 1024**3)) / elapsed if elapsed > 0 else 0
            speed_str = f"{speed/(1024**2):.2f} MB/s" if speed > 1024**2 else f"{speed/1024:.2f} KB/s"
            print(f"\r   📥 Downloading: {percent}% | Speed: {speed_str} | ETA: ...", end='')
    
    print()
    if process.returncode != 0:
        print(f"❌ megadl failed with code {process.returncode}")
        # Print last lines for debugging
        for line in output_lines[-5:]:
            print(f"   {line}")
        return None
    
    all_items = [p for p in Path(dest_dir).iterdir() if not p.name.startswith('.')]
    return all_items[0] if all_items else None

async def try_megacmd(link, dest_dir):
    """Fallback: use MEGAcmd (mega-get) for reliable download."""
    # Install MEGAcmd if not present
    try:
        subprocess.run("mega-get --version", shell=True, capture_output=True, check=True)
    except:
        print("📦 Installing MEGAcmd...")
        subprocess.run("sudo apt-get update && sudo apt-get install megacmd -y", shell=True)
        subprocess.run("mega-login anonymous", shell=True, capture_output=True)
    
    cmd = f'mega-get "{link}" "{dest_dir}"'
    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, bufsize=1
    )
    
    start_time = time.time()
    output_lines = []
    
    while True:
        line = process.stdout.readline()
        if not line:
            if process.poll() is not None:
                break
            continue
        line = line.strip()
        output_lines.append(line)
        
        # Parse progress: "Downloading file 45.6 MB / 102.3 MB (44%)"
        match = re.search(r'([\d.]+) ([\w]+) / ([\d.]+) ([\w]+) \((\d+)%\)', line)
        if match:
            percent = int(match.group(5))
            elapsed = time.time() - start_time
            downloaded = float(match.group(1))
            unit = match.group(2)
            speed = (downloaded * (1024**2 if unit == 'MB' else 1024**3)) / elapsed if elapsed > 0 else 0
            speed_str = f"{speed/(1024**2):.2f} MB/s" if speed > 1024**2 else f"{speed/1024:.2f} KB/s"
            print(f"\r   📥 MEGAcmd: {percent}% | Speed: {speed_str} | ETA: ...", end='')
    
    print()
    if process.returncode != 0:
        print(f"❌ MEGAcmd failed with code {process.returncode}")
        for line in output_lines[-5:]:
            print(f"   {line}")
        return None
    
    all_items = [p for p in Path(dest_dir).iterdir() if not p.name.startswith('.')]
    return all_items[0] if all_items else None