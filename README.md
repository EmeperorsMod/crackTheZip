# ZIP Archive Password Recovery — Python Scripts

A collection of Python scripts used for **recovering passwords from password-protected / encrypted ZIP archives**.

The collection currently includes:

| Script | Approach | Main engine |
|---|---|---|
| crackV2.py | Pure Python brute-forcer (standard library) | zipfile + ProcessPoolExecutor |
| crackV3.py | Chunked dictionary brute-force | Python + fcrackzip |
| crackwork.py | Wordlist generation + fcrackzip + threaded validation | Python + fcrackzip + unzip |
| crakcV2(old).py | Legacy sequential pure-Python cracker | zipfile |
| john.py | John the Ripper wrapper | John the Ripper + zip2john + unzip |
| GeneratePass.py | Wordlist generator | Python stdlib (itertools) |
| hashcat.py | Hashcat wrapper | Hashcat + zip2john + unzip |

> **Scope:** This README documents **every Python script** in this project folder. The asset folders are **ignored** here — only the Python codes are covered.

> **Legal / ethical note:** Use these scripts only on ZIP archives you own or have explicit permission to access.

## Table of Contents

1. [crackV2.py - Pure Python Multi-Core Cracker](#1-crackv2py--pure-python-multi-core-cracker)
2. [crackV3.py - Chunked fcrackzip Dictionary Attack](#2-crackv3py--chunked-fcrackzip-dictionary-attack)
3. [crackwork.py - Wordlist + fcrackzip + Threaded Validation](#3-crackworkpy--wordlist--fcrackzip--threaded-validation)
4. [crakcV2(old).py - Legacy Sequential Cracker](#4-crackv2oldpy--legacy-sequential-cracker)
5. [john.py - John the Ripper Wrapper](#5-johnpy--john-the-ripper-wrapper)
6. [GeneratePass.py - Wordlist Generator](#6-generatepasspy--wordlist-generator)
7. [hashcat.py - Hashcat Wrapper](#7-hashcatpy--hashcat-wrapper)
8. [General Requirements](#️-general-requirements)
9. [How to Use](#-how-to-use)
10. [Known Bugs & Issues](#-known-bugs--issues)
11. [Performance: Bigger vs Smaller ZIP Files](#-performance-bigger-vs-smaller-zip-files)

## 1. crackV2.py - Pure Python Multi-Core Cracker

### Overview
Pure-Python brute-force password recovery for ZIP archives using only the Python standard library (zipfile).

- Automatically detects whether the target is a **normal archive** or a **nested ZIP** (ZIP stored inside another ZIP).
- Uses `concurrent.futures.ProcessPoolExecutor` to test candidate batches in parallel across CPU cores (half of total cores are used).
- Batches candidates for efficiency:
  - Normal archive -> batch size 15,000
  - Nested ZIP -> batch size 1,000
- Verifies a candidate by opening + reading the target (triggers CRC-32 validation).
- On success, writes the verified password to `found_passwords.txt` and extracts the target.

### Setup / Requirements
- **Python 3.9+** (Windows) with the Python launcher (`py`).
- **No third-party Python packages** needed - standard library only.

### How to Use
1. Make sure the target archive (e.g. `FA ASSET FILE_2.zip`) is in the same folder as the script, or update the `outer_zip` setting.
2. Check syntax:
   ```powershell
   py -m py_compile .\crackV2.py
   ```
3. Run:
   ```powershell
   py .\crackV2.py
   ```

### Configuration (top of file)
- `outer_zip` - path of the archive to crack.
- `inner_zip_name` - inner ZIP name; leave as `""` to auto-detect the first encrypted entry.
- `found_file` - file where the found password is written.
- `prefix` / `suffix` - literal characters around the generated middle section.
- `mode` - `"pool"` (random chars from pool) or `"positional"` (strict slot rules).
- Pool settings: `char_pool_pattern`, `min_length`, `max_length`.
- Positional settings: `positional_pattern`.

### Known Bugs & Issues
- **Critical on Windows:** no `if __name__ == "__main__":` guard while using `ProcessPoolExecutor` / `multiprocessing` -> crash or hang on Windows.
- Redundant exception tuple: `except (RuntimeError, BadZipFile, Exception):`.
- Nested-archive reopen via bare filename is fragile.

### Output
Writes the found password to `found_passwords.txt` and extracts the archive into the current working folder.

## 2. crackV3.py - Chunked fcrackzip Dictionary Attack

### Overview
Generates candidate password batches, feeds them to `fcrackzip` in dictionary mode, and extracts the archive once the password is found.

- Auto-detects chunk size from archive size:
  - < 15 MB -> 50,000 candidates per batch
  - < 50 MB -> 200,000 candidates per batch
  - >= 50 MB -> 500,000 candidates per batch
- Runs `fcrackzip -u -D -p <candidates_file> <zip>`.
- Streams progress per chunk and stops on success.

### Setup / Requirements
- Python 3 (standard library only).
- External binary: `fcrackzip`.
- External binary: `unzip` (for extraction).

### How to Use
1. Place the target ZIP (e.g. `Asset FA set 2 2026(FA2026S2).zip`) in the same folder or update `zip_file`.
2. Adjust `prefix`, mode, patterns, `min_length`, `max_length` as needed.
3. Run:
   ```powershell
   py .\crackV3.py
   ```

### Known Bugs & Issues
- Requires external binaries (`fcrackzip`, `unzip`) - not pure Python.
- Password regex may limit captured characters.

### Output
Prints found password / extracts archive; logs to console.

## 3. crackwork.py - Wordlist + fcrackzip + Threaded Validation

### Overview
Two-phase attacker:
1. Generates candidate wordlist (`candidates.txt`) or reuses it.
2. Filters candidates with `fcrackzip -u -v -D -p`.
3. Tests hits concurrently with a thread pool (`unzip -t`) and extracts on success.

### Setup / Requirements
- Python 3 (standard library only).
- External binaries: `fcrackzip`, `unzip`.

### How to Use
1. Ensure the target ZIP (e.g. `Asset FA set 2 2026(FA2026S2).zip`) is present in the working folder (or edit `zip_file`).
2. Run:
   ```powershell
   py .\crackwork.py
   ```

### Known Bugs & Issues
- If `candidates.txt` already exists, candidate generation is skipped (leftover state from previous runs).
- Uses subprocess with shell=True + password interpolation -> quoting risk.

### Output
Writes confirmed passwords to `found_passwords.txt`; extracts archive on success.

## 4. crakcV2(old).py - Legacy Sequential Cracker

### Overview
Older pure-Python cracker: generates candidates on the fly and tests them via trial decryption (`zf.open` + full read for CRC check). Sequential, single-core - no multiprocessing.

### Setup / Requirements
- Python 3 (standard library only).

### How to Use
1. Edit `zip_file`, patterns, lengths, and mode.
2. Run:
   ```powershell
   py .\crakcV2(old).py
   ```

### Known Bugs / Issues / Limitations
- No parallelism - extremely slow; legacy only.

### Output
Writes found password to `found_passwords.txt` and extracts archive.

## 5. john.py - John the Ripper Wrapper

### Overview
Wrapper around John the Ripper:
1. Extracts hash via zip2john.
2. Runs `john --mask=<mask> <hash>`.
3. Streams John live output, checks result via `john --show`.
4. Extracts archive via `unzip -o -P <pw>`.

### Setup / Requirements
- WSL (Ubuntu) with John the Ripper installed (e.g. at `/home/mjar/john/run/john`) plus zip2john.
- `unzip` available.
- Python 3 (standard library only).

### How to Use
1. Edit `zip_file`, `john_bin`, `zip2john_bin`, and `hash_file` (WSL paths!).
2. Adjust mode / patterns / lengths.
3. Run:
   ```powershell
   py .\john.py
   ```

### Known Bugs & Issues
- Hardcoded WSL paths: `john_bin = "/home/mjar/john/run/john"` and `zip2john_bin = "/home/mjar/john/run/zip2john"` - must point to your actual John installation; will not run as-is on plain Windows.

### Output
Prints confirmed password / extracts archive.

## 6. GeneratePass.py - Wordlist Generator

### Overview
Generates a small wordlist (`candidates.txt`) of uppercase 4-character passwords suffixed with `2026`.

### Setup / Requirements
- Python 3 (standard library only).

### How to Use
```powershell
py .\GeneratePass.py
```

### Known Bugs & Issues
- Writes file with default locale encoding instead of explicit UTF-8.

### Output
Creates `candidates.txt` with generated candidates (e.g. `ABCD2026`).

## 7. hashcat.py - Hashcat Wrapper

### Overview
Wrapper around Hashcat:
1. Extracts + sanitizes the hash via zip2john.
2. Detects hash type: `$pkzip$` -> Hashcat mode 17200, otherwise -> mode 13600 (WinZip AES).
3. Runs Hashcat (`-m <mode> -a 3 --potfile-disable --status`), checks via `hashcat --show`.
4. Extracts archive via `unzip -o -P <pw>`.

### Setup / Requirements
- Hashcat installed (Windows exe reachable via WSL interop at `/mnt/c/Users/HP/Documents/script/hashcat.exe` - adjust `script_dir` / `hashcat_bin` as needed).
- zip2john (e.g. `/home/mjar/john/run/zip2john`).
- `unzip` available.
- GPU recommended for practical performance.

### How to Use
1. Edit `script_dir`, `hashcat_bin`, `zip2john_bin`, `zip_file`, mode / patterns / lengths / custom pool.
2. Run:
   ```powershell
   py .\hashcat.py
   ```

### Known Bugs & Issues
- Mixed WSL / Windows paths: Hashcat exe referenced via WSL interop path (`/mnt/c/Users/HP/Documents/script/...`) while other tools use WSL user paths (`/home/mjar/...`).

### Output
Prints confirmed password / extracts archive.

## General Requirements (all scripts)

- **Python 3.9+** via the Python launcher:
  ```powershell
  py --version
  ```
- No pip install step is needed for any script (standard library only), except that some scripts shell out to external tools (see table below).

| Script(s) | External binaries required |
|---|---|
| crackV2.py, crakcV2(old).py, GeneratePass.py | None (pure Python) |
| crackV3.py, crackwork.py | fcrackzip, unzip |
| john.py | WSL + John the Ripper + zip2john + unzip |
| hashcat.py | WSL + Hashcat + zip2john + unzip (+ GPU for speed) |

## How to Use

Generic flow for the pure-Python / generator scripts:

```powershell
# 1. Open PowerShell in this folder
cd "C:\Users\HP\Documents\asignment or exercise\SEM 3"

# 2. Syntax-check the script before running
py -m py_compile .\crackV2.py

# 3. Run the cracker
py .\crackV2.py
```

For wrapper scripts (john.py, hashcat.py, crackV3.py, crackwork.py), make sure the referenced external binaries exist and that the paths configured inside the script match your installation.

## Known Bugs & Issues

### crackV2.py
- Critical on Windows: no if __name__ == "__main__": guard while using ProcessPoolExecutor / multiprocessing -> crash or hang on Windows.
- Redundant exception tuple: except (RuntimeError, BadZipFile, Exception):.

### crackV3.py
- Requires external fcrackzip / unzip binaries.

### crackwork.py
- Skips candidate generation if candidates.txt already exists.

### crakcV2(old).py
- Sequential / single-core -> very slow; legacy only.

### john.py
- Hardcoded WSL paths (/home/mjar/john/run/...).

### hashcat.py
- Mixed WSL / Windows paths.

### GeneratePass.py
- Writes file with default locale encoding instead of explicit UTF-8.

> **Good news:** as of the current versions, all seven Python scripts pass Python syntax compilation - the previously reported malformed expressions / syntax errors in the crackers are resolved.

## Performance: Bigger vs Smaller ZIP Files - Which Is Faster?

**Short answer:** For a **smaller ZIP file**, cracking is faster - each candidate must decrypt + CRC-32 check a smaller payload, so verification is quicker. For a **bigger ZIP file**, per-candidate verification gets slower, and faster engines (Hashcat GPU / John the Ripper / fcrackzip) become important.

### How ZIP size affects speed
- Every password test must decrypt the payload and run the CRC-32 check.
- Smaller ZIP -> faster per-candidate testing (less data to process per attempt).
- Bigger ZIP -> slower per-candidate testing (more data per verification).

### Engine speed comparison (same search space)
1. Hashcat (GPU) - via hashcat.py - fastest for large search spaces; recommended for bigger ZIP files with larger password pools.
2. John the Ripper - via john.py - strong CPU performer for medium-sized spaces.
3. fcrackzip - via crackV3.py / crackwork.py - C engine, far faster than pure Python; good for medium spaces.
4. Pure Python - via crackV2.py (multicore) / crakcV2(old).py (sequential) - slowest per candidate; crackV2.py is faster than the legacy crakcV2(old).py.

### Practical verdict
- Smaller ZIP files / small search spaces: pure-Python scripts are sufficient and simplest (crackV2.py is the fastest pure-Python option thanks to the process pool; crakcV2(old).py is only OK for very small spaces).
- Bigger ZIP files / bigger search spaces: move to hashcat.py (GPU - fastest), john.py, or crackV3.py / crackwork.py (fcrackzip).
- crackV3.py automatically sizes its candidate batch by archive size (< 15 MB -> 50,000 candidates; < 50 MB -> 200,000; >= 50 MB -> 500,000), so bigger archives automatically get bigger batches.

## Runtime Notes

- Runtime depends heavily on the search settings (charset + password length) and the archive size.
- Stop long runs with Ctrl+C.
- Make a backup of important files before extraction; run only on archives you trust.

---

*This README covers all Python scripts in this project folder (asset folders ignored).*
#   c r a c k T h e Z i p  
 