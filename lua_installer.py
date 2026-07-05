import os
import winreg
import zipfile
import shutil
import time

# Attempt to import curl_cffi falling back gracefully if not pre-installed
try:
    from curl_cffi import requests
except ImportError:
    import subprocess
    import sys
    print("[*] Installing browser simulation library dependency (curl_cffi)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "curl_cffi"])
    from curl_cffi import requests

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

    # Use the explicit file delivery endpoint path 
    download_url = f"https://hubcapmanifest.com/api/v1/download/{appid}"
    
    temp_dir = os.environ.get("TEMP", os.getcwd())
    temp_file_path = os.path.join(temp_dir, f"hubcap_{appid}.zip")

    # 3. Download the asset mimicking a genuine user download trigger
    print("[*] Launching secure browser tunnel to Hubcap...")
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/zip, application/octet-stream, text/html, application/xhtml+xml, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://hubcapmanifest.com/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        # Using a newer profile engine string to bypass Cloudflare signatures
        session = requests.Session()
        response = session.get(download_url, headers=headers, impersonate="chrome120", timeout=30)
        
        # Fallback debug step: check what came back if it failed
        if "text/html" in response.headers.get("Content-Type", "") or response.status_code != 200:
            print(f"[!] Security Error: Cloudflare returned status code {response.status_code}")
            print("[!] The server dropped the script session. Checking response snippet...")
            snippet = response.text[:150].strip()
            if "Cloudflare" in snippet or "ray ID" in snippet.lower():
                print(" -> Confirmed: Cloudflare bot defense blocked the automated terminal connection.")
            else:
                print(f" -> Server details: {snippet}")
            return
            
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
        print("[!] Error: Downloaded file is corrupted or not a valid ZIP file archive.")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == "__main__":
    main()
