import subprocess
import os
import re
import itertools
import time
from datetime import datetime
import concurrent.futures
import string

# Define Hashcat-style shorthand expansion
def expand_pool_chars(token_string):
    mappings = {
        "?l": string.ascii_lowercase,                    # a-z
        "?u": string.ascii_uppercase,                    # A-Z
        "?w": string.ascii_lowercase + string.ascii_uppercase, # aA-zZ
        "?d": string.digits,                             # 0-9
        "?1": string.digits,                             # Alias for numbers
        "?s": string.punctuation + " ",                  # Symbols & space
        "?a": string.ascii_letters + string.digits + string.punctuation + " "  # All printable ASCII
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

zip_file = "Asset FA set 2 2026(FA2026S2).zip"
candidates_file = "candidates.txt"
found_file = "found_passwords.txt"
prefix = "FA"
suffix = ""

# Choose your mode: "pool" (random from set) OR "positional" (exact slot rules)
mode = "pool"  # Change to "positional" if you want to use a strict mask like "?l?a?d"

# --- SETTINGS FOR "pool" MODE ---
char_pool_pattern = "?u206"  # e.g., "?l?d", "abcdefghijklmnopqrstuvwxyz1234567890", etc.
min_length = 8
max_length = 8

# --- SETTINGS FOR "positional" MODE ---
positional_pattern = "?d?d?d?d?u?d"  # Exact positional rules for the middle section

if not os.path.exists(zip_file):
    print(f"[!] Error: {zip_file} missing!")
    exit(1)

# Record start time
start_timestamp = time.time()
start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"==================================================")
print(f"[*] Execution Started at: {start_time_str}")
print(f"[*] Active Mode: {mode.upper()}")
print(f"==================================================\n")

if not os.path.exists(candidates_file):
    print("[*] Generating temporary candidates list...")
    with open(candidates_file, "w", encoding="utf-8") as f:
        if mode == "pool":
            chars = expand_pool_chars(char_pool_pattern)
            for total_len in range(min_length, max_length + 1):
                middle_length = total_len - len(prefix) - len(suffix)
                if middle_length < 0:
                    continue
                for p in itertools.product(chars, repeat=middle_length):
                    password = prefix + "".join(p) + suffix + "\n"
                    f.write(password)
                    print("Write: " + password)
                    
        elif mode == "positional":
            middle_pools = parse_positional_mask(positional_pattern)
            for p in itertools.product(*middle_pools):
                middle_str = "".join(p)
                password = prefix + middle_str + suffix + "\n"
                f.write(password)
                print("Write: " + password)
else :
    print ("[*] candidates file exist skiping password generator")


print("\n[*] Step 1: Filtering candidates using fcrackzip...")
cmd_fcrack = ["fcrackzip", "-u", "-v", "-D", "-p", candidates_file, zip_file]

found_passwords = []
process = subprocess.Popen(cmd_fcrack, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

for line in process.stdout:
    print(line, end="")
    if "possible pw found:" in line:
        match = re.search(r'possible pw found:\s*([A-Za-z0-9@]+)', line)
        if match:
            pw = match.group(1)
            if pw not in found_passwords:
                found_passwords.append(pw)

process.wait()

# Immediately delete candidates.txt to save disk space
if os.path.exists(candidates_file):
    os.remove(candidates_file)
    print("\n[+] Temporary candidates.txt deleted successfully (zero disk clutter!).")

# Save filtered passwords to found_passwords.txt
if found_passwords:
    with open(found_file, "w") as f:
        for pw in found_passwords:
            f.write(pw + "\n")
    print(f"[+] Filtered password(s) written to '{found_file}'!")
else:
    print("\n[-] No password found by fcrackzip.")
    exit(1)

print(f"\n[*] Step 2: Testing passwords in background threads concurrently...")

with open(found_file, "r") as f:
    passwords_to_try = [line.strip() for line in f if line.strip()]

success_pw = None

# Worker function to test and extract in the background
def test_password(pw):
    # Test integrity (-t) silently
    test_cmd = f'unzip -o -P "{pw}" -t "{zip_file}" >/dev/null 2>&1'
    res = subprocess.run(test_cmd, shell=True)
    if res.returncode == 0:
        # If valid, extract immediately
        extract_cmd = f'unzip -o -P "{pw}" "{zip_file}" >/dev/null 2>&1'
        subprocess.run(extract_cmd, shell=True)
        return pw
    return None

# Run background threads (max_workers=4 runs 4 unzip tests simultaneously)
total = len(passwords_to_try)
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    future_to_pw = {executor.submit(test_password, pw): pw for pw in passwords_to_try}
    
    for i, future in enumerate(concurrent.futures.as_completed(future_to_pw), 1):
        pw = future_to_pw[future]
        print(f"[*] Background job [{i}/{total}] tested password: '{pw}'")
        try:
            result = future.result()
            if result:
                success_pw = result
                print(f"\n[+] SUCCESS! Valid working password confirmed: '{result}'")
                # Cancel remaining pending tasks once the correct password is found
                for f in future_to_pw:
                    f.cancel()
                break
        except Exception as exc:
            print(f"[-] Error testing {pw}: {exc}")

if success_pw:
    print(f"\n[+] Archive extracted successfully using background concurrency!")
else:
    print("\n[-] Extraction failed across all candidate passwords.")

# Record end time and calculate elapsed duration
end_timestamp = time.time()
end_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
elapsed_seconds = end_timestamp - start_timestamp

print(f"\n==================================================")
print(f"[*] Execution Finished at: {end_time_str}")
print(f"[*] Total Execution Time: {elapsed_seconds:.2f} seconds")
print(f"==================================================\n")