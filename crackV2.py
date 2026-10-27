import itertools
import os
import time
import zipfile
from zipfile import BadZipFile
from datetime import datetime
import string
import concurrent.futures
import multiprocessing
import sys
from io import BytesIO

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

def test_normal_batch(zip_path, target_filename, passwords):
    """Worker for normal archives with full CRC-32 validation."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            target_info = zf.getinfo(target_filename)
            for pwd in passwords:
                for enc in ('utf-8', 'cp437', 'latin-1'):
                    try:
                        pwd_bytes = pwd.encode(enc)
                        with zf.open(target_info, pwd=pwd_bytes) as f:
                            while f.read(1024 * 64):
                                pass
                        return pwd
                    except (RuntimeError, BadZipFile, Exception):
                        continue
    except Exception:
        pass
    return None

def test_nested_batch(outer_zip_path, inner_zip_name, passwords):
    """Worker for nested archives (zip inside zip) with full CRC-32 validation."""
    try:
        with zipfile.ZipFile(outer_zip_path) as outer_zf:
            for pwd in passwords:
                for enc in ('utf-8', 'cp437', 'latin-1'):
                    try:
                        pwd_bytes = pwd.encode(enc)
                        with outer_zf.open(inner_zip_name, pwd=pwd_bytes) as inner_stream:
                            inner_data = BytesIO(inner_stream.read())
                            with zipfile.ZipFile(inner_data) as inner_zf:
                                target_info = inner_zf.infolist()[0]
                                with inner_zf.open(target_info, pwd=pwd_bytes) as f:
                                    while f.read(1024 * 64):
                                        pass
                        return pwd
                    except (RuntimeError, BadZipFile, Exception):
                        continue
    except Exception:
        pass
    return None

def batch_generator(iterable, batch_size):
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch

# ================= CONFIGURATION =================
outer_zip = "FA ASSET FILE_2.zip"
inner_zip_name = ""  # Leave blank ("") to auto-detect target inside outer zip
found_file = "found_passwords.txt"
prefix = "FA"
suffix = ""

# Select Mode: "pool" or "positional"
mode = "pool"

# --- SETTINGS FOR "pool" MODE ---
char_pool_pattern = "206?u"
min_length = 8
max_length = 8

# --- SETTINGS FOR "positional" MODE ---
positional_pattern = "?d?d?d?d?u?d"
# =================================================

if not os.path.exists(outer_zip):
    print(f"[!] Error: {outer_zip} missing!", flush=True)
    exit(1)

start_timestamp = time.time()
start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"==================================================", flush=True)
print(f"[*] Execution Started at: {start_time_str}", flush=True)
print(f"[*] Active Mode: {mode.upper()} (Pure Python Multi-Core Cracker)", flush=True)
print(f"==================================================\n", flush=True)

success_pw = None
total_cpus = multiprocessing.cpu_count()
cpu_count = max(1, total_cpus // 2)
print(f"[*] System total cores: {total_cpus} | Utilizing half: {cpu_count} CPU cores...", flush=True)

try:
    with zipfile.ZipFile(outer_zip) as zf:
        infolist = zf.infolist()
        if not infolist:
            raise Exception(f"Archive '{outer_zip}' is completely empty!")
            
        if not inner_zip_name:
            encrypted_files = [f for f in infolist if f.flag_bits & 0x1]
            if encrypted_files:
                inner_zip_name = encrypted_files[0].filename
            else:
                inner_zip_name = infolist[0].filename

    is_nested_zip = inner_zip_name.lower().endswith('.zip')
    
    if is_nested_zip:
        print(f"[*] Structure detected: NESTED ZIP ('{inner_zip_name}') -> Line-by-line mode (Batch size: 1,000).", flush=True)
        batch_size = 1000
    else:
        print(f"[*] Structure detected: NORMAL ARCHIVE ('{inner_zip_name}') -> Smooth single-line mode (Batch size: 15,000).", flush=True)
        batch_size = 15000

    if mode == "pool":
        chars = expand_pool_chars(char_pool_pattern)
        total_candidates = 0
        for total_len in range(min_length, max_length + 1):
            middle_len = total_len - len(prefix) - len(suffix)
            if middle_len >= 0:
                total_candidates += len(chars) ** middle_len
                
        def candidate_stream():
            for total_len in range(min_length, max_length + 1):
                middle_len = total_len - len(prefix) - len(suffix)
                if middle_len < 0:
                    continue
                for p in itertools.product(chars, repeat=middle_len):
                    yield prefix + "".join(p) + suffix
                    
    elif mode == "positional":
        middle_pools = parse_positional_mask(positional_pattern)
        total_candidates = 1
        for pool in middle_pools:
            total_candidates *= len(pool)
            
        def candidate_stream():
            for p in itertools.product(*middle_pools):
                yield prefix + "".join(p) + suffix

    print(f"[*] Total search space: {total_candidates:,} candidates.", flush=True)
    print(f"[*] Launching worker pool with active feedback...\n", flush=True)

    total_tested = 0
    last_print_time = 0
    print_interval = 0.05

    with concurrent.futures.ProcessPoolExecutor(max_workers=cpu_count) as executor:
        futures = {}
        batch_iter = batch_generator(candidate_stream(), batch_size=batch_size)
        
        initial_queue_size = cpu_count
        for _ in range(initial_queue_size):
            try:
                batch = next(batch_iter)
                if is_nested_zip:
                    f = executor.submit(test_nested_batch, outer_zip, inner_zip_name, batch)
                else:
                    f = executor.submit(test_normal_batch, outer_zip, inner_zip_name, batch)
                futures[f] = batch
            except StopIteration:
                break

        while futures:
            done, _ = concurrent.futures.wait(
                futures.keys(), 
                return_when=concurrent.futures.FIRST_COMPLETED
            )
            
            for future in done:
                batch = futures.pop(future)
                if batch:
                    total_tested += len(batch)
                    current_pw = batch[-1]
                    percent = (total_tested / total_candidates) * 100 if total_candidates > 0 else 0
                    
                    if is_nested_zip:
                        print(f"[*] Progress: {percent:6.2f}% | Tested: {total_tested:,} / {total_candidates:,} | Current: {current_pw}", flush=True)
                    else:
                        now = time.time()
                        if now - last_print_time >= print_interval:
                            print(f"[*] Progress: {percent:.2f}% | Tested: {total_tested:,} | Current: {current_pw}    ", end="\r", flush=True)
                            last_print_time = now
                
                try:
                    result = future.result()
                    if result:
                        success_pw = result
                        print(f"\n\n[+] SUCCESS! Verified working password found: '{success_pw}'", flush=True)
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                except Exception:
                    pass
                
                try:
                    batch = next(batch_iter)
                    if is_nested_zip:
                        f = executor.submit(test_nested_batch, outer_zip, inner_zip_name, batch)
                    else:
                        f = executor.submit(test_normal_batch, outer_zip, inner_zip_name, batch)
                    futures[f] = batch
                except StopIteration:
                    pass
                    
            if success_pw:
                break

except KeyboardInterrupt:
    print("\n\n[!] Interrupted by user (Ctrl+C). Exiting cleanly...", flush=True)
    sys.exit(0)
except Exception as e:
    print(f"\n[!] Error during execution: {e}", flush=True)
    exit(1)

# Save results and robustly unpack files
if success_pw:
    with open(found_file, "w") as f:
        f.write(success_pw + "\n")
    print(f"[+] Password successfully written to '{found_file}'!", flush=True)
    
    if is_nested_zip:
        print(f"[*] Extracting inner zip file '{inner_zip_name}' from outer container...", flush=True)
        with zipfile.ZipFile(outer_zip) as zf:
            zf.extract(inner_zip_name, pwd=success_pw.encode('utf-8'))
        
        print(f"[*] Unpacking contents of '{inner_zip_name}' into working directory...", flush=True)
        with zipfile.ZipFile(inner_zip_name) as inner_zf:
            try:
                inner_zf.extractall(pwd=success_pw.encode('utf-8'))
            except Exception:
                inner_zf.extractall()
        print(f"[+] All files inside '{inner_zip_name}' have been successfully unpacked!", flush=True)
    else:
        print(f"[*] Extracting target file...", flush=True)
        with zipfile.ZipFile(outer_zip) as zf:
            zf.extract(inner_zip_name, pwd=success_pw.encode('utf-8'))
        print(f"[+] '{inner_zip_name}' extracted successfully!", flush=True)
else:
    print(f"\n[-] Exhausted all candidates. No valid password found.", flush=True)

end_timestamp = time.time()
elapsed_seconds = end_timestamp - start_timestamp
print(f"\n==================================================", flush=True)
print(f"[*] Total Execution Time: {elapsed_seconds:.2f} seconds", flush=True)
print(f"==================================================\n", flush=True)