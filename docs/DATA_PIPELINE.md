# Data Pipeline — Men's World Cup Group-Stage Modeling Table

This document describes every transformation, aggregation, and cleaning step that turns
the raw datahub World Cup CSVs into the current final modeling dataset,
**`mens_groupstage_1970on.csv`** (368 rows, one per team per group-stage campaign).

The entire pipeline lives in **`poisson_mens_groupstage.R`**. Nothing here requires the
older `worldcupdata_processing.R` / `transformed_data.csv` path, which carried an
unfixed men's/women's filter bug and is superseded by this script.

---

## 0. Source tables

All inputs come from `worldcup_data/` (the datahub relational World Cup dataset). Eight of
the 38 CSVs are read; the rest are unused. Each is loaded with `read.csv(..., stringsAsFactors = FALSE)`:

| Table | Grain (one row per…) | Columns used downstream |
|---|---|---|
| `group_standings.csv` | team × group stage of a tournament | `tournament_id, team_id, team_name, group_name, played, wins, draws, losses, goals_for, goals_against, goal_difference, points, advanced, tournament_name, stage_name` |
| `teams.csv` | national team | `team_id, confederation_code, region_name` |
| `tournaments.csv` | tournament | `tournament_id, year` |
| `squads.csv` | player × tournament (roster slot) | `tournament_id, team_id, player_id, position_code` |
| `players.csv` | player | `player_id, birth_date, count_tournaments` |
| `bookings.csv` | card event | `tournament_id, team_id, stage_name, yellow_card, red_card, second_yellow_card` |
| `host_countries.csv` | host team × tournament | `tournament_id, team_id` |
| `manager_appointments.csv` | manager × team × tournament | `tournament_id, team_id, country_name, team_name` |

The join key throughout is the pair **`(tournament_id, team_id)`** — it uniquely identifies
one team's appearance at one tournament.

---

## 1. Base table — one row per team per group stage

A `sqldf` query builds the spine of the dataset from `group_standings`, joined to `teams`
(for confederation/region) and `tournaments` (for year). Two `WHERE` filters define the
population:

- **Men's only:** `tournament_name LIKE '%FIFA Men''s%'`.
  This is the corrected filter. The original pipeline used `LIKE '%Men''s%'`, but SQLite's
  `LIKE` is case-insensitive, so `"FIFA Women's"` also matched (it contains "men's"). Matching
  the full `"FIFA Men's"` string cleanly excludes women's tournaments — verified as **0
  women's rows** leaking through.
- **Comparable group stage:** `stage_name IN ('group stage', 'first group stage')`. This
  excludes the 1974–1982 *second* group stages, so the `points`/`played` outcome stays
  comparable across eras.

Output carries the raw standings fields plus `confederation_code`, `region_name`, and `year`.
Note `points` is aliased to `points_raw` here — it is **not** the modeling outcome (see §3).

---

## 2. Predictor blocks (each aggregated to `tournament_id × team_id`)

Six independent aggregations are computed, then left-joined onto the base table in §3.

**Team experience** (`team_experience`) → `prior_tournaments`
A correlated subquery counts the distinct prior **men's** World Cups each team appeared in,
using `t2.year < tp.year` so it is strictly backward-looking (no leakage from the current or
future tournaments).

**Squad composition & age** (`squad_stats`), grouped over `squads` joined to `players`:
- `squad_size` — player count on the roster.
- `avg_age` — tournament `year` minus the 4-digit birth year. A `GLOB '[0-9][0-9][0-9][0-9]'`
  guard nulls the **78 players whose `birth_date` is `'not available'`** so `AVG` ignores them;
  without it, `avg_age` blows up to ~1400.
- `forward_share`, `defender_share` — fraction of the squad with `position_code` `FW` / `DF`.
- `avg_career_tournaments` — mean of `players.count_tournaments`. **Leaky** (counts a player's
  whole career including *future* tournaments); computed for reference only and excluded from
  the model (see §5).

**Squad World Cup experience** (`squad_experience`) — the clean, non-leaky alternative:
Per player, a subquery counts prior men's World Cups appeared in (`t2.year < tp.year`), then
aggregates to the squad:
- `avg_prior_wc` — mean prior-WC appearances across the squad.
- `max_prior_wc` — the veteran anchor.
- `debutant_share` — fraction of the squad at their first World Cup.

**Discipline** (`cards`) from `bookings`, filtered to `stage_name = 'group stage'`:
- `yellows` = `SUM(yellow_card)`, `reds` = `SUM(red_card + second_yellow_card)`,
  `total_cards` = row count. Booking data only exists **from 1970 onward**.

**Host flag** (`host`) → `is_host = 1` for the host team of each tournament (from `host_countries`).

**Foreign-manager flag** (`manager`) → `foreign_manager = 1` when the manager's `country_name`
differs from the `team_name` (an approximation — no nationality field, so it compares the
manager's country string to the team name).

---

## 3. Assembly, outcome recomputation, and the 1970 cut

**Assemble** (`model_full`): the base table is `LEFT JOIN`ed to all six predictor blocks on
`(tournament_id, team_id)`. Card, host, and manager columns are wrapped in `COALESCE(..., 0)`
so teams with no matching rows get 0 rather than `NULL` (a team with no cards genuinely has 0).

**Recompute the outcome** — `points_std = 3*wins + draws`.
The raw `points` column mixes two scoring rules: **2 points for a win before 1994, 3 points
from 1994 on**. That changes both the scale (max 6 vs 9) *and* the value of a draw relative to
a win, so raw points are not comparable across eras. Recomputing a single 3-1-0 rule for all
years removes the artifact and yields a consistent **0–9 count** — a legitimate Poisson
response. `points_std` is the modeling outcome.

**Filter to 1970+** (`model_df <- subset(model_full, year >= 1970)`). Chosen because card data
begins in 1970 and, from 1970 on, every team plays exactly 3 group games — a fixed outcome
denominator, so no Poisson exposure offset is needed. This cut takes the table from **445
men's rows (all years) to 368 rows**.

**Guardrail:** `stopifnot(all(model_df$played == 3))` enforces the fixed-denominator
assumption; if a campaign with ≠3 games ever slips in, the script stops rather than silently
producing a biased fit.

**Two final derived columns:**
- `conf` — a cleaned confederation factor. The rare `OFC` level (~2 rows, New Zealand only)
  is lumped into `"OTHER"` to avoid a high-leverage, near-unidentifiable factor level;
  `UEFA` is set as the reference level.
- `year_c` — `year` centered and rescaled to 4-year units about 1994: `(year - 1994) / 4`,
  making the intercept interpretable.

The result is written to **`mens_groupstage_1970on.csv`**.

---

## 4. Final dataset shape

**`mens_groupstage_1970on.csv` — 368 rows × 33 columns.** One row = one men's national team's
group-stage campaign, 1970–2022. Columns, by role:

- **Identifiers / context:** `tournament_id`, `team_id`, `team_name`, `group_name`, `year`,
  `year_c`, `confederation_code`, `region_name`, `conf`.
- **Outcome:** `points_std` (0–9; range 0–9, mean ≈ 4.1, var ≈ 6.3).
- **Raw standings (kept for reference, mostly excluded as predictors):** `played`, `wins`,
  `draws`, `losses`, `goals_for`, `goals_against`, `goal_difference`, `points_raw`, `advanced`.
- **Engineered predictors:** `prior_tournaments`, `squad_size`, `avg_age`, `forward_share`,
  `defender_share`, `avg_career_tournaments`, `avg_prior_wc`, `max_prior_wc`, `debutant_share`,
  `yellows`, `reds`, `total_cards`, `is_host`, `foreign_manager`.

---

## 5. Which columns are usable as predictors (and why the rest are not)

Although the file keeps every column, the model deliberately uses only a pruned subset. The
constraint: many columns are mechanically tied to the outcome or to each other, so fitting on
all of them would be tautological or unidentifiable.

**Excluded — deterministic functions of the result** (would trivially predict the outcome):
`wins`, `draws`, `losses` (since `points_std = 3*wins + draws`); `points_raw` (the old 2/3-pt
outcome); `advanced` (from final ranking); `goals_for`, `goals_against`, `goal_difference`
(downstream match results, and `GD = GF − GA` exactly).

**Excluded — redundant / collinear with a kept predictor:** `yellows`, `reds`
(`total_cards ≈ yellows + reds`; yellows~total_cards r ≈ 0.99); `max_prior_wc`,
`debutant_share` (avg_prior_wc vs debutant_share r ≈ −0.95); `avg_career_tournaments` (leaky).

**Kept — one clean representative per construct:**
- Experience: `prior_tournaments` (team) + `avg_prior_wc` (squad) — r ≈ 0.49, distinct constructs.
- Squad shape: `avg_age`, `forward_share`, `defender_share`, `squad_size`.
- Context: `is_host`, `foreign_manager`, `conf`, `year_c`.
- Discipline: `total_cards`.

This yields the candidate model spec `f_candidate` (and a leaner pre-tournament-only
`f_structural`), which the downstream stepwise AIC/BIC selection then arbitrates among.

A note on independence: the same nation recurs across tournaments, so rows are **not**
independent — the analysis reports team-clustered standard errors to keep significance tests
honest, but that is a modeling step, not a data-processing one.

---

## 6. Reproducing

From the project root (so the relative path `worldcup_data/` resolves):

```
Rscript poisson_mens_groupstage.R
```

Requires `sqldf` (pulls in `RSQLite`); `sandwich` + `lmtest` are optional (clustered SEs).
The run rebuilds the table, prints `Modeling table: 368 rows x 33 cols (men's, 1970+)`,
writes `mens_groupstage_1970on.csv`, and saves `diagnostics.png`.
