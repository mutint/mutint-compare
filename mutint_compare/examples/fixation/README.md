# mutint-compare-fixation-example

Load with `./mutint load_example mutint-compare-fixation-example`, then open Compare and
choose **Fixed** in the Show menu.

Two ALE lineages sampled at four flasks each, against the 6000 bp synthetic genome. The
point is that **the answer is known**, so an empty Fixed set is unambiguous.

A mutation is *fixed* when it appears in **both of the last two flasks of one ALE** — the
intersection in `analysis.fixed_ids`. Not "seen twice", and not "never lost": only the final two
time points are consulted. The page's threshold asks for how many ALEs that must hold in;
the default is one, and at **2** only `divB` survives here.

| ALE | mutation | 500 | 1000 | 1500 | 2000 | fixed? |
|---|---|:--:|:--:|:--:|:--:|---|
| 1 | `thrA` @150 — arrives and stays | | | ● | ● | **yes** |
| 1 | `divB` @2200 — present throughout | ● | ● | ● | ● | **yes** |
| 1 | `araJ` @1200 — early, then lost | ● | ● | | | no — not in the last two |
| 1 | `pseuA` @3800 — arrives at the end | | | | ● | no — last flask only |
| 2 | `thrB` @600 — arrives and stays | | | ● | ● | **yes**, in ALE 2 |
| 2 | `thrA` @150 — one flask only | ● | | | | no *here* — fixed in ALE 1 |

So `thrA` @150 is fixated in ALE 1 and not in ALE 2, which is what makes the per-lineage
grouping visible: fixation is decided per ALE and then unioned for the experiment.

`thrA` is also hit in both lineages, so **Convergent** holds a gene on the same data.

**The time point is the time axis.** The filenames are strict `A-F-I-R`, so `1-1500-1-1.gd`
is ALE 1, time point 1500, isolate 1, replicate 1 — here the time point is the generation. A
filename that is *not* A-F-I-R falls to auto-numbering, which puts every sample under ALE 1 at
time point 1; an experiment loaded that way can never fix anything, because each ALE ends up
with a single time point.

ALE 1's time point 2000 is sequenced as a **population** (`-p` in the `#=COMMAND` line, which is
what the importer reads), at frequency 0.6. The rest are clonal. It is there so the pages
have a population sample to render.
