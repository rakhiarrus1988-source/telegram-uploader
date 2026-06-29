import os
import asyncio
import time
from pathlib import Path
from mega import Mega

async def download_from_mega(link, dest_dir):
    """
    Download from Mega using mega.py library.
    Supports public links (anonymous login), files & folders.
    Shows real-time progress with speed and ETA.
    """
    print(f"⬇️ Downloading from Mega: {link}")
    os.makedirs(dest_dir, exist_ok=True)

    # ----- Synchronous download function (runs in thread) -----
    def sync_download():
        try:
            # Login anonymously for public links
            mega = Mega()
            m = mega.login_anonymous()
            print("   🔑 Logged in anonymously.")
        except Exception as e:
            print(f"   ⚠️ Anonymous login failed: {e}")
            # Fallback: try without login (some public links work)
            m = Mega()

        try:
            # Get node from link (works with both new & old formats)
            node = m.get_node_from_link(link)
            node_type = node['type']  # 0=file, 1=folder

            if node_type == 0:
                # ---------- Single File ----------
                file_name = node['name']
                dest_path = os.path.join(dest_dir, file_name)
                print(f"   📄 Downloading file: {file_name}")
                start_time = time.time()

                def progress_callback(current, total):
                    percent = (current / total) * 100
                    elapsed = time.time() - start_time
                    speed = current / elapsed if elapsed > 0 else 0
                    if speed > 1024**2:
                        speed_str = f"{speed/(1024**2):.2f} MB/s"
                    elif speed > 1024:
                        speed_str = f"{speed/1024:.2f} KB/s"
                    else:
                        speed_str = f"{speed:.2f} B/s"
                    if speed > 0:
                        remaining = (total - current) / speed
                        eta = time.strftime("%H:%M:%S", time.gmtime(remaining))
                    else:
                        eta = "calculating..."
                    print(f"\r   📥 Downloading: {percent:.1f}% | Speed: {speed_str} | ETA: {eta}    ", end='')

                m.download_node(node, dest_path, progress_callback)
                print()  # newline
                print(f"   ✅ File downloaded: {file_name}")
                return dest_path

            elif node_type == 1:
                # ---------- Folder ----------
                folder_name = node['name']
                folder_path = os.path.join(dest_dir, folder_name)
                print(f"   📂 Downloading folder: {folder_name}")
                # Get all files in folder (recursive)
                files = m.get_files_in_node(node)
                total_files = len(files)
                print(f"   📁 Found {total_files} file(s) in folder.")

                for idx, file_node in enumerate(files, start=1):
                    file_name = file_node['name']
                    print(f"\n   📄 [{idx}/{total_files}] Downloading: {file_name}")
                    start_time = time.time()

                    def progress_callback(current, total):
                        percent = (current / total) * 100
                        elapsed = time.time() - start_time
                        speed = current / elapsed if elapsed > 0 else 0
                        if speed > 1024**2:
                            speed_str = f"{speed/(1024**2):.2f} MB/s"
                        elif speed > 1024:
                            speed_str = f"{speed/1024:.2f} KB/s"
                        else:
                            speed_str = f"{speed:.2f} B/s"
                        if speed > 0:
                            remaining = (total - current) / speed
                            eta = time.strftime("%H:%M:%S", time.gmtime(remaining))
                        else:
                            eta = "calculating..."
                        print(f"\r      📥 Downloading: {percent:.1f}% | Speed: {speed_str} | ETA: {eta}    ", end='')

                    m.download_node(file_node, folder_path, progress_callback)
                    print()
                    print(f"      ✅ Downloaded: {file_name}")

                print(f"\n   ✅ Folder downloaded: {folder_name} (Total: {total_files} files)")
                return folder_path

            else:
                print(f"❌ Unknown node type: {node_type}")
                return None

        except Exception as e:
            print(f"❌ Mega error: {e}")
            return None

    # ----- Run synchronous download in thread to avoid blocking event loop -----
    result = await asyncio.to_thread(sync_download)
    if result is None:
        return None

    # Return as Path object (for compatibility with main.py)
    return Path(result)