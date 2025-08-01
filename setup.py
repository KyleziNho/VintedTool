#!/usr/bin/env python3
import os
import sys
import platform
import subprocess
import zipfile
import requests
import shutil
from pathlib import Path

SUPPORTED_DRIVER_VERSION = "138.0.7204.183"
DRIVERS_DIR = Path("drivers")
VENV_DIR = Path("venv")

def get_os_key():
    if sys.platform == "darwin":
        arch = platform.machine()
        return "mac-arm64" if arch == "arm64" else "mac-x64"
    elif sys.platform.startswith("linux"):
        return "linux64"
    elif sys.platform == "win32":
        return "win64"
    else:
        raise Exception("Unsupported OS")

def get_chrome_version():
    try:
        if sys.platform == "darwin":
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            if os.path.exists(chrome_path):
                version = subprocess.check_output([chrome_path, "--version"]).decode().strip()
                return version.split()[-1]
        elif sys.platform == "win32":
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon") as key:
                version = winreg.QueryValueEx(key, "version")[0]
                return version
        elif sys.platform.startswith("linux"):
            version = subprocess.check_output(["google-chrome", "--version"]).decode().strip()
            return version.split()[-1]
    except Exception:
        pass
    return input("Insert your full Chrome version (e.g. 138.0.7204.169): ").strip()

def download_chromedriver(version, os_key):
    try:
        url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}/{os_key}/chromedriver-{os_key}.zip"
        print(f"⬇️  Downloading ChromeDriver from:\n   {url}")
        r = requests.get(url)
        r.raise_for_status()

        DRIVERS_DIR.mkdir(exist_ok=True)
        zip_path = DRIVERS_DIR / "chromedriver.zip"

        with open(zip_path, "wb") as f:
            f.write(r.content)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(DRIVERS_DIR)

        os.remove(zip_path)

        driver_name = "chromedriver.exe" if sys.platform == "win32" else "chromedriver"
        driver_path = None
        for root, _, files in os.walk(DRIVERS_DIR):
            if driver_name in files:
                driver_path = Path(root) / driver_name
                break

        if not driver_path:
            raise Exception("chromedriver binary not found")

        if sys.platform != "win32":
            os.chmod(driver_path, 0o755)

        print(f"✅ ChromeDriver ready at: {driver_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to download ChromeDriver: {e}")
        return False

def manual_instructions(chrome_version, os_key):
    print("\n🧭 Your Chrome version is not supported for automatic download.")
    print(f"Your version: {chrome_version} | Detected OS: {os_key}")
    print(f"👉 Please download manually:\n   https://googlechromelabs.github.io/chrome-for-testing/")
    print("\nOr just search for 'ChromeDriver {chrome_version} download' in your browser.")
    print("1. Download and unzip the driver")
    print("2. Put `chromedriver` into the `drivers/` folder")
    print("Then, Activate the virtual environment:")
    print("   source venv/bin/activate")
    print("")
    print("2. Run the scraper with one of the following commands:")
    print("   🔍 Scrape all items from a seller profile:")
    print("      python vinted_scraper.py --all=\"<VINTED_PROFILE_URL>\"")
    print("")
    print("   📦 Scrape a specific item:")
    print("      python vinted_scraper.py --item=\"<VINTED_ITEM_URL>\"")
    print("")
    print("📝 Make sure to replace <...> with actual URLs.")
def setup_virtualenv():
    print("\n🐍 Creating virtual environment...")
    if VENV_DIR.exists():
        shutil.rmtree(VENV_DIR)
    subprocess.check_call(["python3", "-m", "venv", "venv"])

    print("📦 Installing requirements inside venv...")
    # Activate the venv by calling pip directly inside it
    pip_path = VENV_DIR / "bin" / "pip" if sys.platform != "win32" else VENV_DIR / "Scripts" / "pip.exe"
    subprocess.check_call([str(pip_path), "install", "--upgrade", "pip"])
    subprocess.check_call([str(pip_path), "install", "-r", "requirements.txt"])

def main():
    print("🚀 Starting Vinted Scraper Setup...\n")
    chrome_version = get_chrome_version()
    os_key = get_os_key()

    if chrome_version.startswith("138."):
        print(f"🛠️ Detected Chrome v{chrome_version} — using driver version {SUPPORTED_DRIVER_VERSION}")
        ok = download_chromedriver(SUPPORTED_DRIVER_VERSION, os_key)
        if not ok:
            manual_instructions(chrome_version, os_key)
    else:
        print(f"\n⚠️ Chrome version detected: {chrome_version}")
        print("❌ This script only supports automatic setup for Chrome v138.x")
        manual_instructions(chrome_version, os_key)

    setup_virtualenv()

    print("\n✅ Setup complete!\n")
    print("📌 Next steps:")
    print("1. Activate the virtual environment:")
    print("   source venv/bin/activate")
    print("")
    print("2. Run the scraper with one of the following commands:")
    print("   🔍 Scrape all items from a seller profile:")
    print("      python vinted_scraper.py --all=\"<VINTED_PROFILE_URL>\"")
    print("")
    print("   📦 Scrape a specific item:")
    print("      python vinted_scraper.py --item=\"<VINTED_ITEM_URL>\"")
    print("")
    print("📝 Make sure to replace <...> with actual URLs.")

if __name__ == "__main__":
    main()
