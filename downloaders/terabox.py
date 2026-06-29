import os
import subprocess
from pathlib import Path

async def download_from_terabox(link, dest_dir):
    """Download from Terabox using yt-dlp."""
    print(f"⬇️ Downloading from Terabox: {link}")
    os.makedirs(dest_dir, exist_ok=True)
    
    # yt-dlp command - downloads and saves in dest_dir
    cmd = f'yt-dlp -o "{dest_dir}/%(title)s.%(ext)s" "{link}"'
    process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if process.returncode != 0:
        print(f"❌ Terabox download failed: {process.stderr}")
        return None
    
    # Find downloaded file(s)
    downloaded = list(Path(dest_dir).iterdir())
    if not downloaded:
        print("❌ No file downloaded.")
        return None
    
    # Return first downloaded item (file or folder)
    return downloaded[0]