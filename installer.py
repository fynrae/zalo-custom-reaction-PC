import os
import re
from pathlib import Path
import subprocess
import shutil
import requests
from typing import Optional, Tuple
import time
import sys
import colorama # Import colorama

# --- Initialize Colorama ---
# autoreset=True ensures colors reset after each print automatically
colorama.init(autoreset=True)
Fore = colorama.Fore
Style = colorama.Style

# --- Color Constants ---
COLOR_INFO = Fore.CYAN         # For general steps [*]
COLOR_SUCCESS = Fore.GREEN       # For success messages [+]
COLOR_WARNING = Fore.YELLOW      # For warnings [!]
COLOR_ERROR = Fore.RED         # For errors [!]
COLOR_HIGHLIGHT = Fore.MAGENTA   # For path highlights or important info
COLOR_STEP = Fore.BLUE + Style.BRIGHT # For step headers --- Step X ---
COLOR_IMPORTANT = Fore.YELLOW + Style.BRIGHT # For very important warnings

# --- Constants ---
CUSTOM_SCRIPT_URL = "https://raw.githubusercontent.com/fynrae/zalo-custom-reaction-PC/main/zalorcustomemoji.user.js"
CUSTOM_SCRIPT_FILENAME = "zalorcustomemoji.user.js"
TARGET_HTML_FILENAME = "index.html"
TARGET_HTML_SUBDIR = "pc-dist"
INJECTION_MARKER = "</body>"
# --- MODIFIED CONSTANTS for file/folder replacement strategy ---
ORIGINAL_ASAR_FILENAME = "app.asar"
BACKUP_ASAR_FILENAME = "app.asar.bak"
UNPACKED_DIR_NAME = "unpacked_temp" # Temporary name for the folder created by extract_asar

def get_asar_executable() -> Optional[str]:
    """Finds the asar executable, checking common locations and PATH."""
    # 1. Check PATH using shutil.which
    asar_cmd = shutil.which('asar')
    if asar_cmd:
        print(f"{COLOR_INFO}[*] Found 'asar' in PATH: {Style.BRIGHT}{asar_cmd}{Style.NORMAL}")
        return asar_cmd

    # 2. Check default npm global locations (Windows)
    appdata = os.getenv('APPDATA')
    if sys.platform == "win32" and appdata:
        npm_global_path = Path(appdata) / 'npm' / 'asar.cmd'
        if npm_global_path.is_file():
            print(f"{COLOR_INFO}[*] Found 'asar' in default npm global location: {Style.BRIGHT}{npm_global_path}{Style.NORMAL}")
            return str(npm_global_path)
        # Check node_modules within npm
        npm_global_modules_path = Path(appdata) / 'npm' / 'node_modules' / 'asar' / 'bin' / 'asar.cmd'
        if npm_global_modules_path.is_file():
             print(f"{COLOR_INFO}[*] Found 'asar' in default npm node_modules: {Style.BRIGHT}{npm_global_modules_path}{Style.NORMAL}")
             return str(npm_global_modules_path)

    print(f"{COLOR_WARNING}[!] Warning: Could not automatically find 'asar' executable.")
    print(f"{COLOR_WARNING}    Attempting to use 'asar' directly, assuming it's in PATH.")
    return 'asar' # Fallback to assuming it's in path


def get_zalo_base_path() -> Path:
    """Gets the base path where Zalo versions are typically installed."""
    local_appdata = os.getenv('LOCALAPPDATA')
    if not local_appdata:
        raise EnvironmentError(f"{COLOR_ERROR}LOCALAPPDATA environment variable not found.")
    potential_paths = [
        Path(local_appdata) / 'Programs' / 'Zalo',
        Path(local_appdata) / 'Zalo'
    ]
    for path in potential_paths:
        if path.is_dir():
            if any(parse_version(entry.name) for entry in path.iterdir() if entry.is_dir()):
                 print(f"{COLOR_INFO}[*] Using Zalo base path: {COLOR_HIGHLIGHT}{path}{Style.RESET_ALL}")
                 return path
    programs_path = Path(local_appdata) / 'Programs'
    if programs_path.is_dir():
        for entry in programs_path.iterdir():
             if entry.is_dir() and entry.name.lower().startswith(('zalo-', 'zalopc-')):
                 parent_dir = entry.parent
                 print(f"{COLOR_INFO}[*] Found Zalo version folder '{entry.name}', using base path: {COLOR_HIGHLIGHT}{parent_dir}{Style.RESET_ALL}")
                 return parent_dir

    raise EnvironmentError(f"{COLOR_ERROR}Could not automatically determine Zalo installation path containing version folders in expected locations like {potential_paths} or {programs_path}")


def parse_version(name: str) -> Optional[Tuple[int, int, int]]:
    """Parses a version tuple (major, minor, patch) from a folder name like 'Zalo-x.y.z'."""
    match = re.match(r"^(ZaloPC|Zalo)-(\d+)\.(\d+)\.(\d+)", name, re.IGNORECASE)
    if match:
        return tuple(map(int, match.groups()[1:]))
    return None

def extract_asar(asar_path: Path, extract_to: Path) -> bool:
    """
    Extracts an ASAR archive using the 'asar' command-line tool using absolute paths.
    Returns True on success, False on failure.
    """
    asar_executable = get_asar_executable()
    if not asar_executable or not shutil.which(asar_executable):
         print(f"{COLOR_ERROR}[!] Error: Could not find or verify 'asar' executable ('{asar_executable}').")
         print(f"{COLOR_ERROR}    Please ensure Node.js and npm are installed correctly.")
         print(f"{COLOR_ERROR}    Run: npm install -g asar")
         print(f"{COLOR_ERROR}    Verify the npm global bin directory is in your system's PATH.")
         return False

    print(f"{COLOR_INFO}[*] Using asar executable: {Style.BRIGHT}{asar_executable}{Style.NORMAL}")

    if not asar_path.is_file():
        print(f"{COLOR_ERROR}[!] Error: Input ASAR file not found: {COLOR_HIGHLIGHT}{asar_path}{Style.RESET_ALL}")
        return False

    # If extract_to (the temporary unpacked folder) exists, remove it
    if extract_to.exists():
        print(f"{COLOR_INFO}[*] Removing existing temporary extraction directory: {COLOR_HIGHLIGHT}{extract_to}{Style.RESET_ALL}")
        try:
            shutil.rmtree(extract_to)
            time.sleep(0.5)
        except OSError as e:
            print(f"{COLOR_ERROR}[!] Error removing existing directory {COLOR_HIGHLIGHT}{extract_to}{Style.RESET_ALL}: {e}")
            print(f"{COLOR_ERROR}    Please check permissions or if Zalo is running.")
            return False

    print(f"{COLOR_INFO}[*] Creating extraction directory: {COLOR_HIGHLIGHT}{extract_to}{Style.RESET_ALL}")
    try:
        extract_to.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"{COLOR_ERROR}[!] Error creating directory {COLOR_HIGHLIGHT}{extract_to}{Style.RESET_ALL}: {e}")
        return False

    print(f"{COLOR_INFO}[*] Extracting {COLOR_HIGHLIGHT}{asar_path}{COLOR_INFO} to {COLOR_HIGHLIGHT}{extract_to}{Style.RESET_ALL}")
    command = [asar_executable, 'extract', str(asar_path), str(extract_to)]
    print(f"{COLOR_INFO}[*] Running command: {' '.join(command)}")

    try:
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, encoding='utf-8'
        )
        print(f"{COLOR_SUCCESS}[+] Extraction complete!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{COLOR_ERROR}[!] Extraction failed (code {e.returncode}):")
        print(f"{COLOR_ERROR}    Command: {' '.join(e.cmd)}")
        print(f"{Fore.RED}    Stderr: {e.stderr.strip() if e.stderr else 'N/A'}")
        print(f"    Stdout: {e.stdout.strip() if e.stdout else 'N/A'}")
        return False
    except FileNotFoundError:
        print(f"{COLOR_ERROR}[!] Error: Could not execute '{asar_executable}'. Path issue?")
        return False
    except Exception as e:
        print(f"{COLOR_ERROR}[!] Unexpected error during extraction: {e}")
        return False

# --- REPACK_ASAR FUNCTION IS NO LONGER NEEDED AND WILL BE REMOVED/COMMENTED ---
# def repack_asar(source_dir: Path, output_asar_path: Path) -> bool:
#     ... (original repack_asar code) ...

def download_file(url: str, destination_path: Path) -> bool:
    """Downloads a file from a URL and saves it. Returns True on success."""
    print(f"{COLOR_INFO}[*] Downloading {url} to {COLOR_HIGHLIGHT}{destination_path}{Style.RESET_ALL}")
    try:
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        with requests.Session() as session:
            response = session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            with open(destination_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            print(f"{COLOR_SUCCESS}[+] Successfully downloaded file to {COLOR_HIGHLIGHT}{destination_path}{Style.RESET_ALL}")
            return True
    except requests.exceptions.RequestException as e:
        print(f"{COLOR_ERROR}[!] Error downloading file: {e}")
        if destination_path.exists():
            try: destination_path.unlink(missing_ok=True) # Python 3.8+
            except AttributeError: # For Python < 3.8
                if destination_path.exists(): destination_path.unlink()
            except OSError: pass
        return False
    except OSError as e:
        print(f"{COLOR_ERROR}[!] Error saving file to {COLOR_HIGHLIGHT}{destination_path}{Style.RESET_ALL}: {e}")
        return False
    except Exception as e:
        print(f"{COLOR_ERROR}[!] An unexpected error occurred during download: {e}")
        return False

def inject_script_to_html(html_path: Path, script_src: str, marker: str) -> bool:
    """Injects script tag into HTML before marker. Returns True on success/already present."""
    print(f"{COLOR_INFO}[*] Attempting to inject script into: {COLOR_HIGHLIGHT}{html_path}{Style.RESET_ALL}")
    if not html_path.is_file():
        print(f"{COLOR_WARNING}[!] HTML file not found initially. Retrying in 1 second...")
        time.sleep(1)
        if not html_path.is_file():
            print(f"{COLOR_ERROR}[!] Error: HTML file still not found after delay: {COLOR_HIGHLIGHT}{html_path}{Style.RESET_ALL}")
            print(f"{COLOR_ERROR}    Please verify the extraction process completed successfully and the path is correct.")
            return False

    script_tag = f'<script src="{script_src}"></script>'
    marker_lower = marker.lower()

    try:
        content = None
        detected_encoding = 'utf-8'
        for encoding in ['utf-8', 'cp1252', 'latin-1']:
            try:
                content = html_path.read_text(encoding=encoding)
                detected_encoding = encoding
                print(f"{COLOR_INFO}[*] Successfully read HTML file with encoding: {encoding}")
                break
            except UnicodeDecodeError:
                 print(f"{COLOR_INFO}[*] Failed to read HTML with encoding {encoding}, trying next...")
            except Exception as read_err:
                print(f"{COLOR_ERROR}[!] Error reading HTML file {COLOR_HIGHLIGHT}{html_path}{Style.RESET_ALL}: {read_err}")
                return False

        if content is None:
            print(f"{COLOR_ERROR}[!] Error: Could not decode HTML file {COLOR_HIGHLIGHT}{html_path}{Style.RESET_ALL} with common encodings.")
            return False

        content_lower = content.lower()
        try:
            insert_pos = content_lower.rindex(marker_lower)
        except ValueError:
            print(f"{COLOR_ERROR}[!] Error: Injection marker '{marker}' not found in {COLOR_HIGHLIGHT}{html_path}{Style.RESET_ALL}")
            return False

        preceding_content = content[max(0, insert_pos - len(script_tag) - 10):insert_pos]
        if script_tag in preceding_content:
             print(f"{COLOR_SUCCESS}[+] Script tag '{script_tag}' already appears to be injected.")
             return True

        new_content = content[:insert_pos] + script_tag + "\n" + content[insert_pos:]
        html_path.write_text(new_content, encoding=detected_encoding)
        print(f"{COLOR_SUCCESS}[+] Successfully injected script tag into {COLOR_HIGHLIGHT}{html_path}{Style.RESET_ALL}")
        return True

    except OSError as e:
        print(f"{COLOR_ERROR}[!] Error reading/writing HTML file {COLOR_HIGHLIGHT}{html_path}{Style.RESET_ALL}: {e}")
        return False
    except Exception as e:
        print(f"{COLOR_ERROR}[!] An unexpected error occurred during script injection: {e}")
        return False

def find_latest_zalo() -> None:
    """Finds Zalo, extracts app.asar, modifies it, then replaces original app.asar
       with the modified unpacked folder, keeping a backup of the original file."""
    print(f"{COLOR_IMPORTANT}[!] Important: Please ensure the Zalo application is completely closed before running this script.")
    print(f"{COLOR_IMPORTANT}    Check Task Manager for any running Zalo processes (Zalo.exe, ZaloApp.exe, etc.).")
    time.sleep(3)

    try:
        base_path = get_zalo_base_path()
    except EnvironmentError as e:
        print(f"{COLOR_ERROR}[!] Error: {e}")
        return

    print(f"{COLOR_INFO}[*] Looking for Zalo version folders in: {COLOR_HIGHLIGHT}{base_path}{Style.RESET_ALL}")
    if not base_path.is_dir():
        print(f"{COLOR_ERROR}[!] Base path does not exist or is not a directory: {COLOR_HIGHLIGHT}{base_path}{Style.RESET_ALL}")
        return

    latest_version: Optional[Tuple[int, int, int]] = None
    latest_folder: Optional[Path] = None
    found_folders = []

    print(f"{COLOR_INFO}[*] Scanning directories...")
    for entry in base_path.iterdir():
        if entry.is_dir():
            version = parse_version(entry.name)
            if version:
                found_folders.append((version, entry))
                print(f"{COLOR_INFO}    - Found potential version folder: {entry.name} ({version})")

    if not found_folders:
        print(Style.BRIGHT + Fore.RED + "-" * 30)
        print(f"{COLOR_ERROR}[!] No valid Zalo version folder (e.g., 'Zalo-x.y.z') found in {COLOR_HIGHLIGHT}{base_path}{Style.RESET_ALL}!")
        return

    found_folders.sort(key=lambda x: x[0], reverse=True)
    latest_version, latest_folder = found_folders[0]

    version_str = '.'.join(map(str, latest_version))
    resources_folder = latest_folder / 'resources'
    # --- Paths for the new strategy ---
    original_asar_path = resources_folder / ORIGINAL_ASAR_FILENAME  # e.g., .../resources/app.asar
    backup_asar_path = resources_folder / BACKUP_ASAR_FILENAME      # e.g., .../resources/app.asar.bak
    unpacked_temp_dir = resources_folder / UNPACKED_DIR_NAME        # e.g., .../resources/unpacked_temp
    # This will be the final name of our modified folder, replacing the original asar file
    target_asar_folder_path = resources_folder / ORIGINAL_ASAR_FILENAME # e.g., .../resources/app.asar (as a folder)


    print(Style.BRIGHT + "-" * 30 + Style.RESET_ALL)
    print(f"{COLOR_SUCCESS}[+] Found latest Zalo folder: {COLOR_HIGHLIGHT}{latest_folder}{Style.RESET_ALL}")
    print(f"{COLOR_SUCCESS}[+] Latest Version: {Style.BRIGHT}{version_str}{Style.NORMAL}")
    print(f"{COLOR_INFO}[*] Resources folder: {COLOR_HIGHLIGHT}{resources_folder}{Style.RESET_ALL}")
    print(f"{COLOR_INFO}[*] Original ASAR target: {COLOR_HIGHLIGHT}{original_asar_path}{Style.RESET_ALL}") # Will be file or dir
    print(f"{COLOR_INFO}[*] Temporary extraction path (if needed): {COLOR_HIGHLIGHT}{unpacked_temp_dir}{Style.RESET_ALL}")

    # --- Determine current state of app.asar (file or directory) ---
    is_asar_already_a_directory = False
    if original_asar_path.is_dir():
        # Check if it looks like a valid unpacked app.asar directory
        if (original_asar_path / TARGET_HTML_SUBDIR / TARGET_HTML_FILENAME).exists():
            print(f"{COLOR_WARNING}[!] '{ORIGINAL_ASAR_FILENAME}' is already a directory. Script might have run before.")
            print(f"{COLOR_WARNING}    Attempting to inject script directly into this existing directory.")
            # Set unpacked_temp_dir to the existing directory to proceed with injection
            unpacked_temp_dir = original_asar_path # Work directly on the existing dir
            is_asar_already_a_directory = True
        else:
            print(f"{COLOR_ERROR}[!] Error: '{ORIGINAL_ASAR_FILENAME}' is a directory, but not a valid unpacked structure.")
            print(f"{COLOR_ERROR}    Location: {COLOR_HIGHLIGHT}{original_asar_path}{Style.RESET_ALL}")
            if backup_asar_path.exists():
                print(f"{COLOR_INFO}    A backup file '{BACKUP_ASAR_FILENAME}' exists. You might want to restore it manually.")
            return
    elif not original_asar_path.is_file():
        print(f"{COLOR_ERROR}[!] Error: '{ORIGINAL_ASAR_FILENAME}' not found as a file or a valid directory.")
        print(f"{COLOR_ERROR}    Location: {COLOR_HIGHLIGHT}{original_asar_path}{Style.RESET_ALL}")
        if backup_asar_path.exists():
            print(f"{COLOR_INFO}    A backup file '{BACKUP_ASAR_FILENAME}' exists. You might want to restore it manually.")
        return

    # --- Step 1: Extract ASAR (if it's a file) ---
    if not is_asar_already_a_directory: # Only extract if app.asar is currently a file
        print(f"\n{COLOR_STEP}--- Step 1: Extracting ASAR file ---{Style.RESET_ALL}")
        if not extract_asar(original_asar_path, unpacked_temp_dir): # Extract to unpacked_temp_dir
            print(f"{COLOR_ERROR}[!] Aborting due to ASAR extraction failure.")
            return
    else:
        print(f"\n{COLOR_STEP}--- Step 1: Skipped (ASAR is already a directory) ---{Style.RESET_ALL}")


    # --- Step 2: Download Custom Script ---
    print(f"\n{COLOR_STEP}--- Step 2: Downloading Custom Script ---{Style.RESET_ALL}")
    # Script destination is inside the (potentially temporarily named) unpacked folder
    script_destination_dir = unpacked_temp_dir / TARGET_HTML_SUBDIR
    custom_script_path = script_destination_dir / CUSTOM_SCRIPT_FILENAME

    if not download_file(CUSTOM_SCRIPT_URL, custom_script_path):
        print(f"{COLOR_ERROR}[!] Aborting due to script download failure.")
        # Only clean up unpacked_temp_dir if it was freshly extracted (i.e., not if app.asar was already a dir)
        if not is_asar_already_a_directory and unpacked_temp_dir.exists():
             print(f"{COLOR_INFO}[*] Cleaning up temporary extraction directory: {COLOR_HIGHLIGHT}{unpacked_temp_dir}{Style.RESET_ALL}")
             shutil.rmtree(unpacked_temp_dir, ignore_errors=True)
        return

    # --- Step 3: Inject Script into HTML ---
    print(f"\n{COLOR_STEP}--- Step 3: Injecting Script into HTML ---{Style.RESET_ALL}")
    html_path = script_destination_dir / TARGET_HTML_FILENAME
    script_relative_src = f"./{CUSTOM_SCRIPT_FILENAME}"

    injection_successful = inject_script_to_html(html_path, script_relative_src, INJECTION_MARKER)
    if not injection_successful:
        print(f"{COLOR_ERROR}[!] Script injection failed.")
        print(f"{COLOR_ERROR}[!] Aborting before modifying ASAR file/folder structure.")
        if not is_asar_already_a_directory and unpacked_temp_dir.exists():
             print(f"{COLOR_INFO}[*] Cleaning up temporary extraction directory: {COLOR_HIGHLIGHT}{unpacked_temp_dir}{Style.RESET_ALL}")
             shutil.rmtree(unpacked_temp_dir, ignore_errors=True)
        return

    # --- Step 4: Backup original app.asar (file) and rename unpacked folder ---
    # This step only runs if original_asar_path was initially a file and extraction happened.
    # If it was already a directory, we just modified it in place.

    if not is_asar_already_a_directory:
        print(f"\n{COLOR_STEP}--- Step 4: Replacing ASAR file with modified folder ---{Style.RESET_ALL}")

        # 4a. Rename original app.asar (file) to app.asar.bak
        print(f"{COLOR_INFO}[*] Backing up original '{ORIGINAL_ASAR_FILENAME}' (file) to '{BACKUP_ASAR_FILENAME}'...")
        try:
            # If backup already exists, remove it first to avoid error on rename
            if backup_asar_path.exists():
                print(f"{COLOR_WARNING}    Existing backup '{BACKUP_ASAR_FILENAME}' found. Replacing it.")
                if backup_asar_path.is_dir(): # Should be a file, but check just in case
                    shutil.rmtree(backup_asar_path)
                else:
                    backup_asar_path.unlink(missing_ok=True) # Python 3.8+
                time.sleep(0.2)
            original_asar_path.rename(backup_asar_path)
            print(f"{COLOR_SUCCESS}[+] Original ASAR file backed up to: {COLOR_HIGHLIGHT}{backup_asar_path}{Style.RESET_ALL}")
        except OSError as e:
            print(f"{COLOR_ERROR}[!] Error backing up original ASAR file: {e}")
            print(f"{COLOR_ERROR}    Please ensure Zalo is closed and you have permissions.")
            print(f"{COLOR_ERROR}    Aborting. Modified files are in {COLOR_HIGHLIGHT}{unpacked_temp_dir}{Style.RESET_ALL}")
            # Attempt to restore original_asar_path if backup failed mid-way (unlikely but cautious)
            # This is complex as original_asar_path might not exist if rename started
            return

        # 4b. Rename the unpacked_temp_dir to app.asar (which is target_asar_folder_path)
        print(f"{COLOR_INFO}[*] Renaming '{UNPACKED_DIR_NAME}' to '{ORIGINAL_ASAR_FILENAME}' (as a folder)...")
        try:
            # If target_asar_folder_path (app.asar) somehow exists as a file now (it shouldn't if backup worked), remove it.
            if target_asar_folder_path.is_file():
                print(f"{COLOR_WARNING}    '{ORIGINAL_ASAR_FILENAME}' unexpectedly exists as a file before renaming folder. Removing it.")
                target_asar_folder_path.unlink(missing_ok=True)

            unpacked_temp_dir.rename(target_asar_folder_path)
            print(f"{COLOR_SUCCESS}[+] Modified folder renamed to: {COLOR_HIGHLIGHT}{target_asar_folder_path}{Style.RESET_ALL}")
        except OSError as e:
            print(f"{COLOR_ERROR}[!] Error renaming '{UNPACKED_DIR_NAME}' to '{ORIGINAL_ASAR_FILENAME}': {e}")
            print(f"{COLOR_ERROR}    The application might be in an inconsistent state.")
            print(f"{COLOR_INFO}    Original backup: {COLOR_HIGHLIGHT}{backup_asar_path}{Style.RESET_ALL} (SHOULD BE A FILE)")
            print(f"{COLOR_INFO}    Modified files (not renamed): {COLOR_HIGHLIGHT}{unpacked_temp_dir}{Style.RESET_ALL}")
            print(f"{COLOR_IMPORTANT}    Attempting to restore backup...")
            try:
                if backup_asar_path.is_file(): # Ensure backup is a file
                    # If target_asar_folder_path exists as a dir (failed rename), remove it
                    if target_asar_folder_path.is_dir() and target_asar_folder_path.name == ORIGINAL_ASAR_FILENAME:
                        shutil.rmtree(target_asar_folder_path)
                    backup_asar_path.rename(original_asar_path)
                    print(f"{COLOR_SUCCESS}    Successfully restored backup '{BACKUP_ASAR_FILENAME}' to '{ORIGINAL_ASAR_FILENAME}'.")
                else:
                    print(f"{COLOR_ERROR}    Backup '{BACKUP_ASAR_FILENAME}' is not a file or doesn't exist. Cannot restore automatically.")
            except Exception as restore_e:
                print(f"{COLOR_ERROR}    Automatic restore failed: {restore_e}")
            print(f"{COLOR_IMPORTANT}    Please manually check the 'resources' folder.")
            return
    else: # This means app.asar was already a directory
        print(f"\n{COLOR_STEP}--- Step 4: Modification Complete (ASAR was already a directory) ---{Style.RESET_ALL}")
        print(f"{COLOR_INFO}[*] '{ORIGINAL_ASAR_FILENAME}' was already a directory. Modifications applied in place.")
        # No specific message about backup here as no file was backed up in this run if it was already a dir.


    # --- Step 5: Finalizing (No explicit cleanup of unpacked_temp_dir as it became the new app.asar or was the existing app.asar dir) ---
    print(f"\n{COLOR_STEP}--- Step 5: Finalizing ---{Style.RESET_ALL}")
    if not is_asar_already_a_directory and backup_asar_path.exists():
        print(f"{COLOR_INFO}[*] The original '{ORIGINAL_ASAR_FILENAME}' (file) is backed up as '{BACKUP_ASAR_FILENAME}'.")
    elif is_asar_already_a_directory and backup_asar_path.exists():
         print(f"{COLOR_INFO}[*] A backup file '{BACKUP_ASAR_FILENAME}' exists from a previous run.")
    print(f"{COLOR_INFO}[*] The modified content is now at: {COLOR_HIGHLIGHT}{target_asar_folder_path}{Style.RESET_ALL} (as a folder).")


    # --- Final Success Message ---
    print(Style.BRIGHT + Fore.RESET + "-" * 30) # Use Fore.RESET to avoid green line
    print(f"{Style.BRIGHT}{Fore.GREEN}[SUCCESS] Script finished successfully!{Style.RESET_ALL}")
    if not is_asar_already_a_directory and backup_asar_path.exists(): # Only show backup message if a backup was made *in this run*
        print(f"{Fore.GREEN}          - Original '{ORIGINAL_ASAR_FILENAME}' (file) backed up to: {COLOR_HIGHLIGHT}{backup_asar_path}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}          - Zalo will now load from the modified folder: {COLOR_HIGHLIGHT}{target_asar_folder_path}{Style.RESET_ALL}")
    print(f"\n{Style.BRIGHT}{Fore.YELLOW}          You may need to RESTART Zalo completely for changes to take effect.")
    print(f"{Style.BRIGHT}{Fore.YELLOW}          (Check Task Manager for Zalo processes).")
    if backup_asar_path.exists(): # Offer revert instructions if any backup exists
        print(f"\n{Style.BRIGHT}{Fore.CYAN}          To revert: Delete the '{ORIGINAL_ASAR_FILENAME}' FOLDER, then rename '{BACKUP_ASAR_FILENAME}' back to '{ORIGINAL_ASAR_FILENAME}'.{Style.RESET_ALL}")


if __name__ == "__main__":
    # Add a note about colorama requirement
    try:
        import colorama
    except ImportError:
        print("Requirement 'colorama' not found. Colors will not be displayed.")
        print("Please install it using: pip install colorama")
        # Define dummy Fore and Style if colorama is missing
        class DummyStyle:
            def __getattr__(self, name): return ""
        Fore = DummyStyle()
        Style = DummyStyle()

    find_latest_zalo()
    # Use default color for the final prompt
    input(f"\n{Style.RESET_ALL}Press Enter to exit...")
