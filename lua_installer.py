import os
import winreg
import zipfile
import shutil
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    import subprocess
    print("[*] Installing browser automation engine (Playwright)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chrome"])
    from playwright.sync_api import sync_playwright

def get_steam_path():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
        winreg.CloseKey(key)
        return os.path.normpath(steam_path)
    except Exception:
        return r"C:\Program Files (x86)\Steam"

def main():
    steam_dir = get_steam_path()
    lua_target_dir = os.path.join(steam_dir, "config", "lua")
    
    if not os.path.exists(lua_target_dir):
        print(f"[!] Target folder not found at: {lua_target_dir}")
        return

    print("--- Hubcap Manifest Headless Automation Deployer ---")
    api_key = input("Paste your Hubcap API Key: ").strip()
    appid = input("Enter the Game AppID to download: ").strip()
    
    if not api_key or not appid:
        print("[!] Inputs cannot be empty.")
        return

    download_url = f"https://hubcapmanifest.com/api/v1/download/{appid}"
    temp_dir = os.environ.get("TEMP", os.getcwd())
    temp_file_path = os.path.join(temp_dir, f"hubcap_{appid}.zip")

    print("[*] Launching automated Chrome engine to bypass security walls...")
    try:
        with sync_playwright() as p:
            # Launch actual Google Chrome channel to pass TLS/Cloudflare signatures
            browser = p.chromium.launch(headless=True, channel="chrome")
            context = browser.new_context(
                extra_http_headers={"Authorization": f"Bearer {api_key}"}
            )
            page = context.new_page()
            
            print("[*] Navigating to download stream...")
            # Expect a file download trigger when navigating
            with page.expect_download(timeout=60000) as download_info:
                page.goto(download_url)
            
            download = download_info.value
            download.save_as(temp_file_path)
            browser.close()
            
        print("[+] Package downloaded successfully via browser automation.")
    except Exception as e:
        print(f"[!] Browser automation failed: {e}")
        return

    # 4. Extract assets
    print("[*] Extracting package and searching for .lua assets...")
    extract_path = os.path.join(temp_dir, f"hubcap_extracted_{appid}")
    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)
        
    try:
        with zipfile.ZipFile(temp_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
            
        copied_count = 0
        for root, _, files in os.walk(extract_path):
            for file in files:
                if file.lower().endswith('.lua'):
                    shutil.copy2(os.path.join(root, file), os.path.join(lua_target_dir, file))
                    print(f"  -> Successfully installed: {file}")
                    copied_count += 1
                    
        shutil.rmtree(extract_path)
        print(f"[+] Complete! Deployed {copied_count} script(s) to your Steam folder.")

    except zipfile.BadZipFile:
        print("[!] Error: Downloaded file is corrupted. The API key might have been blocked.")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == "__main__":
    main()
