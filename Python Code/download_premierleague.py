"""
Download all English Premier League data files listed in PremierLeague.txt.
Run from the Final Project folder:  python download_premierleague.py
Files are saved into a ./premierleague_data subfolder.
"""
import os
import re
import urllib.request

# Anchor paths to this script's folder, so it works no matter where it's run from.
BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "PremierLeague.txt")
OUT = os.path.join(BASE, "premierleague_data")

os.makedirs(OUT, exist_ok=True)

with open(SRC, encoding="utf-8") as f:
    urls = sorted(set(re.findall(r"https://\S+", f.read())))

print(f"Found {len(urls)} URLs\n")

ok, fail = 0, 0
for url in urls:
    name = url.split("/")[-1]
    dest = os.path.join(OUT, name)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as r, open(dest, "wb") as out:
            out.write(r.read())
        print(f"OK    {name}")
        ok += 1
    except Exception as e:
        print(f"FAIL  {name}  ({e})")
        fail += 1

print(f"\nDone: {ok} downloaded, {fail} failed -> {OUT}/")
