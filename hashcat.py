import subprocess
import os
import time
from datetime import datetime
import sys

# --- CONFIGURATION ---
script_dir = r"/mnt/c/Users/HP/Documents/script"
hashcat_bin = os.path.join(script_dir, "hashcat.exe")
zip2john_bin = "/home/mjar/john/run/zip2john"

current_dir = os.path.dirname(os.path.abspath(__file__))
zip_file = os.path.join(current_dir, "Cr-@Ryff winstress..zip")

hash_file_wsl = os.path.join(script_dir, "extracted_hash.txt")
hash_file_name = "extracted_hash.txt"

prefix = ""
suffix = ""

# Choose your mode: "pool" (brute-force charset combination) OR "positional" (strict slot rules)
mode = "pool"

# --- SETTINGS FOR "pool" MODE ---
# Using built-in ?l (lowercase), ?d (digits), and ?1 (custom charset defined below for '@')
char_pool_pattern = "?l?d"
min_length = 4
max_length = 6
custom_pool_chars = ""  # Mapped to ?1

# --- SETTINGS FOR "positional" MODE ---
# Example: exact slot rules per character position
positional_pattern = "?l?l?1?d?d" 

if not os.path.exists(zip_file):
    print(f"[!] Error: Target archive {zip_file} not found!")
    exit(1)

if not os.path.exists(hashcat_bin):
    print(f"[!] Error: hashcat.exe not found at {hashcat_bin}")
    exit(1)

start_timestamp = time.time()
print(f"==================================================")
print(f"[*] Execution Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"[*] Target Archive: {zip_file}")
print(f"[*] Active Mode: {mode.upper()}")
print(f"==================================================\n")

# Step 1: Extract and completely sanitize hash output
print("[*] Step 1: Extracting and sanitizing hash for Hashcat...")
result_z2j = subprocess.run([str(zip2john_bin), str(zip_file)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

raw_output = result_z2j.stdout
extracted_hash = None

for line in raw_output.splitlines():
    for sig in ["$zip2$", "$pkzip$", "$winzip$"]:
        if sig in line:
            idx = line.index(sig)
            extracted_hash = line[idx:].strip()
            break
    if extracted_hash:
        break

if not extracted_hash:
    print("[!] Error: Could not parse a clean hash signature from zip2john output.")
    exit(1)

with open(hash_file_wsl, "w") as f_out:
    f_out.write(extracted_hash + "\n")

print(f"[+] Sanitized pure hash written successfully to {hash_file_wsl}\n")

# Step 2: Auto-detect hash mode type for Hashcat (-m)
if "$pkzip$" in extracted_hash:
    hash_type = "17200"
    print("[+] Algorithm Type: Traditional PKZip -> Hashcat Mode 17200")
else:
    hash_type = "13600"
    print("[+] Algorithm Type: WinZip AES -> Hashcat Mode 13600")

print(f"[+] Configured Hashcat Engine: Mode {hash_type}\n")

# Step 3: Construct masks based on selected mode
masks_to_try = []

if mode == "pool":
    for total_len in range(min_length, max_length + 1):
        middle_length = total_len - len(prefix) - len(suffix)
        if middle_length < 0:
            continue
        # Repeats the pool pattern (e.g. ?l?d?1) across the required length slots
        middle_mask = char_pool_pattern * middle_length
        full_mask = f"{prefix}{middle_mask}{suffix}"
        masks_to_try.append(full_mask)

elif mode == "positional":
    full_mask = f"{prefix}{positional_pattern}{suffix}"
    masks_to_try.append(full_mask)

success_pw = None

# Step 4: Execute Hashcat across generated masks
for current_mask in masks_to_try:
    print(f"\n--------------------------------------------------")
    print(f"[*] Deploying Hashcat Mask: {current_mask} (Length: {len(current_mask)})")
    print(f"--------------------------------------------------")
    
    cmd_hashcat = [
        str(hashcat_bin),
        "-m", str(hash_type),
        "-a", "3",
        "--potfile-disable",
        "--status",
        "--status-timer=10"
    ]
    
    # If the mask uses ?1, assign custom characters to charset -1
    if "?1" in current_mask:
        cmd_hashcat.extend(["-1", custom_pool_chars])
        
    cmd_hashcat.extend([hash_file_name, str(current_mask)])
    
    process = subprocess.Popen(cmd_hashcat, cwd=script_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        
    process.wait()
    
    cmd_show = [
        str(hashcat_bin), 
        "-m", str(hash_type), 
        "--show", 
        hash_file_name
    ]
    result = subprocess.run(cmd_show, cwd=script_dir, capture_output=True, text=True)
    
    if result.returncode == 0 and result.stdout.strip():
        output_lines = result.stdout.strip().splitlines()
        for line in output_lines:
            if ":" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    success_pw = parts[1].strip()
                    break
    if success_pw:
        break

if os.path.exists(hash_file_wsl):
    os.remove(hash_file_wsl)

if success_pw:
    print(f"\n==================================================")
    print(f"[+] SUCCESS! Working password identified: '{success_pw}'")
    print(f"==================================================\n")
    print(f"[*] Extracting archive contents...")
    extract_cmd = f'unzip -o -P "{success_pw}" "{zip_file}"'
    subprocess.run(extract_cmd, shell=True)
    print(f"[+] Archive extracted successfully!")
else:
    print(f"\n[-] Password not discovered within the configured settings.")

end_timestamp = time.time()
print(f"\n==================================================")
print(f"[*] Total Script Execution Time: {end_timestamp - start_timestamp:.2f} seconds")
print(f"==================================================\n")