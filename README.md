# Simulated Population Pre-Workout Drink Study

A STATS 101B final project testing whether a **pre-workout drink** and its
**dosage** affect exercise performance, using a balanced two-factor factorial
design analyzed with a two-way ANOVA.

## Research question

Does the type of drink consumed before exercise — and how much of it — have a
significant effect on muscular strength? Three drinks (water, sugar water, and a
sugar-free energy drink) were each tested at three dosages (250, 500, 750 mL),
giving 9 treatment groups of 28 subjects (252 total). The response is the
**percent change** in bicep curls performed in 30 seconds, comparing a no-drink
baseline to a post-treatment measurement:

```
Difference = (X2 - X1) / X1
```

where `X1` = baseline reps and `X2` = reps after the assigned treatment. Percent
change (rather than raw reps) controls for individual variation in baseline
strength.

> Data comes from *The Islands* simulated-population teaching platform, so the
> subjects and measurements are simulated rather than from live human trials.

## Results (short version)

No factor reached significance. Dosage (p = 0.7458) and Drink (p = 0.2750) main
effects are far from significant; the Drink × Dosage interaction (p = 0.0989) is
the closest but still above α = 0.05, and reduced models recover no significant
effect. Diagnostic plots confirm the model assumptions hold. The sugar-free
energy drink showed the strongest positive mean effect, but too small to be
statistically significant.

## Repository layout

```
.
├── analysis/                      # runnable bundle — keep these together
│   ├── Stats101B_Analysis.Rmd     # full analysis (load, plots, ANOVA, diagnostics, Tukey)
│   └── data for stats 101b project - Sheet1.csv   # raw data (252 rows)
├── docs/
│   ├── Stats 101B Report.docx     # full written report
│   └── Stats 101B Presentation - Drink_Dosage Effect on Exercise.pptx
└── README.md
```

The `.Rmd` reads the CSV by relative filename, so the data file lives **next to
it** in `analysis/`. Knit from within that folder.

## Data dictionary (`analysis/…Sheet1.csv`)

| Column           | Meaning                                                    |
|------------------|------------------------------------------------------------|
| `subject_number` | Row / subject ID (1–252)                                   |
| `subject_name`   | Simulated subject name                                     |
| `subject_location` | Simulated home location on *The Islands*                 |
| `Baseline`       | X1 — reps in 30 s with no drink                            |
| `Drink`          | Factor 1 — water / sugar water / sugar free energy drink   |
| `Dosage(mL)`     | Factor 2 — 250 / 500 / 750                                 |
| `Repetitions`    | X2 — reps in 30 s after the assigned treatment             |
| `Difference`     | Response — (X2 − X1) / X1                                  |

## Authors

Jeremy Shiu, Derek Nakagawa, Luke Shen, Kai Zheng
