import os
import sys
import subprocess

def install_package(package):
    """Install a Python package using pip."""
    subprocess.run([sys.executable, "-m", "pip", "install", package],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def install_megatools():
    """Install megatools (megadl) if not present (Linux/Colab)."""
    if subprocess.run("command -v megadl", shell=True, stdout=subprocess.DEVNULL).returncode != 0:
        print("📦 Installing megatools...")
        subprocess.run("sudo apt-get update && sudo apt-get install megatools -y",
                       shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def ensure_dependencies():
    """
    Ensure all required external tools and Python packages are available.
    - megatools for Mega downloads (Linux/Colab)
    - mediafire for MediaFire downloads
    - yt-dlp for Terabox downloads
    """
    install_megatools()
    
    # Check and install mediafire
    try:
        import mediafire
    except ImportError:
        print("📦 Installing mediafire...")
        install_package("mediafire")
    
    # Check and install yt-dlp (for Terabox)
    try:
        import yt_dlp
    except ImportError:
        print("📦 Installing yt-dlp...")
        install_package("yt-dlp")