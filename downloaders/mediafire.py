import os
import subprocess
from pathlib import Path
import mediafire

async def download_from_mediafire(link, dest_dir):
    """Download from MediaFire using its API + wget."""
    print(f"⬇️ Downloading from MediaFire: {link}")
    os.makedirs(dest_dir, exist_ok=True)
    try:
        mf = mediafire.MediaFireApi()
        response = mf.get_download_link(link)
        if not response.get('success'):
            print("❌ Failed to get MediaFire download link.")
            return None
        direct_link = response['response']['links']['normal_download']
        filename = os.path.basename(direct_link.split('?')[0])
        dest_path = os.path.join(dest_dir, filename)
        subprocess.run(f'wget -q -O "{dest_path}" "{direct_link}"', shell=True, check=True)
        return Path(dest_path)
    except Exception as e:
        print(f"❌ MediaFire error: {e}")
        return None