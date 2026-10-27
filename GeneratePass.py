
import itertools
chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
with open("candidates.txt", "w") as f:
    for p in itertools.product(chars, repeat=4):
        f.write("" + "".join(p) + "2026\n")
print("[+] Uppercase wordlist generated successfully!")