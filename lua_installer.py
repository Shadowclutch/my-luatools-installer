import os
import winreg
import zipfile
import shutil
import requests

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

    # Formatted route used explicitly by Hubcap for file distribution
    download_url = f"https://hubcapmanifest.com/api/v1/download/{appid}"
    
    temp_dir = os.environ.get("TEMP", os.getcwd())
    temp_file_path = os.path.join(temp_dir, f"hubcap_{appid}.zip")

    # 3. Requesting file data with precise browser simulation headers
    print("[*] Requesting manifest packet from Hubcap...")
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/zip, application/octet-stream, */*"
        }
        
        response = requests.get(download_url, headers=headers, stream=True)
        
        # Guard against HTML text pages passing through
        if "text/html" in response.headers.get("Content-Type", ""):
            print("[!] Security Error: Hubcap blocked the request or the API Key has expired.")
            print("[!] Please make sure your token is active on hubcapmanifest.com")
            return
            
        response.raise_for_status()
        
        with open(temp_file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
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
