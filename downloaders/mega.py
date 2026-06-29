import os
import subprocess
import time
from pathlib import Path

async def download_from_mega(link, dest_dir):
    print(f"⬇️ Downloading from Mega: {link}")
    os.makedirs(dest_dir, exist_ok=True)

    # ----- TRY 1: mega.py library (works for files and sometimes folders) -----
    try:
        from mega import Mega
        mega = Mega()
        m = mega.login_anonymous()
        if m is not None:
            node = m.get_node_from_link(link)
            if node is not None:
                node_type = node.get('type')  # 0=file, 1=folder
                if node_type == 0:
                    # ---- File ----
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
                elif node_type == 1:
                    # ---- Folder ----
                    folder_name = node.get('name')
                    folder_path = os.path.join(dest_dir, folder_name)
                    print(f"   📂 Downloading folder: {folder_name} (using mega.py)")
                    m.download_node(node, folder_path)
                    print(f"   ✅ Folder downloaded: {folder_name}")
                    return Path(folder_path)
    except Exception as e:
        print(f"   ⚠️ mega.py error: {e}. Falling back to megadl.")

    # ----- TRY 2: megadl with ORIGINAL link (no conversion) -----
    print("   🔧 Trying megadl with original link...")
    cmd = f'megadl --path "{dest_dir}" "{link}"'
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
    while True:
        line = process.stdout.readline()
        if not line:
            if process.poll() is not None:
                break
            continue
        line = line.strip()
        output_lines.append(line)
        if "%" in line or "Downloaded" in line:
            print(f"\r   📥 {line}", end='')
    print()
    if process.returncode != 0:
        print(f"❌ megadl failed with code {process.returncode}")
        for line in output_lines[-5:]:
            print(f"   {line}")
        return None
    all_items = [p for p in Path(dest_dir).iterdir() if not p.name.startswith('.')]
    if not all_items:
        print("❌ No files/folders downloaded.")
        return None
    print(f"📁 Downloaded {len(all_items)} item(s).")
    return all_items[0] if len(all_items) == 1 else all_items[0]