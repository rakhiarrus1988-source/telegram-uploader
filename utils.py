import os
import sys
import subprocess

def install_package(package):
    """Install a Python package using pip."""
    subprocess.run([sys.executable, "-m", "pip", "install", package],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def install_megatools():
    """Install megatools (megadl) if not present."""
    if subprocess.run("command -v megadl", shell=True, stdout=subprocess.DEVNULL).returncode != 0:
        print("📦 Installing megatools...")
        subprocess.run("sudo apt-get update && sudo apt-get install megatools -y",
                       shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def install_terabox_dl():
    """Install terabox-dl CLI if not present."""
    if subprocess.run("command -v terabox-dl", shell=True, stdout=subprocess.DEVNULL).returncode != 0:
        print("📦 Installing terabox-dl...")
        subprocess.run("pip install terabox-dl", shell=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def ensure_dependencies():
    """Call all install functions."""
    install_megatools()
    install_terabox_dl()
    try:
        import mediafire
    except ImportError:
        install_package("mediafire")