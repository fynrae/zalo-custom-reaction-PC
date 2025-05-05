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

    if extract_to.exists():
        print(f"{COLOR_INFO}[*] Removing existing extraction directory: {COLOR_HIGHLIGHT}{extract_to}{Style.RESET_ALL}")
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
        # Use Fore.RED for stderr, maybe default for stdout if needed
        print(f"{Fore.RED}    Stderr: {e.stderr.strip() if e.stderr else 'N/A'}")
        print(f"    Stdout: {e.stdout.strip() if e.stdout else 'N/A'}")
        return False
    except FileNotFoundError:
        print(f"{COLOR_ERROR}[!] Error: Could not execute '{asar_executable}'. Path issue?")
        return False
    except Exception as e:
        print(f"{COLOR_ERROR}[!] Unexpected error during extraction: {e}")
        return False

def repack_asar(source_dir: Path, output_asar_path: Path) -> bool:
    """
    Repacks a directory into an ASAR archive, overwriting the output file.
    Returns True on success, False on failure.
    """
    asar_executable = get_asar_executable()
    if not asar_executable or not shutil.which(asar_executable):
         print(f"{COLOR_ERROR}[!] Error: Could not find or verify 'asar' executable ('{asar_executable}') for repacking.")
         return False

    print(f"{COLOR_INFO}[*] Using asar executable: {Style.BRIGHT}{asar_executable}{Style.NORMAL}")

    if not source_dir.is_dir():
        print(f"{COLOR_ERROR}[!] Error: Source directory for repacking not found: {COLOR_HIGHLIGHT}{source_dir}{Style.RESET_ALL}")
        print(f"{COLOR_ERROR}    Extraction might have failed earlier.")
        return False

    if output_asar_path.exists():
        print(f"{COLOR_INFO}[*] Removing existing target ASAR file: {COLOR_HIGHLIGHT}{output_asar_path}{Style.RESET_ALL}")
        try:
            output_asar_path.unlink()
            time.sleep(0.2)
        except OSError as e:
            print(f"{COLOR_WARNING}[!] Warning: Could not remove existing {COLOR_HIGHLIGHT}{output_asar_path}{Style.RESET_ALL}: {e}")
            print(f"{COLOR_WARNING}    This might be okay if 'asar pack' can overwrite.")
            print(f"{COLOR_WARNING}    Ensure Zalo is not running if repacking fails.")

    print(f"{COLOR_INFO}[*] Repacking {COLOR_HIGHLIGHT}{source_dir}{COLOR_INFO} to {COLOR_HIGHLIGHT}{output_asar_path}{Style.RESET_ALL}")
    command = [asar_executable, 'pack', str(source_dir), str(output_asar_path)]
    print(f"{COLOR_INFO}[*] Running command: {' '.join(command)}")

    try:
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, encoding='utf-8'
        )
        print(f"{COLOR_SUCCESS}[+] Repacking complete!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{COLOR_ERROR}[!] Repacking failed (code {e.returncode}):")
        print(f"{COLOR_ERROR}    Command: {' '.join(e.cmd)}")
        print(f"{Fore.RED}    Stderr: {e.stderr.strip() if e.stderr else 'N/A'}")
        print(f"    Stdout: {e.stdout.strip() if e.stdout else 'N/A'}")
        print(f"{COLOR_ERROR}[!] Ensure Zalo application is completely closed (check Task Manager).")
        return False
    except FileNotFoundError:
        print(f"{COLOR_ERROR}[!] Error: Could not execute '{asar_executable}'. Path issue?")
        return False
    except Exception as e:
        print(f"{COLOR_ERROR}[!] Unexpected error during repacking: {e}")
        return False

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
            try: destination_path.unlink()
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
    """Finds the latest installed Zalo version, extracts its app.asar,
       downloads a custom script, injects it into index.html, repacks the asar,
       and cleans up."""
    print(f"{COLOR_IMPORTANT}[!] Important: Please ensure the Zalo application is completely closed before running this script.")
    print(f"{COLOR_IMPORTANT}    Check Task Manager for any running Zalo processes.")
    time.sleep(3) # Give user more time to read

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
                # Use a slightly dimmer color for found folders unless it's the latest? Or just keep info
                print(f"{COLOR_INFO}    - Found potential version folder: {entry.name} ({version})")

    if not found_folders:
        print(Style.BRIGHT + Fore.RED + "-" * 30)
        print(f"{COLOR_ERROR}[!] No valid Zalo version folder (e.g., 'Zalo-x.y.z') found in {COLOR_HIGHLIGHT}{base_path}{Style.RESET_ALL}!")
        return

    found_folders.sort(key=lambda x: x[0], reverse=True)
    latest_version, latest_folder = found_folders[0]

    version_str = '.'.join(map(str, latest_version))
    resources_folder = latest_folder / 'resources'
    asar_path = resources_folder / 'app.asar'
    unpacked_folder = resources_folder / 'unpacked'

    print(Style.BRIGHT + "-" * 30 + Style.RESET_ALL) # Separator
    print(f"{COLOR_SUCCESS}[+] Found latest Zalo folder: {COLOR_HIGHLIGHT}{latest_folder}{Style.RESET_ALL}")
    print(f"{COLOR_SUCCESS}[+] Latest Version: {Style.BRIGHT}{version_str}{Style.NORMAL}")
    print(f"{COLOR_INFO}[*] Resources folder: {COLOR_HIGHLIGHT}{resources_folder}{Style.RESET_ALL}")
    print(f"{COLOR_INFO}[*] Target ASAR path: {COLOR_HIGHLIGHT}{asar_path}{Style.RESET_ALL}")
    print(f"{COLOR_INFO}[*] Temporary extraction path: {COLOR_HIGHLIGHT}{unpacked_folder}{Style.RESET_ALL}")

    if not asar_path.is_file():
        print(f"{COLOR_ERROR}[!] Error: app.asar not found at the expected location: {COLOR_HIGHLIGHT}{asar_path}{Style.RESET_ALL}")
        return

    # --- Step 1: Extract ASAR ---
    print(f"\n{COLOR_STEP}--- Step 1: Extracting ASAR ---{Style.RESET_ALL}")
    if not extract_asar(asar_path, unpacked_folder):
        print(f"{COLOR_ERROR}[!] Aborting due to ASAR extraction failure.")
        return

    # --- Step 2: Download Custom Script ---
    print(f"\n{COLOR_STEP}--- Step 2: Downloading Custom Script ---{Style.RESET_ALL}")
    script_destination_dir = unpacked_folder / TARGET_HTML_SUBDIR
    custom_script_path = script_destination_dir / CUSTOM_SCRIPT_FILENAME

    if not download_file(CUSTOM_SCRIPT_URL, custom_script_path):
        print(f"{COLOR_ERROR}[!] Aborting due to script download failure.")
        if unpacked_folder.exists():
             print(f"{COLOR_INFO}[*] Cleaning up temporary directory: {COLOR_HIGHLIGHT}{unpacked_folder}{Style.RESET_ALL}")
             shutil.rmtree(unpacked_folder, ignore_errors=True)
        return

    # --- Step 3: Inject Script into HTML ---
    print(f"\n{COLOR_STEP}--- Step 3: Injecting Script into HTML ---{Style.RESET_ALL}")
    html_path = script_destination_dir / TARGET_HTML_FILENAME
    script_relative_src = f"./{CUSTOM_SCRIPT_FILENAME}"

    injection_successful = inject_script_to_html(html_path, script_relative_src, INJECTION_MARKER)
    if not injection_successful:
        print(f"{COLOR_ERROR}[!] Script injection failed.")
        print(f"{COLOR_ERROR}[!] Aborting before repacking.")
        if unpacked_folder.exists():
             print(f"{COLOR_INFO}[*] Cleaning up temporary directory: {COLOR_HIGHLIGHT}{unpacked_folder}{Style.RESET_ALL}")
             shutil.rmtree(unpacked_folder, ignore_errors=True)
        return

    # --- Step 4: Repack ASAR ---
    print(f"\n{COLOR_STEP}--- Step 4: Repacking modified files into ASAR ---{Style.RESET_ALL}")
    repack_successful = repack_asar(unpacked_folder, asar_path)
    if not repack_successful:
        print(f"{COLOR_ERROR}[!] Repacking failed. The original app.asar might still be in place or corrupted.")
        print(f"{COLOR_WARNING}    The unpacked files are kept in case you need to inspect them:")
        print(f"{COLOR_HIGHLIGHT}    {unpacked_folder}{Style.RESET_ALL}")
        return

    # --- Step 5: Cleanup ---
    print(f"\n{COLOR_STEP}--- Step 5: Cleaning up temporary directory ---{Style.RESET_ALL}")
    if repack_successful and unpacked_folder.exists():
        print(f"{COLOR_INFO}[*] Removing temporary directory: {COLOR_HIGHLIGHT}{unpacked_folder}{Style.RESET_ALL}")
        try:
            shutil.rmtree(unpacked_folder)
            print(f"{COLOR_SUCCESS}[+] Cleanup complete.")
        except OSError as e:
            print(f"{COLOR_WARNING}[!] Warning: Could not remove temporary directory {COLOR_HIGHLIGHT}{unpacked_folder}{Style.RESET_ALL}: {e}")
            print(f"{COLOR_WARNING}    You may need to remove it manually.")

    # --- Final Success Message ---
    print(Style.BRIGHT + Fore.RESET + "-" * 30)
    print(f"{Style.BRIGHT}{Fore.GREEN}[SUCCESS] Script finished successfully!{Style.RESET_ALL}")
    print(f"{Fore.GREEN}          - Modified and repacked: {COLOR_HIGHLIGHT}{asar_path}{Style.RESET_ALL}")
    print(f"\n{Style.BRIGHT}{Fore.YELLOW}          You may need to RESTART Zalo completely for changes to take effect.")
    print(f"{Style.BRIGHT}{Fore.YELLOW}          (Check Task Manager to ensure no Zalo processes are running before restarting).{Style.RESET_ALL}")


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
