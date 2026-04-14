import urllib.request
import zipfile
import os
import shutil
import sys

# The direct download link to the ZIP of the main branch
REPO_ZIP_URL = "https://github.com/Zexolver/ploom/archive/refs/heads/main.zip"
ZIP_FILENAME = "update_temp.zip"
EXTRACT_FOLDER = "ploom-main" # GitHub always appends '-main' to the extracted folder

def update_game():
    print("Fetching latest nightly build from GitHub...")
    
    try:
        # 1. Download the ZIP
        urllib.request.urlretrieve(REPO_ZIP_URL, ZIP_FILENAME)
        print("Download complete. Applying updates...")
        
        # 2. Extract the ZIP
        with zipfile.ZipFile(ZIP_FILENAME, 'r') as zip_ref:
            zip_ref.extractall(".")
            
        # 3. Move files from the extracted folder to the current directory
        if os.path.exists(EXTRACT_FOLDER):
            for item in os.listdir(EXTRACT_FOLDER):
                # Skip replacing the updater itself while it's running to prevent Windows permission crashes
                if item == os.path.basename(__file__):
                    continue 
                    
                source = os.path.join(EXTRACT_FOLDER, item)
                destination = os.path.join(".", item)
                
                # If the destination file/folder exists, delete it first to ensure a clean overwrite
                if os.path.exists(destination):
                    if os.path.isdir(destination):
                        shutil.rmtree(destination)
                    else:
                        os.remove(destination)
                        
                shutil.move(source, destination)
            
            # 4. Clean up the empty extracted folder
            shutil.rmtree(EXTRACT_FOLDER)
            
        # 5. Clean up the downloaded ZIP
        if os.path.exists(ZIP_FILENAME):
            os.remove(ZIP_FILENAME)
            
        print("\nUpdate completely successfully! You are now on the latest version.")
        
    except Exception as e:
        print(f"\nUpdate failed: {e}")
        
    # Keep the window open so the user can see if it worked
    input("Press Enter to close...")

if __name__ == "__main__":
    update_game()