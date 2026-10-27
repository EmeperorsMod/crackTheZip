import subprocess
import os
import re
import itertools
import time
from datetime import datetime
import string

# Define Hashcat-style shorthand expansion
def expand_pool_chars(token_string):
    mappings = {
        "?l": string.ascii_lowercase,                        # a-z
        "?u": string.ascii_uppercase,                        # A-Z
        "?w": string.ascii_lowercase + string.ascii_uppercase, # aA-zZ
        "?d": string.digits,                                 # 0-9
        "?1": string.digits,                                 # Alias for numbers
        "?s": string.punctuation + " ",                      # Symbols & space
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

# --- CONFIGURATION ---
zip_file = "Asset FA set 2 2026(FA2026S2).zip"

candidates_file = "chunk_candidates.txt"

prefix = "FA"

suffix = ""



# Choose your mode: "pool" OR "positional"

mode = "pool"



# --- SETTINGS FOR "pool" MODE ---

char_pool_pattern = "?u?d"

min_length = 8

max_length = 8

# --- SETTINGS FOR "positional" MODE ---
positional_pattern = "?d?d?d?d?u?d" 

if not os.path.exists(zip_file):
    print(f"[!] Error: {zip_file} missing!")
    exit(1)

# --- AUTO-DETECT CHUNK SIZE BASED ON FILE SIZE ---
file_size_bytes = os.path.getsize(zip_file)
file_size_mb = file_size_bytes / (1024 * 1024)

if file_size_mb < 15:
    CHUNK_SIZE = 50000
elif file_size_mb < 50:
    CHUNK_SIZE = 200000
else:
    CHUNK_SIZE = 500000

# Record start time
start_timestamp = time.time()
print(f"==================================================")
print(f"[*] Execution Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"[*] Target Archive: {zip_file} ({file_size_mb:.2f} MB)")
print(f"[*] Auto-Detected Chunk Size: {CHUNK_SIZE} candidates/batch")
print(f"[*] Active Mode: {mode.upper()}")
print(f"==================================================\n")

# Build the complete iterable generator based on mode
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

def batch_generator(iterable, size):
    iterator = iter(iterable)
    while True:
        batch = list(itertools.islice(iterator, size))
        if not batch:
            break
        yield batch

chunk_count = 0
total_tested = 0
success_pw = None

print("[*] Starting chunked generation & fcrackzip loop...\n")

for chunk in batch_generator(candidate_generator(), CHUNK_SIZE):
    chunk_count += 1
    current_chunk_size = len(chunk)
    
    # Single-line updating status display using \r
    elapsed = time.time() - start_timestamp
    speed = total_tested / elapsed if elapsed > 0 else 0
    print(f"\r[*] [Chunk #{chunk_count}] Tested: {total_tested:,} candidates | Speed: {speed:.0f} c/s", end="", flush=True)
    
    # Write chunk to file for fcrackzip dictionary mode
    with open(candidates_file, "w", encoding="utf-8") as f:
        f.writelines(pw + "\n" for pw in chunk)
        
    # Run fcrackzip in dictionary mode (-D) with unzip validation (-u)
    cmd_fcrack = ["fcrackzip", "-u", "-D", "-p", candidates_file, zip_file]
    process = subprocess.Popen(cmd_fcrack, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    for line in process.stdout:
        if "PASSWORD FOUND" in line or "possible pw found" in line:
            print() # Clear the current status line before printing the match
            print(line, end="")
            match = re.search(r'(?:PASSWORD FOUND!!!!:\s*pw\s*==|possible pw found:)\s*([A-Za-z0-9@!]+)', line)
            if match:
                success_pw = match.group(1).strip()

    process.wait()
    
    total_tested += current_chunk_size
    
    if os.path.exists(candidates_file):
        os.remove(candidates_file)
        
    if success_pw:
        print(f"\n[+] SUCCESS! Valid working password confirmed: '{success_pw}'")
        break

# Clean up just in case
if os.path.exists(candidates_file):
    os.remove(candidates_file)

if success_pw:
    print(f"\n[*] Extracting archive using confirmed password...")
    extract_cmd = f'unzip -o -P "{success_pw}" "{zip_file}"'
    subprocess.run(extract_cmd, shell=True)
    print(f"[+] Archive extracted successfully!")
else:
    print(f"\n\n[-] No password found across all evaluated chunks (Total checked: {total_tested:,}).")

# Record end time and calculate elapsed duration
end_timestamp = time.time()
print(f"\n==================================================")
print(f"[*] Total Execution Time: {end_timestamp - start_timestamp:.2f} seconds")
print(f"==================================================\n")