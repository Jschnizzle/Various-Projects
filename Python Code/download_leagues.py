"""
Download the domestic-league datasets listed in the datahub URL text files
(French Ligue 1, Spanish La Liga, German Bundesliga).

Run from the Final Project folder:  python download_leagues.py
Each league's files are saved into its own subfolder, e.g. FrenchLigue1.txt -> ./frenchligue1_data
(same convention as PremierLeague.txt -> ./premierleague_data).

To add another league, just drop its datahub URL list in this folder and add
the file name to LEAGUES below.
"""
import os
import re
import urllib.request

# Anchor paths to this script's folder, so it works no matter where it's run from.
BASE = os.path.dirname(os.path.abspath(__file__))

# League URL-list text files to process. (PremierLeague.txt is already downloaded;
# add it here to refresh it too.)
LEAGUES = [
    "FrenchLigue1.txt",
    "SpanishLaLiga.txt",
    "GermanBundesliga.txt",
]


def out_folder(src_name):
    """FrenchLigue1.txt -> frenchligue1_data  (matches premierleague_data)."""
    stem = os.path.splitext(src_name)[0]
    return os.path.join(BASE, stem.lower() + "_data")


def download_league(src_name):
    src = os.path.join(BASE, src_name)
    if not os.path.exists(src):
        print(f"SKIP  {src_name}  (file not found)")
        return 0, 0

    out = out_folder(src_name)
    os.makedirs(out, exist_ok=True)

    with open(src, encoding="utf-8") as f:
        urls = sorted(set(re.findall(r"https://\S+", f.read())))

    print(f"\n=== {src_name} -> {os.path.basename(out)}/  ({len(urls)} URLs) ===")

    ok, fail = 0, 0
    for url in urls:
        name = url.split("/")[-1]
        dest = os.path.join(out, name)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as r, open(dest, "wb") as f_out:
                f_out.write(r.read())
            print(f"OK    {name}")
            ok += 1
        except Exception as e:
            print(f"FAIL  {name}  ({e})")
            fail += 1

    print(f"--- {src_name}: {ok} downloaded, {fail} failed -> {out}/")
    return ok, fail


if __name__ == "__main__":
    total_ok, total_fail = 0, 0
    for league in LEAGUES:
        ok, fail = download_league(league)
        total_ok += ok
        total_fail += fail

    print(f"\nAll done: {total_ok} downloaded, {total_fail} failed "
          f"across {len(LEAGUES)} league(s).")
