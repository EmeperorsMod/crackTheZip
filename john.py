import subprocess
import os
import time
from datetime import datetime
import sys
import string

# Define Hashcat/John shorthand expansion for pool mode
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

# --- CONFIGURATION (WSL Paths) ---
zip_file = "Cr-@Ryff winstress..zip"
john_bin = "/home/mjar/john/run/john"
zip2john_bin = "/home/mjar/john/run/zip2john"
hash_file = "zip_hash.txt"

prefix = ""
suffix = ""

# Choose your mode: "pool" (random characters from a defined pool) OR "positional" (strict slot rules)
mode = "pool"

# --- SETTINGS FOR "pool" MODE ---
char_pool_pattern = "?l?d"  # Uppercase letters and digits
min_length = 4
max_length = 6

# --- SETTINGS FOR "positional" MODE ---
positional_pattern = "?d?d?d?d?u?d" 

if not os.path.exists(zip_file):
    print(f"[!] Error: {zip_file} missing!")
    exit(1)

start_timestamp = time.time()
print(f"==================================================")
print(f"[*] Execution Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"[*] Target Archive: {zip_file}")
print(f"[*] Active Mode: {mode.upper()} (John the Ripper with Live Progress)")
print(f"==================================================\n")

# Step 1: Extract hash for John using zip2john
print("[*] Extracting hash for John using zip2john...")
with open(hash_file, "w") as f_out:
    subprocess.run([zip2john_bin, zip_file], stdout=f_out, stderr=subprocess.DEVNULL)

if not os.path.exists(hash_file) or os.path.getsize(hash_file) == 0:
    print("[!] Error: Failed to extract hash using zip2john.")
    exit(1)

# Step 2: Build the mask based on the selected mode
masks_to_try = []

if mode == "pool":
    chars = expand_pool_chars(char_pool_pattern)
    john_char_set = f"[{chars}]"
    
    for total_len in range(min_length, max_length + 1):
        middle_length = total_len - len(prefix) - len(suffix)
        if middle_length < 0:
            continue
        middle_mask = john_char_set * middle_length
        full_mask = f"{prefix}{middle_mask}{suffix}"
        masks_to_try.append(full_mask)

elif mode == "positional":
    full_mask = f"{prefix}{positional_pattern}{suffix}"
    masks_to_try.append(full_mask)

success_pw = None

# Step 3: Run John for each generated mask pattern with live output streaming
for current_mask in masks_to_try:
    print(f"\n[*] Testing mask pattern: {current_mask}")
    cmd_john = [john_bin, f"--mask={current_mask}", hash_file]
    
    process = subprocess.Popen(cmd_john, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Stream John's output live so you can see progress, speed, and status updates
    for line in process.stdout:
        # Print John's status lines cleanly
        sys.stdout.write(line)
        sys.stdout.flush()
        
    process.wait()
    
    # Check if cracked successfully after this mask run
    cmd_show = [john_bin, "--show", hash_file]
    result = subprocess.run(cmd_show, capture_output=True, text=True)
    
    if result.returncode == 0 and result.stdout.strip():
        output_lines = result.stdout.strip().splitlines()
        for line in output_lines:
            if ":" in line and not line.startswith("0 password hashes"):
                parts = line.split(":")
                if len(parts) >= 2:
                    success_pw = parts[1].strip()
                    break
    if success_pw:
        break

# Clean up temporary hash file
if os.path.exists(hash_file):
    os.remove(hash_file)

if success_pw:
    print(f"\n[+] SUCCESS! Valid working password confirmed: '{success_pw}'")
    print(f"\n[*] Extracting archive using confirmed password...")
    extract_cmd = f'unzip -o -P "{success_pw}" "{zip_file}"'
    subprocess.run(extract_cmd, shell=True)
    print(f"[+] Archive extracted successfully!")
else:
    print(f"\n[-] Password not found across configured masks.")

end_timestamp = time.time()
print(f"\n==================================================")
print(f"[*] Total Execution Time: {end_timestamp - start_timestamp:.2f} seconds")
print(f"==================================================\n")