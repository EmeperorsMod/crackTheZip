import subprocess
import os
import time
from datetime import datetime
import sys
import string

def expand_pool_chars(token_string):
    mappings = {
        "?l": string.ascii_lowercase,
        "?u": string.ascii_uppercase,
        "?w": string.ascii_lowercase + string.ascii_uppercase,
        "?d": string.digits,
        "?1": string.digits,
        "?s": string.punctuation + " ",
        "?a": string.ascii_letters + string.digits + string.punctuation + " "
    }
    
    if '?' not in token_string:
        return "".join(sorted(set(token_string), key=token_string.index))
        
    expanded = ""
    i = 0
    while i < len(token_string):
        if token_string[i] == '?' and i + 1 < len(token_string):
            token = token_string[i:i+2]
            expanded += mappings.get(token, token)
            i += 2
        else:
            expanded += token_string[i]
            i += 1
            
    return "".join(sorted(set(expanded), key=expanded.index))

def parse_positional_mask(pattern):
    mappings = {
        "?l": string.ascii_lowercase,
        "?u": string.ascii_uppercase,
        "?w": string.ascii_lowercase + string.ascii_uppercase,
        "?d": string.digits,
        "?1": string.digits,
        "?s": string.punctuation + "@",
        "?a": string.ascii_letters + string.digits + string.punctuation + " "
    }
    
    pools = []
    i = 0
    while i < len(pattern):
        if pattern[i] == '?' and i + 1 < len(pattern):
            token = pattern[i:i+2]
            pools.append(mappings.get(token, token))
            i += 2
        else:
            pools.append(pattern[i])
            i += 1
            
    return pools

# ================= CONFIGURATION =================
script_dir = r"/mnt/c/Users/HP/Documents/script"
hashcat_bin = os.path.join(script_dir, "hashcat.exe")
potfile_path = os.path.join(script_dir, "hashcat.potfile")

current_dir = os.path.dirname(os.path.abspath(__file__))
hash_txt_file = os.path.join(current_dir, "hash.txt")

hash_file_wsl = os.path.join(script_dir, "extracted_hash.txt")
hash_file_name = "extracted_hash.txt"

found_file = "found_hashes.txt"
prefix = ""
suffix = ""

# Choose your mode: "pool" (brute-force charset combination) OR "positional" (strict slot rules)
mode = "pool"

# --- SETTINGS FOR "pool" MODE ---
char_pool_pattern = "?a"  # Uppercase letters OR digits
min_length = 1              # Target minimum length
max_length = 7              # Target maximum length
custom_pool_chars = ""

# --- SETTINGS FOR "positional" MODE ---
positional_pattern = "?d?d?d?d?u?d"
# =================================================

if not os.path.exists(hash_txt_file):
    print(f"[!] Error: Target hash file '{hash_txt_file}' not found!")
    exit(1)

if not os.path.exists(hashcat_bin):
    print(f"[!] Error: hashcat.exe not found at {hashcat_bin}")
    exit(1)

# Clean old potfile to ensure fresh detection for this run
if os.path.exists(potfile_path):
    try:
        os.remove(potfile_path)
    except Exception:
        pass

start_timestamp = time.time()
print(f"==================================================")
print(f"[*] Execution Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"[*] Target Hash Source: {hash_txt_file}")
print(f"[*] Active Mode: {mode.upper()} (Instant Loop Break on Crack)")
print(f"==================================================\n")

# Step 1: Copy hash file to script directory for Hashcat identification
with open(hash_txt_file, "r", encoding="utf-8", errors="ignore") as f_in:
    hashes_content = f_in.read()

with open(hash_file_wsl, "w", encoding="utf-8") as f_out:
    f_out.write(hashes_content)

print("[*] Running Hashcat built-in hash identifier (--identify)...")
id_cmd = [str(hashcat_bin), "--identify", hash_file_name]
id_result = subprocess.run(id_cmd, cwd=script_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

identified_modes = []
print("\n--- Hashcat Identification Results ---")
for line in id_result.stdout.splitlines():
    print(line)
    if "[" in line and "]" in line:
        try:
            mode_part = line.split("[")[1].split("]")[0].strip()
            if mode_part.isdigit():
                identified_modes.append((mode_part, line.strip()))
        except Exception:
            pass
print("--------------------------------------\n")

# Step 2: Prompt user to choose the correct mode number
if identified_modes:
    print("[*] Suggested Hashcat Modes detected above.")
    user_choice = input("[?] Enter the Hashcat mode number (-m) you want to use: ").strip()
    hash_mode = user_choice
else:
    print("[!] Automatic identification list empty or unrecognized.")
    hash_mode = input("[?] Enter the Hashcat mode number (-m) manually: ").strip()

if not hash_mode.isdigit():
    print("[!] Error: Invalid mode number entered.")
    if os.path.exists(hash_file_wsl):
        os.remove(hash_file_wsl)
    exit(1)

print(f"\n[+] Selected Hashcat Engine: Mode {hash_mode}\n")

# Step 3: Construct masks cleanly using native charset references
masks_to_try = []

if mode == "pool":
    # Keep the token pattern as-is so Hashcat handles the character lookup natively
    for total_len in range(min_length, max_length + 1):
        middle_length = total_len - len(prefix) - len(suffix)
        if middle_length < 0:
            continue
        middle_mask = "?1" * middle_length
        full_mask = f"{prefix}{middle_mask}{suffix}"
        masks_to_try.append((full_mask, char_pool_pattern, total_len))

elif mode == "positional":
    full_mask = f"{prefix}{positional_pattern}{suffix}"
    masks_to_try.append((full_mask, None, len(positional_pattern)))

success_password = None

# Step 4: Execute Hashcat safely
for current_mask, charset_def, target_len in masks_to_try:
    if success_password:
        break

    print(f"\n--------------------------------------------------")
    print(f"[*] Deploying Mask: {current_mask} | Target Length: {target_len}")
    print(f"[*] Running Hashcat...")
    print(f"--------------------------------------------------")
    
    cmd_hashcat = [
        str(hashcat_bin),
        "-m", str(hash_mode),
        "-a", "3",
        "-w", "3",
        "--status",
        "--status-timer=3"
    ]
    
    if charset_def:
        # Pass the pool pattern (e.g., ?u?d) safely into custom charset 1 (-1)
        cmd_hashcat.extend(["-1", charset_def])
        
    cmd_hashcat.extend([hash_file_name, current_mask])
    
    subprocess.run(cmd_hashcat, cwd=script_dir)
    
    cmd_show = [
        str(hashcat_bin), 
        "-m", str(hash_mode), 
        "--show", 
        hash_file_name
    ]
    result = subprocess.run(cmd_show, cwd=script_dir, capture_output=True, text=True)
    
    if result.returncode == 0 and result.stdout.strip():
        raw_output = result.stdout.strip()
        for line in raw_output.splitlines():
            if ":" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    success_password = parts[-1].strip()
                    break
        if success_password:
            print(f"\n[+] Password found at length {target_len}! Aborting remaining lengths.")
            break

# Clean up temp wsl hash file
if os.path.exists(hash_file_wsl):
    os.remove(hash_file_wsl)

# Output ONLY the password or failure notice cleanly
print(f"\n==================================================preparing")
if success_password:
    with open(found_file, "w", encoding="utf-8") as f:
        f.write(success_password + "\n")
    print(success_password)
else:
    print(f"[-] No matching password found within the configured mask settings.")
    
end_timestamp = time.time()
print(f"[*] Total Execution Time: {end_timestamp - start_timestamp:.2f} seconds")
print(f"==================================================\n")