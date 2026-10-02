# CLAUDE.md — mutint-compare

The cross-sample mutation table: mutations down, samples across, at `/compare/`. It is core's
**mutation matrix** (`mutint_sample.mutation_matrix.build_matrix`, `mutation_matrix/page.html`)
over every call the experiment holds, every mutation type included, with every control
decided in the browser.
The suite-level `CLAUDE.md` and `mutint-core/CLAUDE.md` (**Compare is a plugin**, **The
mutation matrix**) carry the design of the matrix itself; this file is what is Compare's own.

## Everything on the page is decided in the browser

The view sends every sample, every call -- unfiltered, the designated ancestor's mutations
included and flagged -- and two `ClientSet`s, and that is all it decides. Core's matrix script
applies the reader's frequency range, hides columns by sample, population, treatment, type and time,
draws or drops the ancestral rows, and asks this plugin's rules what the two sets hold, on
every change; see **Compare decides in the browser** in `mutint-core/CLAUDE.md`. So hiding a
population changes what converged at once: the sets are always decided over the table the
reader is looking at.

## Convergent and Fixed are row sets, and used to be plugins

`mutint-converge` and `mutint-fixation` were each this page over a narrower queryset with one
hard-coded rule, an export type, an example dataset and a nav entry. They are two rules now,
offered in the matrix's **Show** menu. Nothing in core knows what "convergent" means.

**The rules live twice, on purpose, and are held together.**
`static/mutint_compare/compare_sets.js` is what runs: it registers both sets with
`window.mutintMatrixSets` and is handed the shown samples and the kept cells of the
non-ancestral rows. `analysis.py` is the reference the rules are written down in, with the
reasoning. `tests/test_sets_js.py` runs the script under node against it over three hundred
random experiments and every threshold spelling worth trying, and `test_example_sets.py` runs
it over the example datasets' pages and asserts their READMEs' answers. Both skip, saying so,
where node is not installed. Change a rule in both files.

The rules at their defaults are the old ones exactly. The **threshold** is at least *N*
populations, or at least *X%* of the populations shown, rounded up: `2` or `50%`, typed into
the two boxes on the Sets tab, beside the Show menu, which carry `data-set-param` and are remembered as a
preference per experiment. A threshold that reads as nothing goes back to the default and the
sentence under the controls says so.

**A mutation the importer could not annotate names no gene.** `Mutation.gene` holds the
literal `"None"` for one (see **Adding a mutation by hand** in core's CLAUDE.md), and counted
as a gene it made every unannotated mutation hit in two populations convergent with every
other. `analysis.gene_names` and the script both drop it.

Three things the fold changed, deliberately:

- **AMP is in the sets.** The old pages passed `filter_type='AMP'` (exclude); Compare shows
  every type. A reader who does not want AMP hides it with the Types menu.
- **The time axis comes from the samples, not the calls** -- the samples *shown*. A time
  point every call was filtered out of is still the last time point, and nothing fixed there.
- **The export types `fixed_mut` and `converged_mut` are gone.** Export is the matrix's own
  CSV menu: the rows showing, or all of them.

## Ancestral rows are display, not data

The designated ancestor's mutations are always on the page, flagged, with cells for the
evolved samples still carrying them; the ancestor itself has no column. The script drops them
unless the reader asks -- the Show/Hide button on the Mutations tab, the `ancestral_shown`
session choice the per-sample page shares -- and leaves them out of both sets either way.
`test_ancestral_display.py` pins what the server sends.

## Tests

`./mutint test mutint_compare` from an assembled project; core has no plugin discovery. To run
uncommitted root-checkout edits, put the root checkouts on `PYTHONPATH` ahead of the
submodule clones. `test_example_sets.py` asserts the two example datasets' known answers
through the page, running the browser's set code over the rows and headers the page hands it.
