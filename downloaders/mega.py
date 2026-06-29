import os
import subprocess
from pathlib import Path

async def download_from_mega(link, dest_dir):
    """Download a file or folder from Mega using megadl."""
    print(f"⬇️ Downloading from Mega: {link}")
    # Ensure destination exists
    os.makedirs(dest_dir, exist_ok=True)
    cmd = f'megadl --path "{dest_dir}" "{link}"'
    process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if process.returncode != 0:
        print(f"❌ Mega download failed: {process.stderr}")
        return None
    # Find what was downloaded
    downloaded = list(Path(dest_dir).iterdir())
    if not downloaded:
        print("❌ No file/folder downloaded.")
        return None
    return downloaded[0]  # returns Path object