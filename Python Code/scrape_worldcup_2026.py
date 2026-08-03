#!/usr/bin/env python3
# =============================================================================
# scrape_worldcup_2026.py
# -----------------------------------------------------------------------------
# Builds `mens_groupstage_2026.csv` -- the 2026 World Cup group-stage table in
# the same shape as `mens_groupstage_1970on.csv`, so it can be fed straight into
# the section-8b forward-benchmark scaffold in `logit_mens_groupstage_advance.R`.
#
# It scrapes the twelve Wikipedia group pages (Group A ... Group L) with
# pandas.read_html -- which reads the real team names out of the HTML, unlike a
# plain-text fetch, where Wikipedia's flag-icon templates hide the names.
#
# WHAT IT PRODUCES, per team (one row each, 48 rows):
#   team_name, group_name, position, played, wins, draws, losses,
#   goals_for, goals_against, goal_difference, points_raw, points_std,
#   advanced, confederation_code, conf, is_host, year, year_c, prior_tournaments
#
# The five SQUAD-BASED predictors in the model's `f_structural`
# (avg_prior_wc, avg_age, forward_share, defender_share, foreign_manager) are
# written as empty/NA -- they need the 2026 rosters, which live on separate
# pages. See the SQUAD PREDICTORS hook at the bottom for how to add them.
#
# The SIGNIFICANT predictors from the logistic analysis -- is_host,
# prior_tournaments, and confederation -- ARE fully populated, along with the
# `advanced` outcome, so the model's headline terms can be scored immediately.
#
# Requires: pandas, lxml (or html5lib), requests.  Run from the project root so
# `worldcup_data/group_standings.csv` resolves for the prior_tournaments count.
#     python scrape_worldcup_2026.py
# =============================================================================

import re
import sys
import collections
import pandas as pd
import requests

YEAR = 2026
WIKI = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_Group_{}"
GROUPS = list("ABCDEFGHIJKL")
HEADERS = {"User-Agent": "Mozilla/5.0 (STAT418 research; contact jeremyshiu428@gmail.com)"}

# ---- Static, verified metadata (does not change once the field is set) -------
# Host nations (auto-qualified) get is_host = 1.
HOSTS = {"Canada", "Mexico", "United States"}

# Confederation of each of the 48 finalists. This is fixed membership, not a
# scraped result, so it is encoded here as the source of truth for `conf`.
CONFED = {
    "AFC": ["Australia", "Iran", "Iraq", "Japan", "Jordan", "Qatar",
            "Saudi Arabia", "South Korea", "Uzbekistan"],
    "CAF": ["Algeria", "Cape Verde", "DR Congo", "Egypt", "Ghana", "Ivory Coast",
            "Morocco", "Senegal", "South Africa", "Tunisia"],
    "CONCACAF": ["Canada", "Curacao", "Haiti", "Mexico", "Panama", "United States"],
    "CONMEBOL": ["Argentina", "Brazil", "Colombia", "Ecuador", "Paraguay", "Uruguay"],
    "OFC": ["New Zealand"],
    "UEFA": ["Austria", "Belgium", "Bosnia and Herzegovina", "Croatia",
             "Czech Republic", "England", "France", "Germany", "Netherlands",
             "Norway", "Portugal", "Scotland", "Spain", "Sweden", "Switzerland",
             "Turkey"],
}
CONF_OF = {team: conf for conf, teams in CONFED.items() for team in teams}

# Normalise the many spellings Wikipedia may use into our canonical names above.
NORMALISE = {
    "Korea Republic": "South Korea", "South Korea": "South Korea",
    "IR Iran": "Iran", "Iran": "Iran",
    "Türkiye": "Turkey", "Turkiye": "Turkey", "Turkey": "Turkey",
    "Czechia": "Czech Republic", "Czech Republic": "Czech Republic",
    "Côte d'Ivoire": "Ivory Coast", "Cote d'Ivoire": "Ivory Coast",
    "Ivory Coast": "Ivory Coast",
    "United States": "United States", "USA": "United States",
    "DR Congo": "DR Congo", "Congo DR": "DR Congo",
    "Curaçao": "Curacao", "Curacao": "Curacao",
    "Cape Verde": "Cape Verde", "Cabo Verde": "Cape Verde",
    "Bosnia and Herzegovina": "Bosnia and Herzegovina",
}


def clean_team(raw: str) -> str:
    """Strip host marker, footnote letters, and reference brackets, then map to
    a canonical team name."""
    s = re.sub(r"\[[^\]]*\]", "", str(raw))         # drop [1], [a] references
    s = re.sub(r"\((?:H|A|B|C|D)\)", "", s)          # drop "(H)" host / seeding tags
    s = s.strip().strip("†*").strip()
    # remove a trailing single-letter footnote glued to the name, e.g. "IranE"
    s = re.sub(r"([a-z])[A-Z]$", r"\1", s)
    return NORMALISE.get(s, s)


# =============================================================================
# 1. SCRAPE THE TWELVE GROUP STANDINGS
# =============================================================================
def scrape_group(letter: str) -> pd.DataFrame:
    url = WIKI.format(letter)
    html = requests.get(url, headers=HEADERS, timeout=30).text
    tables = pd.read_html(html)
    # The standings table is the one carrying both 'Pld' and 'Pts' columns.
    for t in tables:
        cols = [str(c) for c in t.columns]
        if any("Pld" in c for c in cols) and any("Pts" in c for c in cols):
            t = t.rename(columns={c: str(c) for c in t.columns})
            keep = {}
            for c in t.columns:
                cs = str(c)
                for want in ["Pos", "Team", "Pld", "W", "D", "L", "GF", "GA", "GD", "Pts"]:
                    if cs == want or cs.endswith(want):
                        keep[c] = want
            t = t[list(keep)].rename(columns=keep)
            t["group_name"] = letter
            t["Team"] = t["Team"].map(clean_team)
            return t
    raise RuntimeError(f"No standings table found for Group {letter} ({url})")


def determine_advancement(df: pd.DataFrame) -> pd.Series:
    """Top 2 of every group advance; then the 8 best third-placed teams by
    (points, goal difference, goals for)."""
    adv = pd.Series(0, index=df.index)
    adv[df["Pos"] <= 2] = 1
    thirds = df[df["Pos"] == 3].sort_values(
        ["Pts", "GD", "GF"], ascending=False).head(8)
    adv[thirds.index] = 1
    return adv


# =============================================================================
# 2. prior_tournaments  (consistent with poisson_mens_groupstage.R)
# -----------------------------------------------------------------------------
#   Count each team's prior men's World Cup appearances from the same historical
#   file the training table was built from. All tournaments in that file predate
#   2026, so every appearance counts. `DR Congo` played 1974 as `Zaire`; every
#   other 2026 side maps by exact name (debutants correctly get 0).
# =============================================================================
def prior_tournaments_map(path="worldcup_data/group_standings.csv") -> dict:
    try:
        gs = pd.read_csv(path)
    except FileNotFoundError:
        print(f"[warn] {path} not found -- prior_tournaments left blank.", file=sys.stderr)
        return {}
    mens = gs[gs["tournament_name"].str.contains("Men's") &
              ~gs["tournament_name"].str.contains("Women")]
    appearances = mens.groupby("team_name")["tournament_id"].nunique().to_dict()
    xwalk = {"DR Congo": "Zaire"}   # historical-name continuity
    return {t: appearances.get(xwalk.get(t, t), 0) for t in CONF_OF}


# =============================================================================
# 3. ASSEMBLE
# =============================================================================
def main():
    frames = []
    for g in GROUPS:
        try:
            frames.append(scrape_group(g))
        except Exception as e:                       # noqa: BLE001
            print(f"[warn] Group {g} failed: {e}", file=sys.stderr)
    if not frames:
        sys.exit("No groups scraped -- check network access to Wikipedia.")
    df = pd.concat(frames, ignore_index=True)

    # numeric coercion
    for c in ["Pos", "Pld", "W", "D", "L", "GF", "GA", "GD", "Pts"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # advancement is computed per group
    df["advanced"] = (df.groupby("group_name", group_keys=False)
                        .apply(lambda d: determine_advancement(d)))

    prior = prior_tournaments_map()
    out = pd.DataFrame({
        "team_name": df["Team"],
        "group_name": df["group_name"],
        "position": df["Pos"],
        "played": df["Pld"],
        "wins": df["W"], "draws": df["D"], "losses": df["L"],
        "goals_for": df["GF"], "goals_against": df["GA"],
        "goal_difference": df["GD"],
        "points_raw": df["Pts"],
        "points_std": 3 * df["W"] + df["D"],          # single 3-1-0 rule, as in R pipeline
        "advanced": df["advanced"],
        "confederation_code": df["Team"].map(CONF_OF),
        "conf": df["Team"].map(CONF_OF),
        "is_host": df["Team"].isin(HOSTS).astype(int),
        "year": YEAR,
        "year_c": (YEAR - 1994) / 4,                  # = 8, matches the R centering
        "prior_tournaments": df["Team"].map(prior),
        # ---- squad-based predictors: fill via the hook below, else NA ----
        "avg_prior_wc": pd.NA, "avg_age": pd.NA,
        "forward_share": pd.NA, "defender_share": pd.NA, "foreign_manager": pd.NA,
    })

    out = out.sort_values(["group_name", "position"]).reset_index(drop=True)
    out.to_csv("mens_groupstage_2026.csv", index=False)

    # ---- verification -------------------------------------------------------
    print(f"Wrote mens_groupstage_2026.csv: {len(out)} rows "
          f"({out['advanced'].sum()} advanced, {out['is_host'].sum()} hosts)")
    assert len(out) == 48, "expected 48 teams"
    assert out["advanced"].sum() == 32, "expected 32 advancers (24 top-two + 8 thirds)"
    missing = out[out["conf"].isna()]["team_name"].tolist()
    if missing:
        print(f"[warn] unmapped team names (fix NORMALISE/CONFED): {missing}", file=sys.stderr)


# =============================================================================
# 4. SQUAD PREDICTORS -- optional hook to make the CSV fully model-ready
# -----------------------------------------------------------------------------
#   f_structural also needs avg_prior_wc, avg_age, forward_share, defender_share
#   and foreign_manager. These come from each team's 26-player squad, listed at
#   `2026_FIFA_World_Cup_squads`. To populate them, scrape that page's per-team
#   tables (pandas.read_html gives Player / Position / DoB / Caps), then:
#     - avg_age          : (2026 - birth_year) averaged over the squad
#     - forward_share    : share of players with position FW
#     - defender_share   : share with position DF
#     - avg_prior_wc     : mean prior-WC appearances per player (needs a
#                          player-history source; the datahub `squads` table
#                          covers <=2022 and can be extended)
#     - foreign_manager  : 1 if the manager's nationality != team nationality
#   Merge on team_name and overwrite the NA columns above before writing.
# =============================================================================

if __name__ == "__main__":
    main()
