import os
import winreg
import zipfile
import shutil
from curl_cffi import requests  # Swapped standard requests for browser impersonation

def get_steam_path():
    """Locates the active Steam installation folder."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
        winreg.CloseKey(key)
        return os.path.normpath(steam_path)
    except Exception:
        return r"C:\Program Files (x86)\Steam"

def main():
    # 1. Target the Lua folder created by OpenSteamTools
    steam_dir = get_steam_path()
    lua_target_dir = os.path.join(steam_dir, "config", "lua")
    
    if not os.path.exists(lua_target_dir):
        print(f"[!] Target folder not found at: {lua_target_dir}")
        print("[!] Please run the main OpenSteamTool setup script first.")
        return

    print("--- Hubcap Manifest Automation Deployer ---")
    
    # 2. Collect inputs dynamically
    api_key = input("Paste your Hubcap API Key: ").strip()
    appid = input("Enter the Game AppID to download: ").strip()
    
    if not api_key or not appid:
        print("[!] API Key and AppID cannot be empty.")
        return

    download_url = f"https://hubcapmanifest.com/api/v1/download/{appid}"
    
    temp_dir = os.environ.get("TEMP", os.getcwd())
    temp_file_path = os.path.join(temp_dir, f"hubcap_{appid}.zip")

    # 3. Requesting file data using Chrome TLS Impersonation
    print("[*] Requesting manifest packet from Hubcap (Impersonating Chrome)...")
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/zip, application/octet-stream, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        # impersonate="chrome" tricks Cloudflare into thinking this is a real browser window
        response = requests.get(download_url, headers=headers, impersonate="chrome")
        
        # Guard against Cloudflare challenge pages falling through
        if "text/html" in response.headers.get("Content-Type", "") or response.status_code == 403:
            print("[!] Security Error: Cloudflare blocked the script connection.")
            print("[!] If your key is good, Cloudflare requires a real browser engine.")
            return
            
        response.raise_for_status()
        
        with open(temp_file_path, "wb") as f:
            f.write(response.content)
        print("[+] Package downloaded successfully.")
    except Exception as e:
        print(f"[!] Network request rejected: {e}")
        return

    # 4. Handle extraction of the payload
    print("[*] Extracting package and searching for .lua assets...")
    extract_path = os.path.join(temp_dir, f"hubcap_extracted_{appid}")
    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)
        
    try:
        with zipfile.ZipFile(temp_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
            
        # Scan and move files to Steam
        copied_count = 0
        for root, _, files in os.walk(extract_path):
            for file in files:
                if file.lower().endswith('.lua'):
                    shutil.copy2(os.path.join(root, file), os.path.join(lua_target_dir, file))
                    print(f"  -> Successfully installed: {file}")
                    copied_count += 1
                    
        shutil.rmtree(extract_path)
        print(f"[+] Complete! Deployed {copied_count} script(s) directly to your Steam configuration.")

    except zipfile.BadZipFile:
        print("[!] Error: Server did not return a valid ZIP archive.")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == "__main__":
    main()
