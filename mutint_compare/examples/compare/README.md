# mutint-compare-example

Load with `./mutint load_example mutint-compare-example`.

Two ALE lineages sampled at three flasks each — a six-column grid — against the 6000 bp
synthetic genome.

Compare pivots the whole experiment: mutations down, samples across, a frequency in each cell.
It computes nothing, so unlike the fixation and converge examples there is no derived answer to
check. What it needs instead is a **pattern**, because a table where every row looks the same
demonstrates nothing:

| mutation | gene | where it appears |
|---|---|---|
| `SNP` @150 | `thrA` | **every sample** — a full row |
| `DEL` @1450 | `araJ` | all three flasks of ALE 1 only — a lineage-shaped row |
| `INS` @2250 | `divB` | the final flask of each ALE — a late-arrival row |
| `AMP` @1750 | `[divA],[divB]` | ALE 2's last two flasks — spans two genes |
| `SUB` @300 | `thrA` | one sample |
| `MOB` @1300 | `araJ` | one sample — the sparsest row |

Six mutation types across six samples, because **Compare is the only page that renders them
all**. `/mutations/amplifications` used to be the only place `AMP` appeared, and Compare
excluded it through a `filter_type` whose value means *exclude*; both are gone, and the `AMP`
row here is what keeps that from coming back.

ALE 1's final flask is a **population** sample (`-p` in the `#=COMMAND` line), at frequency 0.6.
Its cells therefore show a frequency where the clonal samples show a check, which is the
difference the cell rendering exists to make.

## A wart this dataset happens to expose

The `AMP` spans two genes and is annotated `[divA],[divB]` — comma, no space. `get_gene_list`
splits on `", "` (comma **space**), so that collapses to a single pseudo-gene `divA,divB`
rather than two. Compare does not care, but **convergence does**: a multi-gene mutation can
never converge with a mutation in either gene alone. Pre-existing, and left alone here because
changing gene splitting changes convergence results for every deployment.
