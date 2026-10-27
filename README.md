# crackTheZip

Experimental Python scripts for recovering access to ZIP archives when the owner has forgotten a password.

> **Use responsibly:** Only use this project with archives you own or are explicitly authorized to access. Do not use it to bypass access controls on someone else's data. You are responsible for complying with applicable laws and permissions.

## What is in this repository?

The repository contains several independent scripts exploring different archive-recovery approaches. They are experiments rather than a unified command-line application.

| File | Description |
|---|---|
| `crackV2.py` | Multiprocess, standard-library ZIP password recovery experiment. |
| `crackV3.py` | Candidate-list workflow that integrates with `fcrackzip`. |
| `crackwork.py` | Candidate generation and validation workflow using external archive tools. |
| `crakcV2(old).py` | Older, sequential standard-library implementation. |
| `john.py` | Wrapper for John the Ripper and related ZIP utilities. |
| `hashcat.py` | Wrapper for Hashcat and related ZIP utilities. |
| `GeneratePass.py` | Small, fixed-format candidate-list generator. |

## Project status

This is a personal, experimental code collection, not a maintained product. Scripts have separate configuration and dependencies, and some contain machine-specific paths or platform assumptions. They may need adaptation and careful review before they can run in another environment. No compatibility, performance, or recovery guarantee is made.

In particular, multiprocessing behavior can vary by operating system, and the external-tool wrappers depend on local installations and paths. Review each script before use; do not assume that one script's setup or behavior applies to the others.

## Requirements

- Python 3 for the Python scripts.
- Some scripts depend on separately installed tools such as `fcrackzip`, `unzip`, John the Ripper, `zip2john`, or Hashcat.
- External-tool requirements and platform-specific assumptions vary by script.

There are no shared package-management or test instructions in this repository. Check the relevant script and the official documentation for any external dependency before running it.

## Safety and data handling

- Work only with archives for which you have authorization.
- Keep an untouched backup of important archives and extracted data.
- Treat archives and extracted contents as untrusted input.
- Review a script's settings, subprocess calls, output paths, and extraction behavior before running it.
- Avoid placing sensitive archives, passwords, or generated candidate files in a public repository.

## Contributions

Improvements are welcome. Please keep changes focused, document platform and dependency requirements, and avoid committing archives, generated candidate lists, recovered passwords, or other sensitive data.
