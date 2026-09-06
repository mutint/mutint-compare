# mutint-compare-convergence-example

Load with `./mutint load_example mutint-compare-convergence-example`, then open Compare and
choose **Convergent** in the Show menu.

Three ALE lineages sampled at two flasks each, against the 6000 bp synthetic genome.

A gene is **convergent** when it is hit in **at least two ALEs** (the default threshold; the
page lets you ask for more, or for a fraction of the populations) — and it is the *gene* that
converges, not the mutation. Every mutation touching a convergent gene is then listed, so two
different mutations in the same gene in different lineages both appear.

| gene | ALE 1 | ALE 2 | ALE 3 | convergent? |
|---|:--:|:--:|:--:|---|
| `thrA` | SNP @150 | SNP @200 | | **yes** — two lineages, *different* mutations |
| `divB` | SNP @2200 | | SNP @2300 | **yes** — two lineages |
| `araJ` | | | SNP @1200 | no — one lineage, however often |
| `pseuA` | | SNP @3800 | | no — one lineage |

So Convergent holds four mutations: `thrA` @150 and @200, `divB` @2200 and @2300.

`araJ` is the case that earns its place. It is present in **both** of ALE 3's flasks, so it is
recurrent — and still not convergent, because convergence counts *lineages*, not calls.
Nothing else in the dataset separates those two ideas.

Convergence ignores flask ordering entirely, unlike fixation; the two flasks per ALE are here
only so the data reads like a real experiment.
