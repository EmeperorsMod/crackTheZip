import itertools
import os
import time
import zipfile
from zipfile import BadZipFile
from datetime import datetime
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

# --- Configuration ---
zip_file = "Asset FA set 2 2026(FA2026S2).zip"
found_file = "found_passwords.txt"
prefix = "FA"
suffix = ""

# Mode: "pool" or "positional"
mode = "pool"

# --- SETTINGS FOR "pool" MODE ---
char_pool_pattern = "?u206"
min_length = 8
max_length = 8

# --- SETTINGS FOR "positional" MODE ---
positional_pattern = "?d?d?d?d?u?d"

if not os.path.exists(zip_file):
    print(f"[!] Error: {zip_file} missing!")
    exit(1)

start_timestamp = time.time()
start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"==================================================")
print(f"[*] Execution Started at: {start_time_str}")
print(f"[*] Active Mode: {mode.upper()} (On-the-Fly In-Memory Testing)")
print(f"==================================================\n")

success_pw = None
tested_count = 0

try:
    with zipfile.ZipFile(zip_file) as zf:
        print(f"[*] Starting on-the-fly generation and testing...")
        
        # Find a file inside the zip that is actually encrypted (flag_bits & 1)
        target_info = None
        for info in zf.infolist():
            if info.flag_bits & 0x1:
                target_info = info
                break
                
        if not target_info:
            target_info = zf.infolist()[0]
            
        print(f"[*] Targeting internal file for validation: '{target_info.filename}' (Encrypted: {bool(target_info.flag_bits & 0x1)})")

        # Define generator
        if mode == "pool":
            chars = expand_pool_chars(char_pool_pattern)
            def candidate_generator():
                for total_len in range(min_length, max_length + 1):
                    middle_length = total_len - len(prefix) - len(suffix)
                    if middle_length < 0:
                        continue
                    for p in itertools.product(chars, repeat=middle_length):
                        yield prefix + "".join(p) + suffix
                        
        elif mode == "positional":
            middle_pools = parse_positional_mask(positional_pattern)
            def candidate_generator():
                for p in itertools.product(*middle_pools):
                    yield prefix + "".join(p) + suffix

        # Test each generated password by trying a trial extraction
        for password in candidate_generator():
            tested_count += 1
            if tested_count % 1000 == 0:
                print(f"[*] Tested {tested_count} candidates...", end="\r")
                
            try:
                # Try opening and reading a chunk of the encrypted target file
                with zf.open(target_info, pwd=password.encode('utf-8')) as f:
                    f.read() # Read the whole file to trigger CRC check immediately
                
                success_pw = password
                print(f"\n\n[+] SUCCESS! Verified working password after testing {tested_count} candidates: '{success_pw}'")
                break
            except (RuntimeError, BadZipFile, Exception):
                # Any decryption or CRC failure is caught here instantly, continuing the loop
                continue

except Exception as e:
    print(f"\n[!] Error opening zip archive: {e}")
    exit(1)

# Save results if found
if success_pw:
    with open(found_file, "w") as f:
        f.write(success_pw + "\n")
    print(f"[+] Password successfully written to '{found_file}'!")
    
    print(f"[*] Extracting archive...")
    with zipfile.ZipFile(zip_file) as zf:
        zf.extractall(pwd=success_pw.encode('utf-8'))
    print(f"[+] Archive extracted successfully!")
else:
    print(f"\n[-] Exhausted all candidates ({tested_count} tested). No valid password found.")

end_timestamp = time.time()
elapsed_seconds = end_timestamp - start_timestamp
print(f"\n==================================================")
print(f"[*] Total Execution Time: {elapsed_seconds:.2f} seconds")
print(f"==================================================\n")