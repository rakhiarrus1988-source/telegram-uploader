import os
import subprocess
from pathlib import Path

async def download_from_terabox(link, dest_dir):
    """Download from Terabox using terabox-dl CLI."""
    print(f"⬇️ Downloading from Terabox: {link}")
    os.makedirs(dest_dir, exist_ok=True)
    cmd = f'terabox-dl "{link}" -o "{dest_dir}"'
    process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if process.returncode != 0:
        print(f"❌ Terabox download failed: {process.stderr}")
        return None
    downloaded = list(Path(dest_dir).iterdir())
    if not downloaded:
        print("❌ No file/folder downloaded.")
        return None
    return downloaded[0]