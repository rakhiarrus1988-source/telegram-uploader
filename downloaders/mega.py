import os
import subprocess
from pathlib import Path

async def download_from_mega(link, dest_dir):
    """Download a file or folder from Mega using megadl."""
    print(f"⬇️ Downloading from Mega: {link}")
    os.makedirs(dest_dir, exist_ok=True)
    
    # megadl --path will download everything into dest_dir
    cmd = f'megadl --path "{dest_dir}" "{link}"'
    process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if process.returncode != 0:
        print(f"❌ Mega download failed: {process.stderr}")
        return None
    
    # List all items in dest_dir (excluding hidden files)
    all_items = [p for p in Path(dest_dir).iterdir() if not p.name.startswith('.')]
    
    if not all_items:
        print("❌ No files/folders downloaded.")
        return None
    
    print(f"📁 Downloaded {len(all_items)} item(s): {[p.name for p in all_items]}")
    
    # If there's only one item, return it directly (file or folder)
    if len(all_items) == 1:
        return all_items[0]
    else:
        # Multiple items downloaded (could be a folder that was extracted directly)
        # We'll return the first directory if any, else the first file
        # But we should handle this in main.py by treating the dest_dir as a collection
        # For now, return the first item; main.py will check if it's a folder.
        # To handle multiple files, we'll modify main.py to treat the whole dest_dir.
        return all_items[0]