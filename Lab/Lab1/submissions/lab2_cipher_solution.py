from pathlib import Path
import random
import string
import re
from collections import Counter

# Lab 2 solution for Household Carbon Footprint & Target Tracker
# The script keeps punctuation, spaces, and line breaks unchanged.
ROOT = Path(__file__).parent
INPUT = ROOT / "SRN.txt"

def generate_key(seed=20260825):
    plain = list(string.ascii_lowercase)
    cipher = plain.copy()
    random.Random(seed).shuffle(cipher)
    return dict(zip(plain, cipher))

def transform(text, mapping):
    out=[]
    for ch in text:
        low=ch.lower()
        if low in mapping:
            value=mapping[low]
            out.append(value.upper() if ch.isupper() else value)
        else:
            out.append(ch)
    return ''.join(out)

def overlapping_frequency(text, pattern):
    return len(re.findall(r"(?=" + re.escape(pattern) + r")", text))

plaintext = INPUT.read_text(encoding="utf-8").lower()
key = generate_key()
reverse = {v:k for k,v in key.items()}
print("Key mapping (plaintext -> ciphertext):")
print(", ".join(f"{a} -> {key[a]}" for a in string.ascii_lowercase))
print("\nFrequencies:")
for item in ["th", "he", "ar", "ing", "e", "or"]:
    print(f"{item}: {overlapping_frequency(plaintext, item)}")

ciphertext = transform(plaintext, key)
(INPUT.parent / "SRN_ciphertext_student.txt").write_text(ciphertext, encoding="utf-8")
recovered = transform(ciphertext, reverse)
(INPUT.parent / "SRN_decrypted_student.txt").write_text(recovered, encoding="utf-8")
print("\nCiphertext and decrypted files written.")
