import os
import subprocess
import time
from pathlib import Path
import mediafire

async def download_from_mediafire(link, dest_dir):
    """Download from MediaFire using mediafire library."""
    print(f"⬇️ Downloading from MediaFire: {link}")
    os.makedirs(dest_dir, exist_ok=True)
    
    try:
        mf = mediafire.MediaFireApi()
        
        # Get file info using the new API method
        response = mf.get_links(link)
        
        if not response or 'response' not in response:
            print("❌ Failed to get file info from MediaFire.")
            return None
        
        # Extract direct download link
        file_data = response['response']['file']
        direct_link = file_data.get('direct_download_link')
        
        if not direct_link:
            # Fallback: try to get from links
            links = file_data.get('links', {})
            direct_link = links.get('normal_download') or links.get('direct_download')
        
        if not direct_link:
            print("❌ No direct download link found.")
            return None
        
        filename = file_data.get('name', 'mediafire_file')
        dest_path = os.path.join(dest_dir, filename)
        
        print(f"   📄 Downloading: {filename}")
        start_time = time.time()
        
        # Download using wget/curl with progress
        if subprocess.run("command -v wget", shell=True).returncode == 0:
            cmd = f'wget -q --show-progress -O "{dest_path}" "{direct_link}"'
        else:
            cmd = f'curl -L -o "{dest_path}" "{direct_link}"'
        
        process = subprocess.Popen(cmd, shell=True, text=True)
        process.wait()
        
        if process.returncode != 0:
            print(f"❌ Download failed with code {process.returncode}")
            return None
        
        elapsed = time.time() - start_time
        file_size = os.path.getsize(dest_path) if os.path.exists(dest_path) else 0
        if file_size > 0 and elapsed > 0:
            speed = file_size / elapsed
            speed_str = f"{speed/(1024**2):.2f} MB/s" if speed > 1024**2 else f"{speed/1024:.2f} KB/s"
            print(f"   ✅ Downloaded: {filename} ({speed_str})")
        else:
            print(f"   ✅ Downloaded: {filename}")
        
        return Path(dest_path)
        
    except Exception as e:
        print(f"❌ MediaFire error: {e}")
        return None