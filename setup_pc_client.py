import os
import sys
import zipfile
import shutil
import time

zip_path = r'c:\Users\user\Desktop\Pomoshgram_Desktop.zip'
dest_dir = r'c:\Users\user\Desktop\Pomoshgram_PC'
ico_path = r'c:\Users\user\Desktop\Pomoshgram.ico'
shortcut_path = r'c:\Users\user\Desktop\Pomoshgram Desktop.lnk'

print("Waiting for Pomoshgram_Desktop.zip to be complete...", flush=True)
last_sz = -1
while True:
    if os.path.exists(zip_path):
        sz = os.path.getsize(zip_path)
        # Check if file has reached ~76MB and stopped growing
        if sz > 70 * 1024 * 1024 and sz == last_sz:
            try:
                # Test if zip is valid and closed
                with zipfile.ZipFile(zip_path, 'r') as z:
                    test_list = z.namelist()
                    if test_list:
                        print(f"Zip verified ({round(sz / 1024 / 1024, 2)} MB). Extracting...", flush=True)
                        break
            except Exception:
                pass
        last_sz = sz
    time.sleep(2)

os.makedirs(dest_dir, exist_ok=True)
with zipfile.ZipFile(zip_path, 'r') as z:
    z.extractall(dest_dir)

print(f"Extracted to {dest_dir}", flush=True)

# Look for AyuGram.exe or Telegram.exe
exe_found = None
for root, dirs, files in os.walk(dest_dir):
    for f in files:
        if f.lower() in ['ayugram.exe', 'telegram.exe']:
            exe_found = os.path.join(root, f)
            break
    if exe_found:
        break

if exe_found:
    target_exe = os.path.join(dest_dir, 'Pomoshgram.exe')
    if exe_found != target_exe:
        if os.path.exists(target_exe):
            os.remove(target_exe)
        os.rename(exe_found, target_exe)
    print(f"Main binary ready: {target_exe}", flush=True)
    
    # Create Desktop shortcut with Pomoshgram.ico
    try:
        import win32com.client
        shell = win32com.client.Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = target_exe
        shortcut.WorkingDirectory = dest_dir
        if os.path.exists(ico_path):
            shortcut.IconLocation = f"{ico_path},0"
        shortcut.Description = "Pomoshgram Desktop Client (Ghost mode, Anti-delete, Unlocked features)"
        shortcut.Save()
        print(f"Created shortcut on Desktop: {shortcut_path}", flush=True)
    except Exception as e:
        print(f"Shortcut creation notice: {e}", flush=True)

# Remove temporary zip
try:
    os.remove(zip_path)
    print("Cleaned up temp zip.", flush=True)
except Exception:
    pass

print("ALL PC SETUP COMPLETE!")
