# Compare

Compare, at `/compare/`, pivots an experiment into one table: every mutation is a row, every
sequenced sample a column, and each cell is the frequency at which that mutation was called in
that sample. The controls above the table choose which populations, sample types and
frequencies the server produces; the menus above the rows choose what you see of them, and
those choices follow you from experiment to experiment.

## The Show menu: convergent and fixed mutations

**Show** narrows the rows to one of two sets, each counted in the menu. Both are computed from
the rows as you have filtered them, so a frequency cutoff or an ignored gene changes the answer
immediately, and both leave out the designated ancestor's mutations.

Those ancestral mutations are hidden by default. **Show ancestral mutations**, in the line
under the filter, draws them shaded red, with cells for the evolved samples still carrying
them; the ancestor itself gets no column, neither set counts them, and nothing computed
changes. The choice is remembered for you per experiment and is the same one the Mutations
page offers.

**Convergent** — a mutation whose gene was hit in at least so many populations (ALEs). It is
the *gene* that converges, not the mutation: two different mutations in one gene in two
lineages both qualify, and the same gene hit twice in one lineage is recurrence, not
convergence. The default is two populations.

**Fixed** — a mutation present at both of the last two time points sampled from a population,
in at least so many populations. "Last two sampled": an ALE sampled at generations 500, 1000
and 30000 compares 1000 with 30000. A mutation that rose and was lost is not fixed, and one
that arrived only at the final time point is not either. The default is one population.

Both thresholds are in the form above the table, beside the frequency filter, and take either
a number of populations (`2`) or a percentage of the populations shown (`50%`, rounded up:
half of three is two). They are remembered for you per experiment, like the filter.

!!! warning "An ALE with one time point can never fix anything"

    Fixation intersects an ALE's final two time points **by `Sample.time_point`**, so an
    experiment whose ALEs were each sampled once has an empty Fixed set. That usually means
    the samples were not given a position along the evolution, not that nothing fixed.

    Sample identity comes from the filename. A strict `A-F-I-R` name is parsed as such:

    ```
    1-1500-1-1.gd      ALE 1, time point 1500, isolate 1, replicate 1
    ```

    Anything else falls to auto-numbering, which puts **every sample under ALE 1 at time
    point 1**. If your samples have a meaningful position in the evolution, name them
    `A-F-I-R`.

Nothing is stored, so nothing can be stale: an edit, an import or a filter change is
reflected the next time you load the page.

## Export

**Export CSV** is a menu of two. *Filtered mutations* writes what is on the screen — after the
Show menu, the hidden samples and types, and the search box. *All mutations* writes every row
the server produced, hidden or not. Visible columns only, either way.

## Examples

Two shipped datasets have a known answer, so an empty set is unambiguous:

```bash
./mutint load_example mutint-compare-convergence-example
./mutint load_example mutint-compare-fixation-example
```

Each README under `mutint_compare/examples/` states its answer as a table.
